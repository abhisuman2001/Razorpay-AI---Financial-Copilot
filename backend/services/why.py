from datetime import date, datetime, time, timedelta
from typing import Awaitable, Callable

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ai.why_renderer import render_why_explanation
from lib.dates import today_iso
from models.merchant_tables import Customer, Expense, FailedPayment, Payment, Refund, Settlement
from models.why import DriverFinding, WhyMetricResponse
from services.cashflow import build_cashflow_forecast, load_daily_cashflow
from services.reconciliation import calculate_records, default_date_range, summarize_records


def _dt(value: date) -> datetime:
    return datetime.combine(value, time.min)


def _periods() -> tuple[date, date, date, date]:
    today = date.fromisoformat(today_iso())
    current_start = today.replace(day=1)
    previous_end = current_start - timedelta(days=1)
    previous_start = previous_end.replace(day=1)
    return previous_start, current_start, today, today + timedelta(days=1)


def _direction(current: float, previous: float) -> str:
    if current == previous:
        return "unchanged"
    return "increased" if current > previous else "decreased"


def _display(value: float, unit: str) -> str:
    if unit == "currency":
        return f"₹{value / 100:,.0f}"
    if unit == "percent":
        return f"{value:.2f}%"
    return f"{value:,.0f}"


def _difference(current: float, previous: float, unit: str) -> tuple[float, float | None, str]:
    amount = current - previous
    percentage = round((amount / previous) * 100, 2) if previous else None
    summary = f"{abs(percentage):.2f}%" if percentage is not None else _display(abs(amount), unit)
    return amount, percentage, summary


def driver(
    id: str,
    label: str,
    description: str,
    current: float,
    previous: float,
    unit: str,
    increase_effect: str,
    source_metrics: list[str],
    classification: str = "fact",
) -> DriverFinding:
    change_amount, change_percent, change_summary = _difference(current, previous, unit)
    direction = _direction(current, previous)
    if direction == "unchanged":
        effect = "neutral"
    elif direction == "increased":
        effect = increase_effect
    else:
        effect = "negative" if increase_effect == "positive" else "positive" if increase_effect == "negative" else "neutral"
    impact_score = abs(change_percent) if change_percent is not None else (100.0 if change_amount else 0.0)
    return DriverFinding(
        id=id, label=label, description=description,
        current_value=current, previous_value=previous, unit=unit,
        change_amount=change_amount, change_percent=change_percent,
        change_summary=change_summary, direction=direction, effect=effect,
        impact_score=round(impact_score, 2), classification=classification,
        source_metrics=source_metrics,
    )


def response(
    metric_id: str,
    metric_label: str,
    current: float,
    previous: float,
    unit: str,
    drivers: list[DriverFinding],
    current_period: str,
    comparison_period: str,
    methodology: str,
    source_refs: list[str],
    drilldown_path: str,
    classification: str = "fact",
) -> WhyMetricResponse:
    change_amount, change_percent, change_summary = _difference(current, previous, unit)
    ranked = sorted(drivers, key=lambda item: item.impact_score, reverse=True)[:4]
    explanation = render_why_explanation(
        metric_label=metric_label, current_display=_display(current, unit),
        previous_display=_display(previous, unit), direction=_direction(current, previous),
        change_summary=change_summary, drivers=ranked, classification=classification,
    )
    return WhyMetricResponse(
        metric_id=metric_id, metric_label=metric_label, classification=classification,
        as_of_date=date.fromisoformat(today_iso()), current_period=current_period,
        comparison_period=comparison_period, current_value=current, previous_value=previous,
        unit=unit, change_amount=change_amount, change_percent=change_percent,
        change_summary=change_summary, direction=_direction(current, previous),
        drivers=ranked, explanation=explanation,
        explanation_mode="AI CFO deterministic renderer",
        methodology=methodology, source_refs=source_refs,
        drilldown_path=drilldown_path, insufficient_data=previous == 0,
    )


