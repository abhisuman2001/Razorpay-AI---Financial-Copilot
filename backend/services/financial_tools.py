from datetime import date, datetime, time, timedelta, timezone
from typing import Awaitable, Callable

from sqlalchemy import case, distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from lib.dates import today_iso
from models.cfo import FinancialToolResult
from models.merchant_tables import Customer, Expense, FailedPayment, Order, Payment, Refund, Settlement
from services.cashflow import build_cashflow_forecast, load_daily_cashflow
from services.reconciliation import calculate_records, default_date_range, summarize_records


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _month_bounds(anchor: date) -> tuple[date, date, date]:
    current_start = anchor.replace(day=1)
    previous_end = current_start - timedelta(days=1)
    previous_start = previous_end.replace(day=1)
    return previous_start, current_start, anchor + timedelta(days=1)


def _change(current: int, previous: int) -> tuple[int, float | None]:
    difference = current - previous
    percentage = round((difference / previous) * 100, 2) if previous else None
    return difference, percentage


def _dt(day: date) -> datetime:
    return datetime.combine(day, time.min)


async def get_revenue(session: AsyncSession) -> FinancialToolResult:
    today = date.fromisoformat(today_iso())
    previous_start, current_start, tomorrow = _month_bounds(today)
    query = select(
        func.coalesce(func.sum(case((Payment.created_at >= _dt(current_start), Payment.amount), else_=0)), 0),
        func.coalesce(func.sum(case((Payment.created_at < _dt(current_start), Payment.amount), else_=0)), 0),
        func.sum(case((Payment.created_at >= _dt(current_start), 1), else_=0)),
        func.sum(case((Payment.created_at < _dt(current_start), 1), else_=0)),
    ).where(
        Payment.status == "captured",
        Payment.created_at >= _dt(previous_start),
        Payment.created_at < _dt(tomorrow),
    )
    current, previous, current_count, previous_count = (await session.execute(query)).one()
    difference, change_percent = _change(int(current), int(previous))
    methods = (await session.execute(
        select(Payment.payment_method, func.sum(Payment.amount).label("amount"))
        .where(Payment.status == "captured", Payment.created_at >= _dt(current_start), Payment.created_at < _dt(tomorrow))
        .group_by(Payment.payment_method).order_by(func.sum(Payment.amount).desc())
    )).all()
    return FinancialToolResult(
        tool_name="get_revenue", classification="fact",
        period_label=f"{current_start.isoformat()} to {today.isoformat()} vs previous month",
        generated_at=_now(),
        data={
            "current_month_revenue": int(current), "previous_month_revenue": int(previous),
            "change_amount": difference, "change_percent": change_percent,
            "current_month_captured_payments": int(current_count or 0),
            "previous_month_captured_payments": int(previous_count or 0),
            "payment_method_mix": [{"payment_method": row[0], "revenue": int(row[1])} for row in methods],
            "currency": "INR", "amount_unit": "paise",
        },
        source_refs=["payments.status=captured", "payments.created_at", "payments.amount"],
        insufficient_data=previous == 0,
    )


async def get_expenses(session: AsyncSession) -> FinancialToolResult:
    today = date.fromisoformat(today_iso())
    previous_start, current_start, tomorrow = _month_bounds(today)
    current = await session.scalar(select(func.coalesce(func.sum(Expense.amount), 0)).where(
        Expense.date >= current_start, Expense.date < tomorrow,
    )) or 0
    previous = await session.scalar(select(func.coalesce(func.sum(Expense.amount), 0)).where(
        Expense.date >= previous_start, Expense.date < current_start,
    )) or 0
    difference, change_percent = _change(int(current), int(previous))
    categories = (await session.execute(
        select(Expense.category, func.sum(Expense.amount).label("amount"), func.count(Expense.expense_id))
        .where(Expense.date >= current_start, Expense.date < tomorrow)
        .group_by(Expense.category).order_by(func.sum(Expense.amount).desc()).limit(5)
    )).all()
    return FinancialToolResult(
        tool_name="get_expenses", classification="fact",
        period_label=f"{current_start.isoformat()} to {today.isoformat()} vs previous month",
        generated_at=_now(), data={
            "current_month_expenses": int(current), "previous_month_expenses": int(previous),
            "change_amount": difference, "change_percent": change_percent,
            "top_categories": [{"category": row[0], "amount": int(row[1]), "transactions": int(row[2])} for row in categories],
            "currency": "INR", "amount_unit": "paise",
        }, source_refs=["expenses.date", "expenses.amount", "expenses.category"],
        insufficient_data=previous == 0,
    )


