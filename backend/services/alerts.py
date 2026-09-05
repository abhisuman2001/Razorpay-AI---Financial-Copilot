"""
Proactive financial alerts detection using deterministic backend rules.

NO LLM is used to determine whether a financial risk exists.
All thresholds and rules are explicit and deterministic.

Each alert now includes:
  - what_happened:  concise factual statement of the trigger condition
  - why_it_matters: business consequence of this pattern
  - financial_impact: quantified monetary / rate impact where calculable
  - recommended_action: the explicit next step
  - cta_label: short button label for the action
  - cta_path: frontend route the CTA navigates to
"""

from datetime import date
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

# Numeric severity rank used for multi-key sorting
_SEVERITY_RANK: dict[AlertSeverity, int] = {
    "critical": 0,
    "high": 1,
    "medium": 2,
    "low": 3,
}

# Business-impact score per category (higher → shown first within same severity)
_CATEGORY_IMPACT: dict[str, int] = {
    "Cash Flow": 100,
    "Revenue": 90,
    "Reconciliation": 80,
    "Payment Failures": 70,
    "Forecast": 60,
    "Refunds": 50,
}


class Alert(TypedDict):
    """Financial alert structure."""

    id: str
    severity: AlertSeverity
    category: str
    title: str
    metric_label: str
    metric_value: str
    # Existing narrative fields
    explanation: str
    recommended_action: str
    # New actionable fields
    what_happened: str
    why_it_matters: str
    financial_impact: str
    cta_label: str
    cta_path: str
    detected_at: str
    source: str


