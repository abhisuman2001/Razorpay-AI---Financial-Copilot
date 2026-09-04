"""
Proactive financial alerts detection using deterministic backend rules.

NO LLM is used to determine whether a financial risk exists.
All thresholds and rules are explicit and deterministic.
"""

from datetime import date, timedelta
from typing import Literal, TypedDict

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


AlertSeverity = Literal["critical", "high", "medium", "low"]


class Alert(TypedDict):
    """Financial alert structure."""

    id: str
    severity: AlertSeverity
    category: str
    title: str
    metric_label: str
    metric_value: str
    explanation: str
    recommended_action: str
    detected_at: str
    source: str


async def detect_alerts(session: AsyncSession) -> list[Alert]:
    """
    Detect important financial events using deterministic backend rules.

    Alerts:
    - Negative cash flow risk
    - Unusual revenue decline
    - Payment failure spike
    - Refund spike
    - Reconciliation discrepancy
    - High pending/unresolved transactions
    - Unusual expense increase
    """
    alerts: list[Alert] = []
    today = date.fromisoformat(today_iso())

    # Gather financial data
    cash_data = await get_cash_balance(session)
    revenue_data = await get_revenue(session)
    failures_data = await get_failed_payments(session)
    refunds_data = await get_refunds(session)
    reconciliation_data = await get_reconciliation_exceptions(session)
    forecast = await build_cashflow_forecast(session, 30)

    # 1. Negative cash flow risk
    net_cashflow = cash_data.data["last_30_day_net_cashflow"]
    if net_cashflow < 0:
        burn_rate = abs(net_cashflow / 30)
        current_balance = cash_data.data["current_cash_balance"]
        days_remaining = int(current_balance / burn_rate) if burn_rate > 0 else 999

        severity: AlertSeverity = "critical" if days_remaining < 30 else "high"
        alerts.append(
            {
                "id": "negative-cashflow",
                "severity": severity,
                "category": "Cash Flow",
                "title": "Negative cash flow detected",
                "metric_label": "30-day net cash flow",
                "metric_value": f"₹{net_cashflow / 100:,.0f}",
                "explanation": f"Cash is decreasing at ₹{burn_rate / 100:,.0f}/day. At current burn rate, approximately {days_remaining} days of runway remain.",
                "recommended_action": "Review expense breakdown and accelerate collections. Consider forecast scenarios.",
                "detected_at": today.isoformat(),
                "source": "cash_balance_tracker",
            }
        )

    # 2. Unusual revenue decline
    revenue_change_percent = revenue_data.data.get("change_percent")
    if revenue_change_percent is not None and revenue_change_percent < -15:
        severity = "critical" if revenue_change_percent < -30 else "high"
        alerts.append(
            {
                "id": "revenue-decline",
                "severity": severity,
                "category": "Revenue",
                "title": "Significant revenue decline",
                "metric_label": "Revenue change",
                "metric_value": f"{revenue_change_percent:.1f}%",
                "explanation": f"Revenue decreased {abs(revenue_change_percent):.1f}% vs previous month. Current month captured revenue is ₹{revenue_data.data['current_month_revenue'] / 100:,.0f}.",
                "recommended_action": "Investigate payment failures, refunds, and customer churn. Review sales pipeline.",
                "detected_at": today.isoformat(),
                "source": "revenue_tracker",
            }
        )

    # 3. Payment failure spike
    failure_change_percent = failures_data.data.get("count_change_percent")
    if failure_change_percent is not None and failure_change_percent > 25:
        severity = "critical" if failure_change_percent > 50 else "high"
        failed_count = failures_data.data["current_month_failed_count"]
        failed_amount = failures_data.data["current_month_failed_amount"]
        alerts.append(
            {
                "id": "payment-failure-spike",
                "severity": severity,
                "category": "Payment Failures",
                "title": "Payment failure rate increased",
                "metric_label": "Failed payment count",
                "metric_value": f"{failed_count:,}",
                "explanation": f"Failures increased {failure_change_percent:.1f}% vs previous month, representing ₹{failed_amount / 100:,.0f} in lost revenue.",
                "recommended_action": "Review error codes, test payment gateway, and contact failing customers.",
                "detected_at": today.isoformat(),
                "source": "payment_failure_tracker",
            }
        )

    # 4. Refund spike
    refund_rate = refunds_data.data.get("refund_rate_percent") or 0
    if refund_rate > 8:
        severity = "high" if refund_rate > 15 else "medium"
        refund_amount = refunds_data.data["processed_refund_amount"]
        refund_count = refunds_data.data["processed_refund_count"]
        alerts.append(
            {
                "id": "refund-spike",
                "severity": severity,
                "category": "Refunds",
                "title": "High refund rate detected",
                "metric_label": "Refund rate",
                "metric_value": f"{refund_rate:.2f}%",
                "explanation": f"Refunds represent {refund_rate:.2f}% of captured revenue ({refund_count:,} refunds totaling ₹{refund_amount / 100:,.0f}).",
                "recommended_action": "Analyze refund reasons and address product/service quality issues.",
                "detected_at": today.isoformat(),
                "source": "refund_tracker",
            }
        )

    # 5. Reconciliation discrepancy
    recon_rate = reconciliation_data.data["reconciliation_rate"]
    if recon_rate < 85:
        severity = "critical" if recon_rate < 70 else "high"
        discrepancy = reconciliation_data.data["total_discrepancy"]
        exceptions = reconciliation_data.data["total_exceptions"]
        alerts.append(
            {
                "id": "reconciliation-discrepancy",
                "severity": severity,
                "category": "Reconciliation",
                "title": "Low reconciliation rate",
                "metric_label": "Reconciliation rate",
                "metric_value": f"{recon_rate:.1f}%",
                "explanation": f"{exceptions:,} exceptions with ₹{discrepancy / 100:,.0f} in total discrepancies. This impacts financial accuracy.",
                "recommended_action": "Prioritize largest discrepancies and resolve unmatched settlements.",
                "detected_at": today.isoformat(),
                "source": "reconciliation_engine",
            }
        )

    # 6. High pending/unresolved transactions
    pending = reconciliation_data.data["pending"]
    unresolved = reconciliation_data.data["unresolved"]
    total_pending = pending + unresolved
    if total_pending > 50:
        severity = "high" if total_pending > 100 else "medium"
        alerts.append(
            {
                "id": "high-pending-transactions",
                "severity": severity,
                "category": "Reconciliation",
                "title": "Many pending transactions",
                "metric_label": "Pending + unresolved",
                "metric_value": f"{total_pending:,}",
                "explanation": f"{pending:,} pending and {unresolved:,} unresolved transactions are blocking accurate reconciliation.",
                "recommended_action": "Review pending queue and investigate unresolved settlement links.",
                "detected_at": today.isoformat(),
                "source": "reconciliation_queue",
            }
        )

    # 7. High-severity forecast risks
    high_risks = [risk for risk in forecast.risks if risk.severity == "high"]
    if high_risks:
        # Take the first high-severity risk
        risk = high_risks[0]
        alerts.append(
            {
                "id": f"forecast-risk-{risk.id}",
                "severity": "high",
                "category": "Forecast",
                "title": risk.title,
                "metric_label": risk.metric_label,
                "metric_value": risk.metric_value,
                "explanation": risk.description,
                "recommended_action": "Review the 30-day forecast and prepare contingency plans.",
                "detected_at": today.isoformat(),
                "source": "forecast_risk_analyzer",
            }
        )

    # Sort alerts by severity
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    alerts.sort(key=lambda alert: severity_order[alert["severity"]])

    return alerts