async def _payment_totals(session: AsyncSession) -> tuple[int, int, int, int]:
    previous_start, current_start, _, tomorrow = _periods()
    row = (await session.execute(select(
        func.coalesce(func.sum(case((Payment.created_at >= _dt(current_start), Payment.amount), else_=0)), 0),
        func.coalesce(func.sum(case((Payment.created_at < _dt(current_start), Payment.amount), else_=0)), 0),
        func.sum(case((Payment.created_at >= _dt(current_start), 1), else_=0)),
        func.sum(case((Payment.created_at < _dt(current_start), 1), else_=0)),
    ).where(
        Payment.status == "captured", Payment.created_at >= _dt(previous_start),
        Payment.created_at < _dt(tomorrow),
    ))).one()
    return tuple(int(value or 0) for value in row)


async def why_revenue(session: AsyncSession) -> WhyMetricResponse:
    previous_start, current_start, today, tomorrow = _periods()
    current, previous, current_count, previous_count = await _payment_totals(session)
    method_rows = (await session.execute(select(
        Payment.payment_method,
        func.coalesce(func.sum(case((Payment.created_at >= _dt(current_start), Payment.amount), else_=0)), 0),
        func.coalesce(func.sum(case((Payment.created_at < _dt(current_start), Payment.amount), else_=0)), 0),
    ).where(
        Payment.status == "captured", Payment.created_at >= _dt(previous_start), Payment.created_at < _dt(tomorrow),
    ).group_by(Payment.payment_method))).all()
    method_drivers = [driver(
        f"revenue-{row[0]}", f"{str(row[0]).upper()} successful payment value",
        "Captured payment value for this method compared with the previous calendar month.",
        int(row[1]), int(row[2]), "currency", "positive",
        ["payments.payment_method", "payments.status=captured", "payments.amount"],
    ) for row in method_rows]
    strongest_method = max(method_drivers, key=lambda item: item.impact_score) if method_drivers else None
    returning = (await session.execute(select(
        func.coalesce(func.sum(case((Payment.created_at >= _dt(current_start), Payment.amount), else_=0)), 0),
        func.coalesce(func.sum(case((Payment.created_at < _dt(current_start), Payment.amount), else_=0)), 0),
    ).join(Customer, Customer.customer_id == Payment.customer_id).where(
        Payment.status == "captured", Customer.segment.in_(["repeat", "vip"]),
        Payment.created_at >= _dt(previous_start), Payment.created_at < _dt(tomorrow),
    ))).one()
    refunds = (await session.execute(select(
        func.coalesce(func.sum(case((Refund.created_at >= _dt(current_start), Refund.amount), else_=0)), 0),
        func.coalesce(func.sum(case((Refund.created_at < _dt(current_start), Refund.amount), else_=0)), 0),
    ).where(
        Refund.status == "processed", Refund.created_at >= _dt(previous_start), Refund.created_at < _dt(tomorrow),
    ))).one()
    current_aov = round(current / current_count) if current_count else 0
    previous_aov = round(previous / previous_count) if previous_count else 0
    candidates = [
        *([strongest_method] if strongest_method else []),
        driver("returning-customer-revenue", "Returning customer revenue", "Captured value from customers marked repeat or VIP.", int(returning[0]), int(returning[1]), "currency", "positive", ["customers.segment", "payments.amount"]),
        driver("processed-refunds", "Processed refunds", "Refund value can reduce retained revenue but is not treated as captured-revenue causation.", int(refunds[0]), int(refunds[1]), "currency", "negative", ["refunds.status=processed", "refunds.amount"]),
        driver("average-order-value", "Average captured payment value", "Captured revenue divided by successful payment count, calculated in the backend.", current_aov, previous_aov, "currency", "positive", ["payments.amount", "captured_payment_count"]),
        driver("successful-payment-count", "Successful payment count", "Number of captured payments in each calendar month.", current_count, previous_count, "count", "positive", ["payments.status=captured"]),
    ]
    return response(
        "revenue", "Revenue", current, previous, "currency", candidates,
        f"{current_start.isoformat()} to {today.isoformat()}",
        f"{previous_start.isoformat()} to {(current_start - timedelta(days=1)).isoformat()}",
        "Captured payment revenue is compared month over month; contributors are ranked by absolute percentage movement.",
        ["payments", "customers.segment", "refunds"], "/cfo",
    )


