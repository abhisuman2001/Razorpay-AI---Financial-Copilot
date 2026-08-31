from datetime import date, datetime, timezone
from typing import Any
from uuid import uuid4
import os

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from ai.providers import OllamaProvider
from models.cfo import (
    CfoChatResponse,
    CfoSource,
    DailyInsight,
    DailyInsightsResponse,
    FinancialToolResult,
)
from services.financial_tools import TOOL_REGISTRY


def money(value: int | None) -> str:
    if value is None:
        return "not available"
    return f"₹{value / 100:,.0f}"


def percent(value: float | None) -> str:
    return "not available" if value is None else f"{value:.2f}%"


def choose_tools(question: str) -> list[str]:
    text = question.lower()
    if any(word in text for word in ["customer", "valuable", "buyer", "repeat"]):
        return ["get_top_customers", "get_customer_statistics", "get_revenue", "get_refunds"]
    if any(word in text for word in ["settlement", "reconcil", "mismatch", "lower than expected"]):
        return ["get_settlement_summary", "get_reconciliation_exceptions", "get_refunds"]
    if any(word in text for word in ["cash", "runway", "next month", "enough", "liquidity"]):
        return ["get_cash_balance", "get_cashflow_forecast", "get_expenses", "get_settlement_summary"]
    if any(word in text for word in ["revenue", "sales", "income", "fall", "decline"]):
        return ["get_revenue", "get_failed_payments", "get_refunds", "get_settlement_summary"]
    if any(word in text for word in ["risk", "concern", "today", "worry", "problem"]):
        return ["get_cashflow_forecast", "get_reconciliation_exceptions", "get_failed_payments", "get_revenue"]
    return ["get_revenue", "get_expenses", "get_cash_balance", "get_reconciliation_exceptions", "get_cashflow_forecast"]


async def collect_context(
    session: AsyncSession, tool_names: list[str]
) -> list[FinancialToolResult]:
    context: list[FinancialToolResult] = []
    for name in tool_names:
        context.append(await TOOL_REGISTRY[name](session))
    return context


def build_sources(context: list[FinancialToolResult]) -> list[CfoSource]:
    sources: list[CfoSource] = []
    for tool in context:
        for index, reference in enumerate(tool.source_refs):
            sources.append(CfoSource(
                id=f"{tool.tool_name}:{index + 1}", tool_name=tool.tool_name,
                label=reference, classification=tool.classification, period=tool.period_label,
            ))
    return sources


def result_map(context: list[FinancialToolResult]) -> dict[str, dict[str, Any]]:
    return {item.tool_name: item.data for item in context}


def describe_context(context: list[FinancialToolResult]) -> tuple[list[str], list[str]]:
    data = result_map(context)
    facts: list[str] = []
    predictions: list[str] = []
    if revenue := data.get("get_revenue"):
        facts.append(
            f"Captured revenue this month is {money(revenue['current_month_revenue'])}, "
            f"a {percent(revenue['change_percent'])} change from the previous month."
        )
    if expenses := data.get("get_expenses"):
        facts.append(
            f"Booked expenses this month are {money(expenses['current_month_expenses'])}, "
            f"a {percent(expenses['change_percent'])} change from the previous month."
        )
    if cash := data.get("get_cash_balance"):
        facts.append(
            f"Recorded cash balance is {money(cash['current_cash_balance'])}; "
            f"last 30-day net cash flow is {money(cash['last_30_day_net_cashflow'])}."
        )
    if failures := data.get("get_failed_payments"):
        facts.append(
            f"This month has {failures['current_month_failed_count']:,} failed payments "
            f"representing {money(failures['current_month_failed_amount'])}."
        )
    if refunds := data.get("get_refunds"):
        facts.append(
            f"Processed refunds this month total {money(refunds['processed_refund_amount'])} "
            f"across {refunds['processed_refund_count']:,} refunds."
        )
    if settlements := data.get("get_settlement_summary"):
        facts.append(
            f"Net settled cash over the last 30 days is {money(settlements['net_settlement'])} "
            f"after {money(settlements['refund_amount'])} of refunds, {money(settlements['fees'])} of fees, "
            f"and {money(settlements['taxes'])} of taxes."
        )
    if reconciliation := data.get("get_reconciliation_exceptions"):
        facts.append(
            f"The 90-day reconciliation queue contains {reconciliation['total_exceptions']:,} exceptions "
            f"and {money(reconciliation['total_discrepancy'])} in absolute discrepancy."
        )
    if customers := data.get("get_top_customers"):
        top = customers["customers"][0] if customers["customers"] else None
        if top:
            facts.append(
                f"The highest-value customer in the last 90 days is {top['name']} with "
                f"{money(top['captured_revenue'])} in captured revenue."
            )
    if statistics := data.get("get_customer_statistics"):
        facts.append(
            f"There are {statistics['active_paying_customers']:,} active paying customers; "
            f"the repeat-customer rate is {percent(statistics['repeat_customer_rate_percent'])}."
        )
    if forecast := data.get("get_cashflow_forecast"):
        predictions.append(
            f"Prediction: the 30-day model forecasts {money(forecast['forecasted_balance'])} in cash, "
            f"with a lowest 80% lower bound of {money(forecast['lowest_balance_lower_bound'])}."
        )
    return facts, predictions


