"""
Forecast explanation service.

Provides deterministic explanations for what's driving the cash flow forecast
and how confident we are in the predictions.
"""

from typing import TypedDict

import numpy as np

from models.cashflow import CashFlowForecastResponse


class ForecastDriver(TypedDict):
    """Individual driver of the forecast."""

    category: str
    label: str
    value: str
    explanation: str
    impact: str  # "positive", "negative", "neutral"


class ForecastExplanation(TypedDict):
    """Complete forecast explanation."""

    drivers: list[ForecastDriver]
    confidence_explanation: str
    confidence_factors: list[str]
    uncertainty_range_explanation: str


def explain_forecast(forecast: CashFlowForecastResponse, history_volatility: float) -> ForecastExplanation:
    """
    Generate deterministic explanations for what's driving the forecast.

    Args:
        forecast: The complete forecast response
        history_volatility: Standard deviation of historical daily net cash flow
    """
    drivers: list[ForecastDriver] = []

    # Income assumptions
    total_income = forecast.expected_incoming
    avg_daily_income = total_income / forecast.horizon_days
    drivers.append(
        {
            "category": "Income",
            "label": "Expected settlement income",
            "value": f"₹{total_income / 100:,.0f}",
            "explanation": f"Model predicts ₹{avg_daily_income / 100:,.0f}/day average over {forecast.horizon_days} days based on recent settlement patterns and weekly seasonality.",
            "impact": "positive",
        }
    )

    # Expense assumptions
    total_expenses = forecast.expected_outgoing
    avg_daily_expenses = total_expenses / forecast.horizon_days
    drivers.append(
        {
            "category": "Expenses",
            "label": "Expected operating expenses",
            "value": f"₹{total_expenses / 100:,.0f}",
            "explanation": f"Model predicts ₹{avg_daily_expenses / 100:,.0f}/day average based on booked expense history with damped trend and weekly patterns.",
            "impact": "negative",
        }
    )

    # Net change
    net_change = total_income - total_expenses
    drivers.append(
        {
            "category": "Net Change",
            "label": f"Projected {'gain' if net_change > 0 else 'burn'}",
            "value": f"₹{abs(net_change) / 100:,.0f}",
            "explanation": f"Net cash flow over {forecast.horizon_days} days. Balance {'increases' if net_change > 0 else 'decreases'} from ₹{forecast.current_cash_balance / 100:,.0f} to ₹{forecast.forecasted_balance / 100:,.0f}.",
            "impact": "positive" if net_change > 0 else "negative",
        }
    )

    # Find major positive drivers
    income_points = [point.predicted_income for point in forecast.forecast]
    max_income_day = max(income_points)
    max_income_index = income_points.index(max_income_day)
    max_income_date = forecast.forecast[max_income_index].date

    drivers.append(
        {
            "category": "Income",
            "label": "Peak settlement day",
            "value": f"₹{max_income_day / 100:,.0f}",
            "explanation": f"The largest predicted settlement day is {max_income_date.isoformat()}, reflecting weekly payment settlement cycles.",
            "impact": "positive",
        }
    )

    # Find major negative drivers
    expense_points = [point.predicted_expenses for point in forecast.forecast]
    max_expense_day = max(expense_points)
    max_expense_index = expense_points.index(max_expense_day)
    max_expense_date = forecast.forecast[max_expense_index].date

    drivers.append(
        {
            "category": "Expenses",
            "label": "Peak expense day",
            "value": f"₹{max_expense_day / 100:,.0f}",
            "explanation": f"The largest predicted expense day is {max_expense_date.isoformat()}, based on historical expense patterns.",
            "impact": "negative",
        }
    )

    # Forecast risks as drivers
    high_risks = [risk for risk in forecast.risks if risk.severity in ["high", "critical"]]
    for risk in high_risks:
        drivers.append(
            {
                "category": "Risk",
                "label": risk.title,
                "value": risk.metric_value,
                "explanation": risk.description,
                "impact": "negative",
            }
        )

    # Confidence explanation
    confidence_factors: list[str] = []

    # Data availability
    confidence_factors.append(
        f"Model trained on {(forecast.history_end - forecast.history_start).days} days of actual settlement and expense data."
    )

    # Volatility factor
    avg_balance = forecast.current_cash_balance
    volatility_ratio = (history_volatility / avg_balance * 100) if avg_balance else 0
    if volatility_ratio < 5:
        confidence_factors.append("Cash flow volatility is low; historical patterns are stable.")
    elif volatility_ratio < 15:
        confidence_factors.append("Cash flow volatility is moderate; predictions have reasonable uncertainty.")
    else:
        confidence_factors.append("Cash flow volatility is high; predictions have wide uncertainty ranges.")

    # Trend stability
    confidence_factors.append("Additive Holt-Winters with damped trend prevents unrealistic exponential projections.")

    # Seasonality
    confidence_factors.append("Weekly seasonality captures regular settlement and expense cycles.")

    # Risk assessment
    if len(high_risks) == 0:
        confidence_factors.append("No high-severity risks detected in the forecast period.")
    elif len(high_risks) == 1:
        confidence_factors.append(f"One high-severity risk detected: {high_risks[0]['title']}.")
    else:
        confidence_factors.append(f"{len(high_risks)} high-severity risks detected; exercise caution.")

    confidence_explanation = (
        f"This forecast uses {forecast.model_name} with a {forecast.confidence_label}. "
        f"Confidence is {'high' if len(high_risks) == 0 and volatility_ratio < 10 else 'moderate' if len(high_risks) <= 1 else 'limited'} "
        f"given current data quality and market volatility."
    )

    uncertainty_range_explanation = (
        "The shaded uncertainty band shows the 80% prediction interval. "
        "This means there's an 80% probability the actual balance will fall within this range, "
        "assuming settlement and expense patterns continue. "
        "The range widens over time as forecast uncertainty accumulates."
    )

    return {
        "drivers": drivers,
        "confidence_explanation": confidence_explanation,
        "confidence_factors": confidence_factors,
        "uncertainty_range_explanation": uncertainty_range_explanation,
    }