async def _settlement_months(session: AsyncSession) -> dict[str, tuple[int, int]]:
    previous_start, current_start, _, tomorrow = _periods()
    row = (await session.execute(select(
        *[
            func.coalesce(func.sum(case((Settlement.settlement_date >= current_start, column), else_=0)), 0)
            for column in [Settlement.net_settlement, Settlement.gross_amount, Settlement.refund_amount, Settlement.fees, Settlement.taxes]
        ],
        *[
            func.coalesce(func.sum(case((Settlement.settlement_date < current_start, column), else_=0)), 0)
            for column in [Settlement.net_settlement, Settlement.gross_amount, Settlement.refund_amount, Settlement.fees, Settlement.taxes]
        ],
        func.sum(case((Settlement.settlement_date >= current_start, 1), else_=0)),
        func.sum(case((Settlement.settlement_date < current_start, 1), else_=0)),
    ).where(
        Settlement.status == "settled", Settlement.settlement_date >= previous_start,
        Settlement.settlement_date < tomorrow,
    ))).one()
    names = ["net", "gross", "refunds", "fees", "taxes"]
    return {
        **{name: (int(row[index]), int(row[index + 5])) for index, name in enumerate(names)},
        "count": (int(row[10] or 0), int(row[11] or 0)),
    }


async def why_settlement(session: AsyncSession) -> WhyMetricResponse:
    previous_start, current_start, today, _ = _periods()
    stats = await _settlement_months(session)
    drivers = [
        driver("settlement-gross", "Gross settled payment value", "Gross payment value represented by settled records.", *stats["gross"], "currency", "positive", ["settlements.gross_amount"]),
        driver("settlement-refunds", "Refunds deducted", "Processed refund value deducted in settlement records.", *stats["refunds"], "currency", "negative", ["settlements.refund_amount"]),
        driver("settlement-fees", "Gateway fees deducted", "Recorded fees deducted before net cash is settled.", *stats["fees"], "currency", "negative", ["settlements.fees"]),
        driver("settlement-taxes", "Taxes on fees", "Recorded tax deducted from settlement proceeds.", *stats["taxes"], "currency", "negative", ["settlements.taxes"]),
        driver("settlement-count", "Settled transaction count", "Number of settlement rows marked settled.", *stats["count"], "count", "positive", ["settlements.status=settled"]),
    ]
    return response(
        "settlement_amount", "Settlement amount", *stats["net"], "currency", drivers,
        f"{current_start.isoformat()} to {today.isoformat()}",
        f"{previous_start.isoformat()} to {(current_start - timedelta(days=1)).isoformat()}",
        "Net settlements equal recorded gross amount minus refunds, fees, and taxes; monthly drivers are ranked by movement.",
        ["settlements.gross_amount", "settlements.refund_amount", "settlements.fees", "settlements.taxes", "settlements.net_settlement"], "/reconciliation",
    )


async def why_cash_balance(session: AsyncSession) -> WhyMetricResponse:
    previous_start, current_start, today, tomorrow = _periods()
    history, _, _, _ = await load_daily_cashflow(session)
    current = history[-1].cumulative_cash_balance
    prior_points = [point for point in history if point.date < current_start]
    previous = prior_points[-1].cumulative_cash_balance if prior_points else 0
    settlements = await _settlement_months(session)
    expenses = (await session.execute(select(
        func.coalesce(func.sum(case((Expense.date >= current_start, Expense.amount), else_=0)), 0),
        func.coalesce(func.sum(case((Expense.date < current_start, Expense.amount), else_=0)), 0),
    ).where(Expense.date >= previous_start, Expense.date < tomorrow))).one()
    drivers = [
        driver("cash-settled-income", "Settled cash received", "Net settled cash recognized on settlement dates.", *settlements["net"], "currency", "positive", ["settlements.net_settlement"]),
        driver("cash-expenses", "Booked expenses", "Operating expenses recognized on their booked dates.", int(expenses[0]), int(expenses[1]), "currency", "negative", ["expenses.amount"]),
        driver("cash-refunds", "Settlement refunds", "Refund deductions included in settled cash.", *settlements["refunds"], "currency", "negative", ["settlements.refund_amount"]),
        driver("cash-fees", "Settlement fees", "Gateway fee deductions included in settled cash.", *settlements["fees"], "currency", "negative", ["settlements.fees"]),
    ]
    return response(
        "cash_balance", "Cash balance", current, previous, "currency", drivers,
        f"Balance as of {today.isoformat()}", f"Balance as of {(current_start - timedelta(days=1)).isoformat()}",
        "Cash balance is opening cash plus cumulative settled income minus booked expenses; monthly movements explain the change.",
        ["OPENING_CASH_BALANCE_PAISE", "settlements.status=settled", "expenses"], "/forecast",
    )


