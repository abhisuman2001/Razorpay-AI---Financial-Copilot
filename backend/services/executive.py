from datetime import date, datetime, time, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ai.service import daily_insights
from lib.dates import today_iso
from models.executive import (
    ExecutiveDashboardResponse,
    ExecutiveMetric,
    ExecutiveReconciliation,
    MetricEvidence,
)
from models.merchant_tables import Expense, Payment, Settlement
from services.cashflow import build_cashflow_forecast
from services.financial_tools import get_revenue
from services.reconciliation import calculate_records, default_date_range, summarize_records


def _trend(value: float | None) -> str:
    if value is None or value == 0:
        return "neutral"
    return "up" if value > 0 else "down"


def _dt(value: date) -> datetime:
    return datetime.combine(value, time.min)


async def build_executive_dashboard(session: AsyncSession) -> ExecutiveDashboardResponse:
    today = date.fromisoformat(today_iso())
    revenue = await get_revenue(session)
    revenue_data = revenue.data
    forecast = await build_cashflow_forecast(session, 30)
    start, end = default_date_range()
    reconciliation_records = await calculate_records(session, start, end)
    reconciliation = summarize_records(reconciliation_records, start, end)
    insights = await daily_insights(session)

    current_month_start = today.replace(day=1)
    recent_payments = list((await session.scalars(
        select(Payment).where(
            Payment.status == "captured",
            Payment.created_at >= _dt(current_month_start),
        ).order_by(Payment.created_at.desc()).limit(5)
    )).all())
    recent_settlements = list((await session.scalars(
        select(Settlement).where(Settlement.status == "settled")
        .order_by(Settlement.settlement_date.desc()).limit(3)
    )).all())
    recent_expenses = list((await session.scalars(
        select(Expense).order_by(Expense.date.desc()).limit(2)
    )).all())
    largest_exceptions = [record for record in reconciliation_records if record.status != "MATCHED"]
    largest_exceptions.sort(key=lambda record: abs(record.difference_amount or record.expected_settlement), reverse=True)

    revenue_change = revenue_data["change_percent"]
    prior_balance = forecast.current_cash_balance - sum(item.daily_net_cashflow for item in forecast.historical[-30:])
    balance_change = (
        round(((forecast.current_cash_balance - prior_balance) / prior_balance) * 100, 2)
        if prior_balance else None
    )
    forecast_change = round(
        ((forecast.forecasted_balance - forecast.current_cash_balance) / forecast.current_cash_balance) * 100,
        2,
    ) if forecast.current_cash_balance else None
    exception_count = (
        reconciliation.partially_matched_transactions + reconciliation.mismatched_transactions
        + reconciliation.pending_transactions + reconciliation.unresolved_transactions
    )

    metrics = [
        ExecutiveMetric(
            id="revenue", label="Revenue", value=revenue_data["current_month_revenue"],
            value_kind="currency", change_percent=revenue_change, trend=_trend(revenue_change),
            period_label="Current calendar month vs previous month",
            detail=f"{revenue_data['current_month_captured_payments']:,} captured payments",
            explanation="Revenue is recognized from successfully captured payments created in the current calendar month.",
            calculation="SUM(payments.amount) WHERE status = captured AND created_at is in the current month",
            source_metric="Captured payment amount", source_tool="get_revenue", drilldown_path="/cfo",
            evidence=[MetricEvidence(
                id=item.payment_id, type="payment", label=item.order_id, date=item.created_at.date(),
                amount=item.amount, status=item.status,
            ) for item in recent_payments],
        ),
        ExecutiveMetric(
            id="current_balance", label="Current balance", value=forecast.current_cash_balance,
            value_kind="currency", change_percent=balance_change, trend=_trend(balance_change),
            period_label=f"As of {forecast.as_of_date.isoformat()}",
            detail="Opening cash + settled income − booked expenses",
            explanation="Current balance is the configured opening cash balance plus every historical settled inflow and booked expense.",
            calculation="OPENING_CASH_BALANCE_PAISE + cumulative settled net cash − cumulative booked expenses",
            source_metric="Cumulative daily cash balance", source_tool="get_cash_balance", drilldown_path="/forecast",
            evidence=[
                *[MetricEvidence(
                    id=item.settlement_id, type="settlement", label=item.external_reference,
                    date=item.settlement_date, amount=item.net_settlement, status=item.status,
                ) for item in recent_settlements],
                *[MetricEvidence(
                    id=item.expense_id, type="expense", label=item.category,
                    date=item.date, amount=-item.amount, status="booked",
                ) for item in recent_expenses],
            ],
        ),
        ExecutiveMetric(
            id="cash_forecast", label="30-day cash forecast", value=forecast.forecasted_balance,
            value_kind="currency", change_percent=forecast_change, trend=_trend(forecast_change),
            period_label=f"30 days after {forecast.as_of_date.isoformat()}",
            detail=f"{forecast.confidence_label}",
            explanation="This is a model prediction, not a recorded fact. Separate Holt-Winters models forecast settled income and booked expenses.",
            calculation="Current balance + cumulative predicted daily income − cumulative predicted daily expenses",
            source_metric="Predicted 30-day ending balance", source_tool="get_cashflow_forecast", drilldown_path="/forecast",
            evidence=[MetricEvidence(
                id=f"forecast-{item.date.isoformat()}", type="prediction", label="Predicted net cash flow",
                date=item.date, amount=item.predicted_net_cashflow, status="prediction",
            ) for item in forecast.forecast[:5]],
        ),
        ExecutiveMetric(
            id="reconciliation_exceptions", label="Reconciliation exceptions", value=exception_count,
            value_kind="count", change_percent=None, trend="neutral",
            period_label="Server-anchored last 90 days",
            detail=f"{reconciliation.mismatched_transactions} mismatched · {reconciliation.unresolved_transactions} unresolved",
            explanation="Exceptions include component-only partial matches, net mismatches, pending settlements, and unresolved links.",
            calculation="PARTIALLY_MATCHED + MISMATCHED + PENDING + UNRESOLVED reconciliation records",
            source_metric="Deterministic reconciliation status", source_tool="get_reconciliation_exceptions",
            drilldown_path="/reconciliation",
            evidence=[MetricEvidence(
                id=item.id, type="reconciliation", label=item.payment_id or item.settlement_id or item.id,
                date=(item.payment_created_at.date() if item.payment_created_at else item.settlement_date or today),
                amount=abs(item.difference_amount or item.expected_settlement), status=item.status,
            ) for item in largest_exceptions[:5]],
        ),
    ]
    return ExecutiveDashboardResponse(
        as_of_date=forecast.as_of_date,
        metrics=metrics,
        cashflow_actual=forecast.historical[-60:],
        cashflow_forecast=forecast.forecast,
        reconciliation=ExecutiveReconciliation(
            transactions_analyzed=reconciliation.total_transactions,
            matched=reconciliation.matched_transactions,
            partially_matched=reconciliation.partially_matched_transactions,
            mismatched=reconciliation.mismatched_transactions,
            pending=reconciliation.pending_transactions,
            unresolved=reconciliation.unresolved_transactions,
            total_discrepancy=reconciliation.total_discrepancy,
            reconciliation_rate=reconciliation.reconciliation_rate,
        ),
        insights=insights.insights,
        insight_mode=insights.mode,
    )