def _sort_key(alert: Alert) -> tuple[int, int]:
    """Sort primarily by severity rank, then by category business-impact (descending)."""
    return (
        _SEVERITY_RANK[alert["severity"]],
        -_CATEGORY_IMPACT.get(alert["category"], 0),
    )


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
    - High-severity forecast risk
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

    # ─── 1. Negative cash flow risk ───────────────────────────────────────────
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
                "what_happened": (
                    f"Net cash flow over the last 30 days is ₹{net_cashflow / 100:,.0f}, "
                    f"burning ₹{burn_rate / 100:,.0f} per day."
                ),
                "why_it_matters": (
                    "Sustained negative cash flow erodes the operating buffer. "
                    f"At this burn rate, approximately {days_remaining} days of runway remain."
                ),
                "financial_impact": (
                    f"₹{burn_rate / 100:,.0f}/day burn · {days_remaining} days runway · "
                    f"current balance ₹{current_balance / 100:,.0f}"
                ),
                "explanation": (
                    f"Cash is decreasing at ₹{burn_rate / 100:,.0f}/day. "
                    f"At current burn rate, approximately {days_remaining} days of runway remain."
                ),
                "recommended_action": (
                    "Review expense breakdown and accelerate collections. "
                    "Open the cash-flow forecast to model scenario outcomes."
                ),
                "cta_label": "Open cash-flow forecast",
                "cta_path": "/forecast",
                "detected_at": today.isoformat(),
                "source": "cash_balance_tracker",
            }
        )

    # ─── 2. Unusual revenue decline ───────────────────────────────────────────
    revenue_change_percent = revenue_data.data.get("change_percent")
    if revenue_change_percent is not None and revenue_change_percent < -15:
        current_rev = revenue_data.data["current_month_revenue"]
        prev_rev = revenue_data.data["previous_month_revenue"]
        change_amount = current_rev - prev_rev

        severity = "critical" if revenue_change_percent < -30 else "high"
        alerts.append(
            {
                "id": "revenue-decline",
                "severity": severity,
                "category": "Revenue",
                "title": "Significant revenue decline",
                "metric_label": "Revenue change",
                "metric_value": f"{revenue_change_percent:.1f}%",
                "what_happened": (
                    f"Captured revenue fell {abs(revenue_change_percent):.1f}% month-on-month, "
                    f"from ₹{prev_rev / 100:,.0f} to ₹{current_rev / 100:,.0f}."
                ),
                "why_it_matters": (
                    "A decline of this magnitude can signal lost customers, gateway issues, "
                    "or seasonal headwinds that require immediate investigation."
                ),
                "financial_impact": (
                    f"₹{abs(change_amount) / 100:,.0f} less revenue vs previous month "
                    f"({revenue_change_percent:.1f}%)"
                ),
                "explanation": (
                    f"Revenue decreased {abs(revenue_change_percent):.1f}% vs previous month. "
                    f"Current month captured revenue is ₹{current_rev / 100:,.0f}."
                ),
                "recommended_action": (
                    "Investigate payment failures, refund trends, and customer churn. "
                    "Review the sales pipeline in the AI CFO."
                ),
                "cta_label": "Investigate revenue",
                "cta_path": "/cfo",
                "detected_at": today.isoformat(),
                "source": "revenue_tracker",
            }
        )

    # ─── 3. Payment failure spike ─────────────────────────────────────────────
    failure_change_percent = failures_data.data.get("count_change_percent")
    if failure_change_percent is not None and failure_change_percent > 25:
        failed_count = failures_data.data["current_month_failed_count"]
        failed_amount = failures_data.data["current_month_failed_amount"]
        prev_count = failures_data.data["previous_month_failed_count"]

        severity = "critical" if failure_change_percent > 50 else "high"
        alerts.append(
            {
                "id": "payment-failure-spike",
                "severity": severity,
                "category": "Payment Failures",
                "title": "Payment failure rate increased",
                "metric_label": "Failed payment count",
                "metric_value": f"{failed_count:,}",
                "what_happened": (
                    f"Payment failures rose {failure_change_percent:.1f}% month-on-month, "
                    f"from {prev_count:,} to {failed_count:,} failures."
                ),
                "why_it_matters": (
                    "Higher failure rates directly reduce captured revenue and damage customer trust. "
                    f"₹{failed_amount / 100:,.0f} in potential revenue was lost this month."
                ),
                "financial_impact": (
                    f"₹{failed_amount / 100:,.0f} in failed payment value · "
                    f"{failed_count:,} failed transactions (+{failure_change_percent:.1f}%)"
                ),
                "explanation": (
                    f"Failures increased {failure_change_percent:.1f}% vs previous month, "
                    f"representing ₹{failed_amount / 100:,.0f} in lost revenue."
                ),
                "recommended_action": (
                    "Review the top error codes, test the payment gateway, "
                    "and contact customers with retryable failures."
                ),
                "cta_label": "Review pending transactions",
                "cta_path": "/cfo",
                "detected_at": today.isoformat(),
                "source": "payment_failure_tracker",
            }
        )

    # ─── 4. Refund spike ──────────────────────────────────────────────────────
    refund_rate = refunds_data.data.get("refund_rate_percent") or 0
    if refund_rate > 8:
        refund_amount = refunds_data.data["processed_refund_amount"]
        refund_count = refunds_data.data["processed_refund_count"]
        captured_rev = refunds_data.data["captured_revenue"]

        severity = "high" if refund_rate > 15 else "medium"
        alerts.append(
            {
                "id": "refund-spike",
                "severity": severity,
                "category": "Refunds",
                "title": "High refund rate detected",
                "metric_label": "Refund rate",
                "metric_value": f"{refund_rate:.2f}%",
                "what_happened": (
                    f"Refunds represent {refund_rate:.2f}% of captured revenue this month — "
                    f"{refund_count:,} refunds totalling ₹{refund_amount / 100:,.0f}."
                ),
                "why_it_matters": (
                    "Elevated refund rates reduce net retained revenue and may indicate "
                    "product quality, fulfilment, or customer-experience issues."
                ),
                "financial_impact": (
                    f"₹{refund_amount / 100:,.0f} returned to customers out of "
                    f"₹{captured_rev / 100:,.0f} captured ({refund_rate:.2f}%)"
                ),
                "explanation": (
                    f"Refunds represent {refund_rate:.2f}% of captured revenue "
                    f"({refund_count:,} refunds totaling ₹{refund_amount / 100:,.0f})."
                ),
                "recommended_action": (
                    "Analyze the top refund reasons and address product or service quality issues."
                ),
                "cta_label": "Review reconciliation",
                "cta_path": "/reconciliation",
                "detected_at": today.isoformat(),
                "source": "refund_tracker",
            }
        )

    # ─── 5. Reconciliation discrepancy ────────────────────────────────────────
    recon_rate = reconciliation_data.data["reconciliation_rate"]
    if recon_rate < 85:
        discrepancy = reconciliation_data.data["total_discrepancy"]
        exceptions = reconciliation_data.data["total_exceptions"]
        mismatched = reconciliation_data.data["mismatched"]
        unresolved = reconciliation_data.data["unresolved"]

        severity = "critical" if recon_rate < 70 else "high"
        alerts.append(
            {
                "id": "reconciliation-discrepancy",
                "severity": severity,
                "category": "Reconciliation",
                "title": "Low reconciliation rate",
                "metric_label": "Reconciliation rate",
                "metric_value": f"{recon_rate:.1f}%",
                "what_happened": (
                    f"Reconciliation rate is {recon_rate:.1f}% — below the 85% threshold. "
                    f"{mismatched:,} net mismatches and {unresolved:,} unresolved records found."
                ),
                "why_it_matters": (
                    "Unreconciled transactions mean reported financials may not reflect actual "
                    "settlements. Discrepancies can mask revenue leakage or over-deductions."
                ),
                "financial_impact": (
                    f"₹{discrepancy / 100:,.0f} in total discrepancies across "
                    f"{exceptions:,} exception records"
                ),
                "explanation": (
                    f"{exceptions:,} exceptions with ₹{discrepancy / 100:,.0f} in total discrepancies. "
                    "This impacts financial accuracy."
                ),
                "recommended_action": (
                    "Prioritise the largest discrepancies first and resolve unmatched settlements."
                ),
                "cta_label": "Review reconciliation",
                "cta_path": "/reconciliation",
                "detected_at": today.isoformat(),
                "source": "reconciliation_engine",
            }
        )

    # ─── 6. High pending/unresolved transactions ──────────────────────────────
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
                "what_happened": (
                    f"{pending:,} transactions are awaiting settlement and "
                    f"{unresolved:,} have no matched settlement record past the T+2 window."
                ),
                "why_it_matters": (
                    "A large pending queue delays accurate cash reporting and can hide "
                    "settlement failures or gateway processing delays."
                ),
                "financial_impact": (
                    f"{total_pending:,} transactions blocking accurate reconciliation "
                    f"({pending:,} pending, {unresolved:,} unresolved)"
                ),
                "explanation": (
                    f"{pending:,} pending and {unresolved:,} unresolved transactions "
                    "are blocking accurate reconciliation."
                ),
                "recommended_action": (
                    "Review the pending queue and investigate unresolved settlement links."
                ),
                "cta_label": "Review reconciliation",
                "cta_path": "/reconciliation",
                "detected_at": today.isoformat(),
                "source": "reconciliation_queue",
            }
        )

    # ─── 7. High-severity forecast risks ──────────────────────────────────────
    high_risks = [risk for risk in forecast.risks if risk.severity == "high"]
    if high_risks:
        risk = high_risks[0]
        alerts.append(
            {
                "id": f"forecast-risk-{risk.id}",
                "severity": "high",
                "category": "Forecast",
                "title": risk.title,
                "metric_label": risk.metric_label,
                "metric_value": risk.metric_value,
                "what_happened": (
                    f"The 30-day cash-flow model flagged a high-severity risk in "
                    f"'{risk.category}': {risk.title}."
                ),
                "why_it_matters": risk.description,
                "financial_impact": f"{risk.metric_label}: {risk.metric_value}",
                "explanation": risk.description,
                "recommended_action": (
                    "Review the 30-day forecast and prepare contingency plans."
                ),
                "cta_label": "Open cash-flow forecast",
                "cta_path": "/forecast",
                "detected_at": today.isoformat(),
                "source": "forecast_risk_analyzer",
            }
        )

    # Sort: primary = severity (critical → low), secondary = category business-impact (descending)
    alerts.sort(key=_sort_key)

    return alerts
