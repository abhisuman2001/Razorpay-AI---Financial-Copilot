from collections import defaultdict
from datetime import date, timedelta

import numpy as np
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from statsmodels.tsa.holtwinters import ExponentialSmoothing

from lib.dates import today_iso
from models.financial import (
    ForecastPoint,
    ForecastResponse,
    ReconciliationItem,
    ReconciliationResponse,
    ReconciliationSummary,
)
from models.tables import FinancialTransaction


async def load_transactions(session: AsyncSession) -> list[FinancialTransaction]:
    result = await session.execute(
        select(FinancialTransaction).order_by(FinancialTransaction.transaction_date.desc())
    )
    return list(result.scalars().all())


def make_reconciliation_response(
    transactions: list[FinancialTransaction],
) -> ReconciliationResponse:
    total_volume = sum(t.amount for t in transactions)
    matched = [t for t in transactions if t.status == "matched"]
    exceptions = [t for t in transactions if t.status == "exception"]
    pending = [t for t in transactions if t.status == "pending"]
    exception_value = sum(abs(t.amount - t.expected_amount) for t in exceptions)
    summary = ReconciliationSummary(
        period_label="Last 12 weeks",
        total_transactions=len(transactions),
        matched_count=len(matched),
        exception_count=len(exceptions),
        pending_count=len(pending),
        total_volume=total_volume,
        matched_volume=sum(t.amount for t in matched),
        exception_value=exception_value,
        match_rate=round((len(matched) / len(transactions)) * 100, 1) if transactions else 0,
    )
    items = [
        ReconciliationItem(
            id=t.id,
            date=t.transaction_date.isoformat(),
            reference=t.reference,
            category=t.category,
            expected_amount=t.expected_amount,
            actual_amount=t.amount,
            variance=round(t.amount - t.expected_amount, 2),
            status=t.status,
        )
        for t in transactions
    ]
    return ReconciliationResponse(summary=summary, items=items)


def make_forecast_response(transactions: list[FinancialTransaction]) -> ForecastResponse:
    if not transactions:
        return ForecastResponse(
            horizon_weeks=6,
            current_cash=0,
            ending_cash=0,
            change_percent=0,
            confidence_label="Limited",
            points=[],
        )

    weekly_net: dict[date, float] = defaultdict(float)
    for transaction in transactions:
        week_start = transaction.transaction_date - timedelta(days=transaction.transaction_date.weekday())
        signed_amount = transaction.amount if transaction.direction == "inflow" else -transaction.amount
        weekly_net[week_start] += signed_amount

    ordered_weeks = sorted(weekly_net)
    net_values = np.array([weekly_net[week] for week in ordered_weeks], dtype=float)
    model = ExponentialSmoothing(net_values, trend="add", initialization_method="estimated").fit()
    future = np.asarray(model.forecast(6), dtype=float)

    base_cash = 186000.0
    actual_points: list[ForecastPoint] = []
    running_cash = base_cash
    for week in ordered_weeks:
        running_cash += weekly_net[week]
        actual_points.append(
            ForecastPoint(
                period=week.isoformat(),
                label=week.strftime("%b %-d"),
                actual=round(running_cash, 2),
                is_forecast=False,
            )
        )

    current_cash = actual_points[-1].actual or base_cash
    future_points: list[ForecastPoint] = []
    future_cash = current_cash
    residual = float(np.std(model.resid)) if len(model.resid) > 1 else 2500.0
    for index, value in enumerate(future, start=1):
        future_cash += value
        period = ordered_weeks[-1] + timedelta(days=index * 7)
        spread = residual * (1 + index * 0.12)
        future_points.append(
            ForecastPoint(
                period=period.isoformat(),
                label=period.strftime("%b %-d"),
                forecast=round(future_cash, 2),
                lower=round(future_cash - spread, 2),
                upper=round(future_cash + spread, 2),
                is_forecast=True,
            )
        )

    change_percent = ((future_cash - current_cash) / current_cash) * 100 if current_cash else 0
    return ForecastResponse(
        horizon_weeks=6,
        current_cash=round(current_cash, 2),
        ending_cash=round(future_cash, 2),
        change_percent=round(change_percent, 1),
        confidence_label="Directional · 80% range",
        points=actual_points + future_points,
    )


def make_summary(
    transactions: list[FinancialTransaction], forecast: ForecastResponse, reconciliation: ReconciliationSummary
) -> dict:
    today = date.fromisoformat(today_iso())
    incoming_30d = sum(
        t.amount for t in transactions if t.direction == "inflow" and t.transaction_date >= today - timedelta(days=30)
    )
    outgoing_30d = sum(
        t.amount for t in transactions if t.direction == "outflow" and t.transaction_date >= today - timedelta(days=30)
    )
    weekly_burn = max(outgoing_30d / 4.3, 1)
    return {
        "cash_balance": forecast.current_cash,
        "cash_delta_percent": forecast.change_percent,
        "incoming_30d": round(incoming_30d, 2),
        "outgoing_30d": round(outgoing_30d, 2),
        "runway_weeks": round(forecast.current_cash / weekly_burn, 1),
        "reconciliation_rate": reconciliation.match_rate,
        "open_exceptions": reconciliation.exception_count + reconciliation.pending_count,
        "data_as_of": today_iso(),
    }