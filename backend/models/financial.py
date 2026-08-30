from typing import Literal

from pydantic import BaseModel, Field


TransactionStatus = Literal["matched", "exception", "pending"]
InsightPriority = Literal["high", "medium", "low"]


class ReconciliationItem(BaseModel):
    id: str
    date: str
    reference: str
    category: str
    expected_amount: float
    actual_amount: float
    variance: float
    status: TransactionStatus


class ReconciliationSummary(BaseModel):
    period_label: str
    total_transactions: int
    matched_count: int
    exception_count: int
    pending_count: int
    total_volume: float
    matched_volume: float
    exception_value: float
    match_rate: float = Field(ge=0, le=100)


class ReconciliationResponse(BaseModel):
    summary: ReconciliationSummary
    items: list[ReconciliationItem]


class ForecastPoint(BaseModel):
    period: str
    label: str
    actual: float | None = None
    forecast: float | None = None
    lower: float | None = None
    upper: float | None = None
    is_forecast: bool


class ForecastResponse(BaseModel):
    horizon_weeks: int
    current_cash: float
    ending_cash: float
    change_percent: float
    confidence_label: str
    points: list[ForecastPoint]


class Insight(BaseModel):
    id: str
    priority: InsightPriority
    title: str
    body: str
    metric_label: str
    metric_value: str
    action: str
    source: str


class CfoResponse(BaseModel):
    generated_by: str
    disclaimer: str
    insights: list[Insight]


class DashboardSummary(BaseModel):
    cash_balance: float
    cash_delta_percent: float
    incoming_30d: float
    outgoing_30d: float
    runway_weeks: float
    reconciliation_rate: float
    open_exceptions: int
    data_as_of: str


class DashboardResponse(BaseModel):
    summary: DashboardSummary
    reconciliation: ReconciliationSummary
    forecast: ForecastResponse
    insights: list[Insight]