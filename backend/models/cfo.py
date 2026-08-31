from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


ContextClassification = Literal["fact", "prediction"]
ChatMode = Literal["deterministic", "ollama", "deterministic_fallback"]


class FinancialToolResult(BaseModel):
    tool_name: str
    classification: ContextClassification
    period_label: str
    generated_at: datetime
    data: dict[str, Any]
    source_refs: list[str]
    insufficient_data: bool = False


class CfoSource(BaseModel):
    id: str
    tool_name: str
    label: str
    classification: ContextClassification
    period: str


class CfoChatRequest(BaseModel):
    question: str = Field(min_length=3, max_length=600)


class CfoChatResponse(BaseModel):
    id: str
    question: str
    answer: str
    mode: ChatMode
    facts: list[str]
    predictions: list[str]
    reasoning: list[str]
    recommendations: list[str]
    sources: list[CfoSource]
    tools_used: list[str]
    insufficient_data: bool
    read_only: bool = True
    provider_message: str


class DailyInsight(BaseModel):
    id: str
    category: str
    severity: Literal["high", "medium", "low"]
    title: str
    summary: str
    metric_label: str
    metric_value: str
    classification: ContextClassification
    source_tool: str
    source_ref: str
    action: str


class DailyInsightsResponse(BaseModel):
    as_of_date: date
    generated_at: datetime
    mode: ChatMode
    disclaimer: str
    insights: list[DailyInsight]