def deterministic_explanation(
    question: str, context: list[FinancialToolResult]
) -> tuple[str, list[str], list[str], list[str], list[str], bool]:
    data = result_map(context)
    facts, predictions = describe_context(context)
    reasoning: list[str] = []
    recommendations: list[str] = []
    text = question.lower()

    if "get_top_customers" in data:
        reasoning.append("Customers are ranked by recorded captured payment value over the same 90-day period.")
        recommendations.append("Protect service quality for top customers and review concentration before offering incentives.")
    elif "get_reconciliation_exceptions" in data and any(word in text for word in ["settlement", "reconcil", "mismatch", "problem"]):
        reconciliation = data["get_reconciliation_exceptions"]
        reasoning.append("Expected settlement is compared with actual settlement using gross payment minus refunds, fees, and taxes.")
        reasoning.append("Net differences are separated from component-only differences and unresolved links.")
        recommendations.append(f"Review the largest exceptions first; the queue contains {reconciliation['mismatched']:,} net mismatches and {reconciliation['unresolved']:,} unresolved records.")
    elif "get_cashflow_forecast" in data and any(word in text for word in ["cash", "month", "enough", "liquidity", "risk", "concern", "today"]):
        forecast = data["get_cashflow_forecast"]
        reasoning.append("Recorded cash is separated from the 30-day Holt-Winters prediction and its 80% uncertainty range.")
        recommendations.append("Use the lower forecast bound as a planning guardrail, not as a guaranteed outcome.")
        risks = forecast.get("risks", [])
        if risks:
            recommendations.append(f"Monitor {risks[0]['category'].lower()}: {risks[0]['title']}.")
    elif "get_revenue" in data:
        revenue = data["get_revenue"]
        direction = "lower" if revenue["change_amount"] < 0 else "higher"
        reasoning.append(f"Captured revenue is {direction} than the previous month by {money(abs(revenue['change_amount']))}.")
        reasoning.append("Payment failures, refunds, and settled cash are shown separately so correlation is not presented as causation.")
        recommendations.append("Compare the leading failure reasons and refund reasons before attributing the revenue change to one cause.")
    else:
        reasoning.append("The response uses only available structured tool results and does not infer missing financial data.")
        recommendations.append("Ask about revenue, settlements, cash, risks, customers, or reconciliation for a more focused answer.")

    insufficient = any(item.insufficient_data for item in context) or not (facts or predictions)
    if insufficient:
        answer = "The available data is insufficient for a complete conclusion. " + " ".join(facts + predictions)
    else:
        answer = "Facts: " + " ".join(facts)
        if predictions:
            answer += " " + " ".join(predictions)
        answer += " Reasoning: " + " ".join(reasoning)
    return answer, facts, predictions, reasoning, recommendations, insufficient


async def answer_question(session: AsyncSession, question: str) -> CfoChatResponse:
    tool_names = choose_tools(question)
    context = await collect_context(session, tool_names)
    fallback, facts, predictions, reasoning, recommendations, insufficient = deterministic_explanation(question, context)
    mode = "deterministic"
    answer = fallback
    provider_message = "Answered by deterministic financial tools; local Ollama is disabled."

    if os.environ.get("AI_CFO_PROVIDER", "deterministic").lower() == "ollama":
        try:
            answer = await OllamaProvider().generate(question, context)
            mode = "ollama"
            provider_message = "Local Ollama rendered the explanation from structured tool context."
        except (httpx.HTTPError, KeyError, TypeError, ValueError):
            mode = "deterministic_fallback"
            provider_message = "Local Ollama was unavailable or ungrounded; deterministic fallback returned the answer."

    return CfoChatResponse(
        id=f"msg_{uuid4().hex[:12]}", question=question, answer=answer, mode=mode,
        facts=facts, predictions=predictions, reasoning=reasoning,
        recommendations=recommendations, sources=build_sources(context),
        tools_used=tool_names, insufficient_data=insufficient,
        provider_message=provider_message,
    )