async def get_cash_balance(session: AsyncSession) -> FinancialToolResult:
    history, _, _, as_of = await load_daily_cashflow(session)
    point = history[-1]
    last_30 = history[-30:]
    return FinancialToolResult(
        tool_name="get_cash_balance", classification="fact",
        period_label=f"As of {as_of.isoformat()}", generated_at=_now(), data={
            "current_cash_balance": point.cumulative_cash_balance,
            "last_30_day_income": sum(item.daily_income for item in last_30),
            "last_30_day_expenses": sum(item.daily_expenses for item in last_30),
            "last_30_day_net_cashflow": sum(item.daily_net_cashflow for item in last_30),
            "currency": "INR", "amount_unit": "paise",
        }, source_refs=["settlements.status=settled", "settlements.net_settlement", "expenses.amount", "OPENING_CASH_BALANCE_PAISE"],
    )


async def get_failed_payments(session: AsyncSession) -> FinancialToolResult:
    today = date.fromisoformat(today_iso())
    previous_start, current_start, tomorrow = _month_bounds(today)
    rows = (await session.execute(
        select(
            func.sum(case((FailedPayment.failed_at >= _dt(current_start), 1), else_=0)),
            func.coalesce(func.sum(case((FailedPayment.failed_at >= _dt(current_start), Payment.amount), else_=0)), 0),
            func.sum(case((FailedPayment.failed_at < _dt(current_start), 1), else_=0)),
        ).join(Payment, Payment.payment_id == FailedPayment.payment_id).where(
            FailedPayment.failed_at >= _dt(previous_start), FailedPayment.failed_at < _dt(tomorrow)
        )
    )).one()
    current_count, current_amount, previous_count = int(rows[0] or 0), int(rows[1] or 0), int(rows[2] or 0)
    count_change, count_change_percent = _change(current_count, previous_count)
    reasons = (await session.execute(
        select(FailedPayment.error_code, func.count(FailedPayment.failed_payment_id).label("count"))
        .where(FailedPayment.failed_at >= _dt(current_start), FailedPayment.failed_at < _dt(tomorrow))
        .group_by(FailedPayment.error_code).order_by(func.count(FailedPayment.failed_payment_id).desc()).limit(5)
    )).all()
    return FinancialToolResult(
        tool_name="get_failed_payments", classification="fact",
        period_label=f"{current_start.isoformat()} to {today.isoformat()} vs previous month",
        generated_at=_now(), data={
            "current_month_failed_count": current_count, "current_month_failed_amount": current_amount,
            "previous_month_failed_count": previous_count, "count_change": count_change,
            "count_change_percent": count_change_percent,
            "top_failure_reasons": [{"error_code": row[0], "count": int(row[1])} for row in reasons],
            "currency": "INR", "amount_unit": "paise",
        }, source_refs=["failed_payments", "payments.amount"], insufficient_data=previous_count == 0,
    )


async def get_refunds(session: AsyncSession) -> FinancialToolResult:
    today = date.fromisoformat(today_iso())
    _, current_start, tomorrow = _month_bounds(today)
    refund_count, refund_amount = (await session.execute(
        select(func.count(Refund.refund_id), func.coalesce(func.sum(Refund.amount), 0)).where(
            Refund.status == "processed", Refund.created_at >= _dt(current_start), Refund.created_at < _dt(tomorrow)
        )
    )).one()
    revenue = await session.scalar(select(func.coalesce(func.sum(Payment.amount), 0)).where(
        Payment.status == "captured", Payment.created_at >= _dt(current_start), Payment.created_at < _dt(tomorrow)
    )) or 0
    refund_rate = round((int(refund_amount) / int(revenue)) * 100, 2) if revenue else None
    reasons = (await session.execute(
        select(Refund.reason, func.sum(Refund.amount).label("amount"), func.count(Refund.refund_id))
        .where(Refund.status == "processed", Refund.created_at >= _dt(current_start), Refund.created_at < _dt(tomorrow))
        .group_by(Refund.reason).order_by(func.sum(Refund.amount).desc()).limit(5)
    )).all()
    return FinancialToolResult(
        tool_name="get_refunds", classification="fact",
        period_label=f"{current_start.isoformat()} to {today.isoformat()}", generated_at=_now(), data={
            "processed_refund_count": int(refund_count), "processed_refund_amount": int(refund_amount),
            "captured_revenue": int(revenue), "refund_rate_percent": refund_rate,
            "top_reasons": [{"reason": row[0], "amount": int(row[1]), "count": int(row[2])} for row in reasons],
            "currency": "INR", "amount_unit": "paise",
        }, source_refs=["refunds.status=processed", "refunds.amount", "payments.status=captured"],
        insufficient_data=revenue == 0,
    )


