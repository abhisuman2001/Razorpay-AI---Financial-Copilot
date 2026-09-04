"""
Deterministic Financial Health Score calculation.

The score is calculated ENTIRELY in the backend using existing financial data.
The LLM never calculates or modifies this score.
"""

from datetime import date, timedelta
from typing import TypedDict

from sqlalchemy.ext.asyncio import AsyncSession

from lib.dates import today_iso
from services.cashflow import build_cashflow_forecast
from services.financial_tools import (
    get_cash_balance,
    get_failed_payments,
    get_reconciliation_exceptions,
    get_refunds,
    get_revenue,
)


class ComponentScore(TypedDict):
    """Individual component of the health score."""

    name: str
    score: float
    weight: float
    explanation: str
    status: str  # "excellent", "good", "fair", "poor"


class HealthScore(TypedDict):
    """Complete financial health score."""

    overall_score: float
    overall_explanation: str
    overall_status: str
    components: list[ComponentScore]
    as_of_date: str
    calculation_method: str


def _status(score: float) -> str:
    """Determine status label from score."""
    if score >= 85:
        return "excellent"
    if score >= 70:
        return "good"
    if score >= 50:
        return "fair"
    return "poor"


async def calculate_health_score(session: AsyncSession) -> HealthScore:
    """
    Calculate financial health score deterministically.

    Components:
    1. Cash flow stability (25%)
    2. Revenue stability (20%)
    3. Payment success rate (20%)
    4. Reconciliation health (20%)
    5. Refund risk (10%)
    6. Forecast risk (5%)
    """
    today = date.fromisoformat(today_iso())

    # Gather financial data using existing tools
    cash_data = await get_cash_balance(session)
    revenue_data = await get_revenue(session)
    failures_data = await get_failed_payments(session)
    refunds_data = await get_refunds(session)
    reconciliation_data = await get_reconciliation_exceptions(session)
    forecast = await build_cashflow_forecast(session, 30)

    components: list[ComponentScore] = []

    # 1. Cash flow stability (25%)
    net_cashflow = cash_data.data["last_30_day_net_cashflow"]
    current_balance = cash_data.data["current_cash_balance"]
    cashflow_ratio = net_cashflow / current_balance if current_balance else 0
    if cashflow_ratio > 0:
        cashflow_score = min(100, 75 + (cashflow_ratio * 100))
    elif cashflow_ratio > -0.1:
        cashflow_score = 60
    else:
        cashflow_score = max(20, 60 + (cashflow_ratio * 200))

    components.append(
        {
            "name": "Cash Flow Stability",
            "score": round(cashflow_score, 1),
            "weight": 0.25,
            "explanation": (
                f"Net cash flow over 30 days is ₹{net_cashflow / 100:,.0f}. "
                + (
                    "Positive and healthy."
                    if net_cashflow > 0
                    else "Negative, monitor burn rate carefully."
                )
            ),
            "status": _status(cashflow_score),
        }
    )

    # 2. Revenue stability (20%)
    revenue_change_percent = revenue_data.data.get("change_percent")
    if revenue_change_percent is None:
        revenue_score = 50.0
        revenue_explanation = "Insufficient historical data to assess revenue stability."
    elif revenue_change_percent >= 0:
        revenue_score = min(100, 75 + revenue_change_percent)
        revenue_explanation = f"Revenue grew {revenue_change_percent}% vs previous month. Strong performance."
    elif revenue_change_percent >= -10:
        revenue_score = 65 + revenue_change_percent
        revenue_explanation = f"Revenue declined {abs(revenue_change_percent)}% vs previous month. Monitor closely."
    else:
        revenue_score = max(20, 65 + revenue_change_percent)
        revenue_explanation = f"Revenue declined {abs(revenue_change_percent)}% vs previous month. Urgent attention needed."

    components.append(
        {
            "name": "Revenue Stability",
            "score": round(revenue_score, 1),
            "weight": 0.20,
            "explanation": revenue_explanation,
            "status": _status(revenue_score),
        }
    )

    # 3. Payment success rate (20%)
    captured_count = revenue_data.data["current_month_captured_payments"]
    failed_count = failures_data.data["current_month_failed_count"]
    total_attempts = captured_count + failed_count
    success_rate = (captured_count / total_attempts * 100) if total_attempts else 0
    payment_score = success_rate

    components.append(
        {
            "name": "Payment Success Rate",
            "score": round(payment_score, 1),
            "weight": 0.20,
            "explanation": f"Success rate is {success_rate:.1f}% with {failed_count:,} failures this month.",
            "status": _status(payment_score),
        }
    )

    # 4. Reconciliation health (20%)
    recon_rate = reconciliation_data.data["reconciliation_rate"]
    recon_score = recon_rate

    components.append(
        {
            "name": "Reconciliation Health",
            "score": round(recon_score, 1),
            "weight": 0.20,
            "explanation": f"Reconciliation rate is {recon_rate:.1f}% with ₹{reconciliation_data.data['total_discrepancy'] / 100:,.0f} in discrepancies.",
            "status": _status(recon_score),
        }
    )

    # 5. Refund risk (10%)
    refund_rate = refunds_data.data.get("refund_rate_percent") or 0
    refund_score = max(0, 100 - (refund_rate * 5))  # 20% refund = 0 score

    components.append(
        {
            "name": "Refund Risk",
            "score": round(refund_score, 1),
            "weight": 0.10,
            "explanation": f"Refund rate is {refund_rate:.2f}% of captured revenue. {'Healthy level.' if refund_rate < 5 else 'High, investigate reasons.'}",
            "status": _status(refund_score),
        }
    )

    # 6. Forecast risk (5%)
    forecast_balance = forecast.forecasted_balance
    forecast_score = 100 if forecast_balance > current_balance * 0.8 else 50

    high_severity_risks = sum(1 for risk in forecast.risks if risk.severity == "high")
    forecast_score -= high_severity_risks * 15
    forecast_score = max(0, forecast_score)

    components.append(
        {
            "name": "Forecast Risk",
            "score": round(forecast_score, 1),
            "weight": 0.05,
            "explanation": f"30-day forecast shows {len(forecast.risks)} risks, {high_severity_risks} high-severity.",
            "status": _status(forecast_score),
        }
    )

    # Calculate overall weighted score
    overall_score = sum(comp["score"] * comp["weight"] for comp in components)

    # Generate overall explanation
    weak_areas = [comp for comp in components if comp["score"] < 60]
    if not weak_areas:
        overall_explanation = "All financial health indicators are performing well."
    elif len(weak_areas) == 1:
        overall_explanation = f"{weak_areas[0]['name']} needs attention."
    else:
        names = ", ".join(comp["name"] for comp in weak_areas[:-1])
        overall_explanation = f"{names}, and {weak_areas[-1]['name']} need attention."

    return {
        "overall_score": round(overall_score, 1),
        "overall_explanation": overall_explanation,
        "overall_status": _status(overall_score),
        "components": components,
        "as_of_date": today.isoformat(),
        "calculation_method": "Deterministic weighted scoring · No LLM calculations",
    }