async def why_refund_rate(session: AsyncSession) -> WhyMetricResponse:
    previous_start, current_start, today, tomorrow = _periods()
    revenue_current, revenue_previous, _, _ = await _payment_totals(session)
    refund_row = (await session.execute(select(
        func.coalesce(func.sum(case((Refund.created_at >= _dt(current_start), Refund.amount), else_=0)), 0),
        func.coalesce(func.sum(case((Refund.created_at < _dt(current_start), Refund.amount), else_=0)), 0),
        func.sum(case((Refund.created_at >= _dt(current_start), 1), else_=0)),
        func.sum(case((Refund.created_at < _dt(current_start), 1), else_=0)),
    ).where(Refund.status == "processed", Refund.created_at >= _dt(previous_start), Refund.created_at < _dt(tomorrow)))).one()
    refund_current, refund_previous = int(refund_row[0]), int(refund_row[1])
    count_current, count_previous = int(refund_row[2] or 0), int(refund_row[3] or 0)
    current_rate = round((refund_current / revenue_current) * 100, 2) if revenue_current else 0
    previous_rate = round((refund_previous / revenue_previous) * 100, 2) if revenue_previous else 0
    current_avg = round(refund_current / count_current) if count_current else 0
    previous_avg = round(refund_previous / count_previous) if count_previous else 0
    drivers = [
        driver("refund-value", "Processed refund value", "Total processed refund value in each month.", refund_current, refund_previous, "currency", "negative", ["refunds.amount"]),
        driver("refund-count", "Processed refund count", "Number of refunds with processed status.", count_current, count_previous, "count", "negative", ["refunds.status=processed"]),
        driver("refund-average", "Average refund value", "Processed refund value divided by processed refund count.", current_avg, previous_avg, "currency", "negative", ["refunds.amount", "processed_refund_count"]),
        driver("refund-revenue-base", "Captured revenue base", "Captured revenue used as the refund-rate denominator.", revenue_current, revenue_previous, "currency", "positive", ["payments.status=captured", "payments.amount"]),
    ]
    return response(
        "refund_rate", "Refund rate", current_rate, previous_rate, "percent", drivers,
        f"{current_start.isoformat()} to {today.isoformat()}",
        f"{previous_start.isoformat()} to {(current_start - timedelta(days=1)).isoformat()}",
        "Refund rate equals processed refund value divided by captured payment revenue for each calendar month.",
        ["refunds.status=processed", "refunds.amount", "payments.status=captured", "payments.amount"], "/cfo",
    )


