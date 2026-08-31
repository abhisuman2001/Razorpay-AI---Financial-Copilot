from datetime import date
from typing import Literal

from pydantic import BaseModel

from models.cashflow import HistoricalCashFlowPoint, PredictedCashFlowPoint
from models.cfo import DailyInsight


class MetricEvidence(BaseModel):
    id: str
    type: str
    label: str
    date: date
    amount: int
    status: str


class ExecutiveMetric(BaseModel):
    id: Literal["revenue", "current_balance", "cash_forecast", "reconciliation_exceptions"]
    label: str
    value: int
    value_kind: Literal["currency", "count"]
    change_percent: float | None
    trend: Literal["up", "down", "neutral"]
    period_label: str
    detail: str
    explanation: str
    calculation: str
    source_metric: str
    source_tool: str
    drilldown_path: str
    evidence: list[MetricEvidence]


class ExecutiveReconciliation(BaseModel):
    transactions_analyzed: int
    matched: int
    partially_matched: int
    mismatched: int
    pending: int
    unresolved: int
    total_discrepancy: int
    reconciliation_rate: float


class ExecutiveDashboardResponse(BaseModel):
    as_of_date: date
    metrics: list[ExecutiveMetric]
    cashflow_actual: list[HistoricalCashFlowPoint]
    cashflow_forecast: list[PredictedCashFlowPoint]
    reconciliation: ExecutiveReconciliation
    insights: list[DailyInsight]
    insight_mode: str
    amount_unit: str = "paise"