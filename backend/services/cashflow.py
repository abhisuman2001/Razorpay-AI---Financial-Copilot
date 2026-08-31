from collections import defaultdict
from datetime import date, timedelta
import os

import numpy as np
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from statsmodels.tsa.holtwinters import ExponentialSmoothing

from lib.dates import today_iso
from models.cashflow import (
    CashFlowForecastResponse,
    ForecastHorizon,
    ForecastRisk,
    HistoricalCashFlowPoint,
    PredictedCashFlowPoint,
)
from models.merchant_tables import DatasetRun, Expense, Settlement


OPENING_BALANCE = int(os.environ.get("OPENING_CASH_BALANCE_PAISE", "250000000"))
Z_80 = 1.2815515655446004


def _all_dates(start: date, end: date) -> list[date]:
    return [start + timedelta(days=offset) for offset in range((end - start).days + 1)]


def _fit_forecast(values: np.ndarray, horizon: int) -> tuple[np.ndarray, float]:
    """Explainable additive Holt-Winters with weekly seasonality and a damped trend."""
    model = ExponentialSmoothing(
        values,
        trend="add",
        damped_trend=True,
        seasonal="add",
        seasonal_periods=7,
        initialization_method="estimated",
    ).fit(optimized=True, remove_bias=True)
    predicted = np.maximum(np.asarray(model.forecast(horizon), dtype=float), 0)
    residual_std = max(float(np.std(model.resid, ddof=1)), 1.0)
    return predicted, residual_std


async def load_daily_cashflow(
    session: AsyncSession,
) -> tuple[list[HistoricalCashFlowPoint], np.ndarray, np.ndarray, date]:
    run = await session.scalar(select(DatasetRun).order_by(DatasetRun.generated_at.desc()).limit(1))
    if not run:
        raise ValueError("Synthetic financial dataset has not been generated")
    as_of = min(date.fromisoformat(today_iso()), run.period_end)
    dates = _all_dates(run.period_start, as_of)

    settled_rows = (await session.execute(
        select(Settlement.settlement_date, Settlement.net_settlement).where(
            Settlement.status == "settled",
            Settlement.settlement_date >= run.period_start,
            Settlement.settlement_date <= as_of,
        )
    )).all()
    expense_rows = (await session.execute(
        select(Expense.date, Expense.amount).where(
            Expense.date >= run.period_start,
            Expense.date <= as_of,
        )
    )).all()

    income_by_date: dict[date, int] = defaultdict(int)
    expenses_by_date: dict[date, int] = defaultdict(int)
    for settlement_date, amount in settled_rows:
        income_by_date[settlement_date] += amount
    for expense_date, amount in expense_rows:
        expenses_by_date[expense_date] += amount

    income = np.asarray([income_by_date[day] for day in dates], dtype=float)
    expenses = np.asarray([expenses_by_date[day] for day in dates], dtype=float)
    balance = OPENING_BALANCE
    history: list[HistoricalCashFlowPoint] = []
    for day, daily_income, daily_expense in zip(dates, income, expenses, strict=True):
        net = int(round(daily_income - daily_expense))
        balance += net
        history.append(HistoricalCashFlowPoint(
            date=day,
            daily_income=int(round(daily_income)),
            daily_expenses=int(round(daily_expense)),
            daily_net_cashflow=net,
            cumulative_cash_balance=balance,
        ))
    return history, income, expenses, as_of


