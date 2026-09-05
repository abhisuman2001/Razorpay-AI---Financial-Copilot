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


# ── Cash Balance Analysis ─────────────────────────────────────────────────────

class CashBalanceWaterfallRow(BaseModel):
    """One row of the opening → current balance waterfall."""

    id: str
    label: str
    amount: int  # paise; positive = inflow, negative = outflow
    is_subtotal: bool = False  # True for the final "Current cash balance" line
    source_table: str  # e.g. "OPENING_CASH_BALANCE_PAISE", "settlements", "expenses"
    record_count: int  # number of contributing DB rows (0 for constants)
    description: str


class CashBalanceDailyRow(BaseModel):
    """One row of the daily cash-movement breakdown."""

    date: date
    inflows: int        # paise
    outflows: int       # paise
    net_movement: int   # paise  (inflows - outflows)
    ending_balance: int # paise cumulative


class CashBalanceAnalysis(BaseModel):
    """
    Full auditable breakdown of how the current cash balance was derived.

    All amounts are in paise. No LLM is involved; every number is calculated
    deterministically from the financial database.
    """

    as_of_date: date
    period_start: date   # first date of the historical series
    period_end: date     # last date included (= as_of_date)

    # Opening balance
    opening_balance: int
    opening_balance_date: date
    opening_balance_source: str
    opening_balance_configurable: bool

    # Aggregated inflows
    total_settled_cash: int       # sum of settlements.net_settlement (settled)
    total_other_income: int       # currently 0; reserved for future income types
    settlement_record_count: int
    settlement_fees_total: int    # informational: total fees already deducted in net_settlement
    settlement_refunds_total: int # informational: total refunds already deducted in net_settlement

    # Aggregated outflows
    total_expenses: int
    expense_record_count: int

    # Waterfall rows (ordered from opening to current balance)
    waterfall: list[CashBalanceWaterfallRow]

    # Daily breakdown
    daily_breakdown: list[CashBalanceDailyRow]

    # Reconciliation check
    calculated_balance: int   # opening + inflows - outflows (must equal current_balance)
    current_balance: int      # as reported on the Cash Flow page
    rounding_difference: int  # current_balance - calculated_balance (should be 0)

    # Human-readable conclusion
    why_this_matters: str     # deterministic narrative; LLM cannot modify values
    calculation_method: str
    validation_status: str    # human-readable validation message