async def get_settlement_summary(session: AsyncSession) -> FinancialToolResult:
    today = date.fromisoformat(today_iso())
    start = today - timedelta(days=29)
    row = (await session.execute(select(
        func.count(Settlement.settlement_id), func.coalesce(func.sum(Settlement.gross_amount), 0),
        func.coalesce(func.sum(Settlement.refund_amount), 0), func.coalesce(func.sum(Settlement.fees), 0),
        func.coalesce(func.sum(Settlement.taxes), 0), func.coalesce(func.sum(Settlement.net_settlement), 0),
    ).where(Settlement.settlement_date >= start, Settlement.settlement_date <= today))).one()
    statuses = (await session.execute(
        select(Settlement.status, func.count(Settlement.settlement_id))
        .where(Settlement.settlement_date >= start, Settlement.settlement_date <= today)
        .group_by(Settlement.status)
    )).all()
    return FinancialToolResult(
        tool_name="get_settlement_summary", classification="fact",
        period_label=f"{start.isoformat()} to {today.isoformat()}", generated_at=_now(), data={
            "settlement_count": int(row[0]), "gross_amount": int(row[1]), "refund_amount": int(row[2]),
            "fees": int(row[3]), "taxes": int(row[4]), "net_settlement": int(row[5]),
            "status_counts": {status: int(count) for status, count in statuses},
            "currency": "INR", "amount_unit": "paise",
        }, source_refs=["settlements.gross_amount", "settlements.refund_amount", "settlements.fees", "settlements.taxes", "settlements.net_settlement"],
        insufficient_data=row[0] == 0,
    )


async def get_reconciliation_exceptions(session: AsyncSession) -> FinancialToolResult:
    start, end = default_date_range()
    records = await calculate_records(session, start, end)
    summary = summarize_records(records, start, end)
    exceptions = [record for record in records if record.status != "MATCHED"]
    exceptions.sort(key=lambda record: abs(record.difference_amount or record.expected_settlement), reverse=True)
    return FinancialToolResult(
        tool_name="get_reconciliation_exceptions", classification="fact",
        period_label=f"{start.isoformat()} to {end.isoformat()}", generated_at=_now(), data={
            "total_exceptions": len(exceptions), "mismatched": summary.mismatched_transactions,
            "partially_matched": summary.partially_matched_transactions, "pending": summary.pending_transactions,
            "unresolved": summary.unresolved_transactions, "total_discrepancy": summary.total_discrepancy,
            "reconciliation_rate": summary.reconciliation_rate,
            "largest_exceptions": [{
                "reconciliation_id": item.id, "payment_id": item.payment_id, "settlement_id": item.settlement_id,
                "status": item.status, "expected_settlement": item.expected_settlement,
                "actual_settlement": item.actual_settlement, "difference_amount": item.difference_amount,
                "possible_reason": item.possible_reason,
            } for item in exceptions[:7]],
            "currency": "INR", "amount_unit": "paise",
        }, source_refs=["deterministic_reconciliation_engine", "payments", "refunds", "settlements"],
        insufficient_data=not records,
    )