async def why_payment_success(session: AsyncSession) -> WhyMetricResponse:
    previous_start, current_start, today, tomorrow = _periods()
    row = (await session.execute(select(
        func.sum(case((Payment.created_at >= _dt(current_start), 1), else_=0)),
        func.sum(case((Payment.created_at < _dt(current_start), 1), else_=0)),
        func.sum(case(((Payment.created_at >= _dt(current_start)) & (Payment.status == "captured"), 1), else_=0)),
        func.sum(case(((Payment.created_at < _dt(current_start)) & (Payment.status == "captured"), 1), else_=0)),
        func.sum(case(((Payment.created_at >= _dt(current_start)) & (Payment.status == "failed"), 1), else_=0)),
        func.sum(case(((Payment.created_at < _dt(current_start)) & (Payment.status == "failed"), 1), else_=0)),
    ).where(Payment.created_at >= _dt(previous_start), Payment.created_at < _dt(tomorrow)))).one()
    total_current, total_previous, captured_current, captured_previous, failed_current, failed_previous = [int(value or 0) for value in row]
    current_rate = round((captured_current / total_current) * 100, 2) if total_current else 0
    previous_rate = round((captured_previous / total_previous) * 100, 2) if total_previous else 0
    method_rows = (await session.execute(select(
        Payment.payment_method,
        func.sum(case((Payment.created_at >= _dt(current_start), 1), else_=0)),
        func.sum(case((Payment.created_at < _dt(current_start), 1), else_=0)),
        func.sum(case(((Payment.created_at >= _dt(current_start)) & (Payment.status == "captured"), 1), else_=0)),
        func.sum(case(((Payment.created_at < _dt(current_start)) & (Payment.status == "captured"), 1), else_=0)),
    ).where(Payment.created_at >= _dt(previous_start), Payment.created_at < _dt(tomorrow)).group_by(Payment.payment_method))).all()
    method_drivers = []
    for method, cur_total, prev_total, cur_captured, prev_captured in method_rows:
        cur_rate = round((int(cur_captured or 0) / int(cur_total or 1)) * 100, 2)
        prev_rate = round((int(prev_captured or 0) / int(prev_total or 1)) * 100, 2)
        method_drivers.append(driver(
            f"success-{method}", f"{str(method).upper()} success rate",
            "Captured attempts divided by all attempts for this method.",
            cur_rate, prev_rate, "percent", "positive",
            ["payments.payment_method", "payments.status"],
        ))
    method_drivers.sort(key=lambda item: item.impact_score, reverse=True)
    gateway_errors = (await session.execute(select(
        func.sum(case((FailedPayment.failed_at >= _dt(current_start), 1), else_=0)),
        func.sum(case((FailedPayment.failed_at < _dt(current_start), 1), else_=0)),
    ).where(
        FailedPayment.error_code.in_(["GATEWAY_ERROR", "SERVER_ERROR"]),
        FailedPayment.failed_at >= _dt(previous_start), FailedPayment.failed_at < _dt(tomorrow),
    ))).one()
    drivers = [
        *method_drivers[:2],
        driver("failed-attempts", "Failed payment attempts", "Attempts with failed status.", failed_current, failed_previous, "count", "negative", ["payments.status=failed"]),
        driver("captured-attempts", "Captured payment attempts", "Attempts with captured status.", captured_current, captured_previous, "count", "positive", ["payments.status=captured"]),
        driver("gateway-errors", "Gateway and server errors", "Failed attempts carrying gateway or server error codes.", int(gateway_errors[0] or 0), int(gateway_errors[1] or 0), "count", "negative", ["failed_payments.error_code"]),
    ]
    return response(
        "payment_success_rate", "Payment success rate", current_rate, previous_rate, "percent", drivers,
        f"{current_start.isoformat()} to {today.isoformat()}",
        f"{previous_start.isoformat()} to {(current_start - timedelta(days=1)).isoformat()}",
        "Success rate equals captured payment attempts divided by all payment attempts; contributors are observed method and failure movements.",
        ["payments.status", "payments.payment_method", "failed_payments.error_code"], "/cfo",
    )


