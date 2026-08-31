from datetime import date
from typing import Literal

from pydantic import BaseModel, Field


ForecastHorizon = Literal[7, 30, 90]
RiskSeverity = Literal["high", "medium", "low"]


class HistoricalCashFlowPoint(BaseModel):
    date: date
    daily_income: int
    daily_expenses: int
    daily_net_cashflow: int
    cumulative_cash_balance: int


class PredictedCashFlowPoint(BaseModel):
    date: date
    predicted_income: int
    predicted_expenses: int
    predicted_net_cashflow: int
    predicted_balance: int
    balance_lower: int
    balance_upper: int


class ForecastRisk(BaseModel):
    id: str
    severity: RiskSeverity
    category: str
    title: str
    description: str
    metric_label: str
    metric_value: str
    source: str


class CashFlowForecastResponse(BaseModel):
    horizon_days: ForecastHorizon
    as_of_date: date
    history_start: date
    history_end: date
    opening_cash_balance: int
    current_cash_balance: int
    expected_incoming: int
    expected_outgoing: int
    forecasted_balance: int
    confidence_level: float = Field(default=0.80, ge=0, le=1)
    confidence_label: str
    model_name: str
    methodology: str
    amount_unit: str = "paise"
    historical: list[HistoricalCashFlowPoint]
    forecast: list[PredictedCashFlowPoint]
    risks: list[ForecastRisk]