async def get_cashflow_forecast(session: AsyncSession) -> FinancialToolResult:
    forecast = await build_cashflow_forecast(session, 30)
    return FinancialToolResult(
        tool_name="get_cashflow_forecast", classification="prediction",
        period_label=f"30 days after {forecast.as_of_date.isoformat()}", generated_at=_now(), data={
            "as_of_date": forecast.as_of_date.isoformat(), "horizon_days": 30,
            "current_cash_balance": forecast.current_cash_balance,
            "expected_incoming": forecast.expected_incoming, "expected_outgoing": forecast.expected_outgoing,
            "forecasted_balance": forecast.forecasted_balance,
            "lowest_balance_lower_bound": min(item.balance_lower for item in forecast.forecast),
            "confidence_level": forecast.confidence_level, "confidence_label": forecast.confidence_label,
            "model_name": forecast.model_name,
            "risks": [risk.model_dump(mode="json") for risk in forecast.risks],
            "currency": "INR", "amount_unit": "paise",
        }, source_refs=["cashflow_forecast_30", "settlements.status=settled", "expenses", "OPENING_CASH_BALANCE_PAISE"],
    )


async def get_top_customers(session: AsyncSession) -> FinancialToolResult:
    today = date.fromisoformat(today_iso())
    start = today - timedelta(days=89)
    rows = (await session.execute(
        select(
            Customer.customer_id, Customer.name, Customer.segment,
            func.sum(Payment.amount).label("revenue"), func.count(Payment.payment_id).label("payments"),
            func.count(distinct(Payment.order_id)).label("orders"),
        ).join(Payment, Payment.customer_id == Customer.customer_id).where(
            Payment.status == "captured", Payment.created_at >= _dt(start), Payment.created_at < _dt(today + timedelta(days=1))
        ).group_by(Customer.customer_id, Customer.name, Customer.segment)
        .order_by(func.sum(Payment.amount).desc()).limit(10)
    )).all()
    return FinancialToolResult(
        tool_name="get_top_customers", classification="fact",
        period_label=f"{start.isoformat()} to {today.isoformat()}", generated_at=_now(), data={
            "customers": [{
                "customer_id": row[0], "name": row[1], "segment": row[2],
                "captured_revenue": int(row[3]), "captured_payments": int(row[4]), "orders": int(row[5]),
            } for row in rows], "currency": "INR", "amount_unit": "paise",
        }, source_refs=["customers", "payments.status=captured", "payments.amount"], insufficient_data=not rows,
    )


async def get_customer_statistics(session: AsyncSession) -> FinancialToolResult:
    today = date.fromisoformat(today_iso())
    start = today - timedelta(days=89)
    customer_rows = (await session.execute(
        select(Payment.customer_id, func.sum(Payment.amount), func.count(distinct(Payment.order_id)))
        .where(Payment.status == "captured", Payment.created_at >= _dt(start), Payment.created_at < _dt(today + timedelta(days=1)))
        .group_by(Payment.customer_id)
    )).all()
    active = len(customer_rows)
    repeat = sum(int(row[2]) > 1 for row in customer_rows)
    revenue = sum(int(row[1]) for row in customer_rows)
    new_customers = await session.scalar(select(func.count(Customer.customer_id)).where(
        Customer.created_at >= _dt(start), Customer.created_at < _dt(today + timedelta(days=1))
    )) or 0
    return FinancialToolResult(
        tool_name="get_customer_statistics", classification="fact",
        period_label=f"{start.isoformat()} to {today.isoformat()}", generated_at=_now(), data={
            "active_paying_customers": active, "repeat_customers": repeat,
            "repeat_customer_rate_percent": round((repeat / active) * 100, 2) if active else None,
            "new_customers": int(new_customers),
            "average_revenue_per_active_customer": round(revenue / active) if active else None,
            "captured_revenue": revenue, "currency": "INR", "amount_unit": "paise",
        }, source_refs=["customers.created_at", "payments.status=captured", "payments.customer_id", "payments.order_id"],
        insufficient_data=active == 0,
    )


ToolFunction = Callable[[AsyncSession], Awaitable[FinancialToolResult]]
TOOL_REGISTRY: dict[str, ToolFunction] = {
    "get_revenue": get_revenue,
    "get_expenses": get_expenses,
    "get_cash_balance": get_cash_balance,
    "get_failed_payments": get_failed_payments,
    "get_refunds": get_refunds,
    "get_settlement_summary": get_settlement_summary,
    "get_reconciliation_exceptions": get_reconciliation_exceptions,
    "get_cashflow_forecast": get_cashflow_forecast,
    "get_top_customers": get_top_customers,
    "get_customer_statistics": get_customer_statistics,
}