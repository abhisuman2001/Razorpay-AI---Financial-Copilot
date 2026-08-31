from datetime import date
from typing import Literal

from pydantic import BaseModel, Field


WhyMetricId = Literal[
    "revenue", "cash_balance", "settlement_amount", "refund_rate",
    "payment_success_rate", "forecasted_balance", "reconciliation_exceptions",
]
ValueUnit = Literal["currency", "percent", "count"]


class DriverFinding(BaseModel):
    id: str
    label: str
    description: str
    current_value: float
    previous_value: float
    unit: ValueUnit
    change_amount: float
    change_percent: float | None
    change_summary: str
    direction: Literal["increased", "decreased", "unchanged"]
    effect: Literal["positive", "negative", "neutral"]
    impact_score: float = Field(ge=0)
    classification: Literal["fact", "prediction"]
    source_metrics: list[str]


class WhyMetricResponse(BaseModel):
    metric_id: WhyMetricId
    metric_label: str
    classification: Literal["fact", "prediction"]
    as_of_date: date
    current_period: str
    comparison_period: str
    current_value: float
    previous_value: float
    unit: ValueUnit
    change_amount: float
    change_percent: float | None
    change_summary: str
    direction: Literal["increased", "decreased", "unchanged"]
    drivers: list[DriverFinding]
    explanation: str
    explanation_mode: str
    methodology: str
    source_refs: list[str]
    drilldown_path: str
    insufficient_data: bool