async def why_forecast(session: AsyncSession) -> WhyMetricResponse:
    forecast = await build_cashflow_forecast(session, 30)
    recent = forecast.historical[-30:]
    recent_income = sum(item.daily_income for item in recent)
    recent_expenses = sum(item.daily_expenses for item in recent)
    recent_net = sum(item.daily_net_cashflow for item in recent)
    predicted_net = sum(item.predicted_net_cashflow for item in forecast.forecast)
    lower_bound = min(item.balance_lower for item in forecast.forecast)
    drivers = [
        driver("forecast-income", "Expected incoming cash", "Holt-Winters predicted settled income compared with recorded recent income.", forecast.expected_incoming, recent_income, "currency", "positive", ["forecast.predicted_income", "historical.daily_income"], "prediction"),
        driver("forecast-expenses", "Expected outgoing cash", "Holt-Winters predicted expenses compared with recorded recent expenses.", forecast.expected_outgoing, recent_expenses, "currency", "negative", ["forecast.predicted_expenses", "historical.daily_expenses"], "prediction"),
        driver("forecast-net", "Net cash-flow outlook", "Cumulative predicted net flow compared with recorded recent net flow.", predicted_net, recent_net, "currency", "positive", ["forecast.predicted_net_cashflow", "historical.daily_net_cashflow"], "prediction"),
        driver("forecast-lower-bound", "80% lower balance bound", "Lowest balance in the model uncertainty range compared with current cash.", lower_bound, forecast.current_cash_balance, "currency", "positive", ["forecast.balance_lower", "current_cash_balance"], "prediction"),
    ]
    return response(
        "forecasted_balance", "Forecasted balance", forecast.forecasted_balance,
        forecast.current_cash_balance, "currency", drivers,
        f"30 days after {forecast.as_of_date.isoformat()}", f"Recorded balance on {forecast.as_of_date.isoformat()}",
        "Forecast drivers compare backend-predicted incoming, outgoing, net flow, and uncertainty with the latest 30 recorded days.",
        ["cashflow_forecast_30", "settlements.status=settled", "expenses", "80% model range"], "/forecast", "prediction",
    )


async def why_reconciliation(session: AsyncSession) -> WhyMetricResponse:
    current_start, current_end = default_date_range()
    previous_end = current_start - timedelta(days=1)
    previous_start = previous_end - timedelta(days=89)
    current_summary = summarize_records(await calculate_records(session, current_start, current_end), current_start, current_end)
    previous_summary = summarize_records(await calculate_records(session, previous_start, previous_end), previous_start, previous_end)
    current = current_summary.partially_matched_transactions + current_summary.mismatched_transactions + current_summary.pending_transactions + current_summary.unresolved_transactions
    previous = previous_summary.partially_matched_transactions + previous_summary.mismatched_transactions + previous_summary.pending_transactions + previous_summary.unresolved_transactions
    drivers = [
        driver("recon-mismatched", "Net settlement mismatches", "Records where actual net settlement differs from deterministic expected net.", current_summary.mismatched_transactions, previous_summary.mismatched_transactions, "count", "negative", ["reconciliation.status=MISMATCHED"]),
        driver("recon-partial", "Component-only mismatches", "Records where net matches but refund, fee, or tax components differ.", current_summary.partially_matched_transactions, previous_summary.partially_matched_transactions, "count", "negative", ["reconciliation.status=PARTIALLY_MATCHED"]),
        driver("recon-pending", "Pending settlements", "Captured payments or settlement records still inside processing state.", current_summary.pending_transactions, previous_summary.pending_transactions, "count", "negative", ["reconciliation.status=PENDING"]),
        driver("recon-unresolved", "Unresolved links", "Captured payments without settlement or settlements without payment links.", current_summary.unresolved_transactions, previous_summary.unresolved_transactions, "count", "negative", ["reconciliation.status=UNRESOLVED"]),
        driver("recon-discrepancy", "Absolute discrepancy", "Absolute net difference across reconciled records.", current_summary.total_discrepancy, previous_summary.total_discrepancy, "currency", "negative", ["reconciliation.total_discrepancy"]),
    ]
    return response(
        "reconciliation_exceptions", "Reconciliation exceptions", current, previous, "count", drivers,
        f"{current_start.isoformat()} to {current_end.isoformat()}",
        f"{previous_start.isoformat()} to {previous_end.isoformat()}",
        "Exception statuses are counted over two consecutive 90-day windows using the deterministic reconciliation engine.",
        ["deterministic_reconciliation_engine", "payments", "refunds", "settlements"], "/reconciliation",
    )


WhyFunction = Callable[[AsyncSession], Awaitable[WhyMetricResponse]]
WHY_REGISTRY: dict[str, WhyFunction] = {
    "revenue": why_revenue,
    "cash_balance": why_cash_balance,
    "settlement_amount": why_settlement,
    "refund_rate": why_refund_rate,
    "payment_success_rate": why_payment_success,
    "forecasted_balance": why_forecast,
    "reconciliation_exceptions": why_reconciliation,
}