async def daily_insights(session: AsyncSession) -> DailyInsightsResponse:
    tool_names = [
        "get_reconciliation_exceptions", "get_cashflow_forecast", "get_revenue",
        "get_failed_payments", "get_refunds",
    ]
    context = await collect_context(session, tool_names)
    data = result_map(context)
    reconciliation = data["get_reconciliation_exceptions"]
    forecast = data["get_cashflow_forecast"]
    revenue = data["get_revenue"]
    failures = data["get_failed_payments"]
    refunds = data["get_refunds"]
    leading_risk = forecast["risks"][0]
    failure_change = failures["count_change_percent"]
    insights = [
        DailyInsight(
            id="daily-reconciliation", category="Reconciliation",
            severity="high" if reconciliation["mismatched"] or reconciliation["unresolved"] else "low",
            title="Reconciliation exceptions need attention",
            summary=f"The current 90-day queue has {reconciliation['mismatched']:,} mismatches, {reconciliation['partially_matched']:,} partial matches, and {reconciliation['unresolved']:,} unresolved records.",
            metric_label="Absolute discrepancy", metric_value=money(reconciliation["total_discrepancy"]),
            classification="fact", source_tool="get_reconciliation_exceptions",
            source_ref="deterministic_reconciliation_engine", action="Review the largest reconciliation problems",
        ),
        DailyInsight(
            id="daily-cashflow", category="Cash flow", severity=leading_risk["severity"],
            title=leading_risk["title"], summary=leading_risk["description"],
            metric_label="30-day forecasted balance", metric_value=money(forecast["forecasted_balance"]),
            classification="prediction", source_tool="get_cashflow_forecast",
            source_ref="cashflow_forecast_30", action="Open the cash-flow forecast",
        ),
        DailyInsight(
            id="daily-revenue", category="Revenue",
            severity="medium" if revenue["change_amount"] < 0 else "low",
            title="Revenue is lower than last month" if revenue["change_amount"] < 0 else "Revenue is ahead of last month",
            summary=f"Captured revenue changed by {percent(revenue['change_percent'])} compared with the previous calendar month.",
            metric_label="Current month revenue", metric_value=money(revenue["current_month_revenue"]),
            classification="fact", source_tool="get_revenue", source_ref="payments.status=captured",
            action="Ask why revenue changed",
        ),
        DailyInsight(
            id="daily-failures", category="Payment failures",
            severity="high" if failure_change is not None and failure_change > 25 else "medium" if failures["current_month_failed_count"] else "low",
            title="Payment failures are affecting conversion",
            summary=f"There are {failures['current_month_failed_count']:,} failed payments this month, a {percent(failure_change)} change from last month.",
            metric_label="Failed payment value", metric_value=money(failures["current_month_failed_amount"]),
            classification="fact", source_tool="get_failed_payments", source_ref="failed_payments",
            action="Review leading failure reasons",
        ),
        DailyInsight(
            id="daily-refunds", category="Refunds",
            severity="medium" if (refunds["refund_rate_percent"] or 0) > 5 else "low",
            title="Refunds are reducing retained revenue",
            summary=f"Processed refunds represent {percent(refunds['refund_rate_percent'])} of captured revenue this month.",
            metric_label="Processed refunds", metric_value=money(refunds["processed_refund_amount"]),
            classification="fact", source_tool="get_refunds", source_ref="refunds.status=processed",
            action="Review refund reasons",
        ),
    ]
    return DailyInsightsResponse(
        as_of_date=date.fromisoformat(forecast["as_of_date"]),
        generated_at=datetime.now(timezone.utc), mode="deterministic",
        disclaimer="Insights are generated on request from deterministic financial tools. Predictions are labeled and no LLM calculates financial numbers.",
        insights=insights,
    )