def calculate_risks(
    history: list[HistoricalCashFlowPoint],
    forecast: list[PredictedCashFlowPoint],
    income_values: np.ndarray,
    expense_values: np.ndarray,
) -> list[ForecastRisk]:
    risks: list[ForecastRisk] = []
    lower_min = min(point.balance_lower for point in forecast)
    if lower_min < 0:
        risks.append(ForecastRisk(
            id="negative-cash", severity="high", category="Liquidity",
            title="Cash could fall below zero in the uncertainty range",
            description="The lower 80% balance path crosses zero. Protect a liquidity buffer before committing discretionary spend.",
            metric_label="Lowest lower bound", metric_value=f"₹{lower_min / 100:,.0f}",
            source="80% cumulative forecast range",
        ))
    else:
        buffer_ratio = lower_min / max(history[-1].cumulative_cash_balance, 1)
        risks.append(ForecastRisk(
            id="cash-buffer", severity="low" if buffer_ratio > 0.5 else "medium", category="Liquidity",
            title="Liquidity buffer remains positive",
            description="The lower 80% balance path stays above zero, but should still be monitored as new settlements arrive.",
            metric_label="Lowest lower bound", metric_value=f"₹{lower_min / 100:,.0f}",
            source="80% cumulative forecast range",
        ))

    recent_income = income_values[-90:]
    total_income = float(recent_income.sum())
    top_share = float(np.sort(recent_income)[-5:].sum() / total_income) if total_income else 0
    risks.append(ForecastRisk(
        id="income-concentration", severity="medium" if top_share > 0.28 else "low", category="Concentration",
        title="Income is concentrated on a small number of settlement days",
        description="A high share of recent cash receipts arrived on the five strongest days, increasing timing sensitivity.",
        metric_label="Top 5-day share", metric_value=f"{top_share * 100:.1f}%",
        source="Last 90 days of settled income",
    ))

    recent_net = np.asarray([point.daily_net_cashflow for point in history[-90:]], dtype=float)
    net_volatility = float(np.std(recent_net))
    mean_flow = max(abs(float(np.mean(recent_net))), 1.0)
    volatility_ratio = net_volatility / mean_flow
    risks.append(ForecastRisk(
        id="cash-volatility", severity="high" if volatility_ratio > 5 else "medium" if volatility_ratio > 2 else "low",
        category="Volatility", title="Daily net cash flow is uneven",
        description="Settlement batching and lumpy operating expenses create meaningful day-to-day cash movement.",
        metric_label="Volatility ratio", metric_value=f"{volatility_ratio:.1f}×",
        source="90-day standard deviation ÷ mean net flow",
    ))

    predicted_expenses = np.asarray([point.predicted_expenses for point in forecast], dtype=float)
    recent_expense_p90 = float(np.percentile(expense_values[-90:], 90))
    max_predicted_expense = float(predicted_expenses.max())
    expense_ratio = max_predicted_expense / max(recent_expense_p90, 1)
    risks.append(ForecastRisk(
        id="expense-spike", severity="high" if expense_ratio > 1.8 else "medium" if expense_ratio > 1.15 else "low",
        category="Expenses", title="Watch the largest forecast expense day",
        description="The model carries weekly expense seasonality forward; the largest projected outflow deserves a funding check.",
        metric_label="Largest predicted expense", metric_value=f"₹{max_predicted_expense / 100:,.0f}",
        source="Holt-Winters expense forecast",
    ))
    return risks


async def build_cashflow_forecast(
    session: AsyncSession, horizon: ForecastHorizon
) -> CashFlowForecastResponse:
    history, income_values, expense_values, as_of = await load_daily_cashflow(session)
    predicted_income, income_std = _fit_forecast(income_values, horizon)
    predicted_expenses, expense_std = _fit_forecast(expense_values, horizon)
    predicted_net = predicted_income - predicted_expenses
    combined_std = float(np.sqrt(income_std ** 2 + expense_std ** 2))
    current_balance = history[-1].cumulative_cash_balance
    running_balance = current_balance
    forecast: list[PredictedCashFlowPoint] = []
    for index in range(horizon):
        income = int(round(predicted_income[index]))
        expenses = int(round(predicted_expenses[index]))
        net = income - expenses
        running_balance += net
        uncertainty = int(round(Z_80 * combined_std * np.sqrt(index + 1)))
        forecast.append(PredictedCashFlowPoint(
            date=as_of + timedelta(days=index + 1),
            predicted_income=income,
            predicted_expenses=expenses,
            predicted_net_cashflow=net,
            predicted_balance=running_balance,
            balance_lower=running_balance - uncertainty,
            balance_upper=running_balance + uncertainty,
        ))

    chart_history = history[-90:]
    return CashFlowForecastResponse(
        horizon_days=horizon,
        as_of_date=as_of,
        history_start=history[0].date,
        history_end=history[-1].date,
        opening_cash_balance=OPENING_BALANCE,
        current_cash_balance=current_balance,
        expected_incoming=sum(point.predicted_income for point in forecast),
        expected_outgoing=sum(point.predicted_expenses for point in forecast),
        forecasted_balance=forecast[-1].predicted_balance,
        confidence_label="80% model uncertainty range",
        model_name="Additive Holt-Winters",
        methodology=(
            "Separate daily income and expense models use a damped trend with seven-day additive seasonality. "
            "Income is recognized on settled cash dates; expenses use booked expense dates. "
            "The balance range accumulates observed model residual uncertainty."
        ),
        historical=chart_history,
        forecast=forecast,
        risks=calculate_risks(history, forecast, income_values, expense_values),
    )