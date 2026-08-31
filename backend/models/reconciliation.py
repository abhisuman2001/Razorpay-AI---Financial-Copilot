from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field


ReconciliationStatus = Literal["MATCHED", "PARTIALLY_MATCHED", "MISMATCHED", "PENDING", "UNRESOLVED"]


class ComponentComparison(BaseModel):
    component: str
    expected_amount: int
    actual_amount: int | None
    difference_amount: int | None
    matches: bool


class ReconciliationRecord(BaseModel):
    id: str
    payment_id: str | None
    settlement_id: str | None
    order_id: str | None
    customer_id: str | None
    payment_method: str | None
    currency: str
    payment_created_at: datetime | None
    settlement_date: date | None
    gross_payment: int
    refund_amount: int
    fees: int
    taxes: int
    expected_settlement: int
    actual_settlement: int | None
    difference_amount: int | None
    difference_percentage: float | None
    status: ReconciliationStatus
    possible_reason: str
    component_comparisons: list[ComponentComparison]


class ReconciliationSummary(BaseModel):
    date_from: date
    date_to: date
    total_transactions: int
    matched_transactions: int
    partially_matched_transactions: int
    mismatched_transactions: int
    pending_transactions: int
    unresolved_transactions: int
    total_expected_amount: int
    total_actual_amount: int
    total_discrepancy: int
    reconciliation_rate: float = Field(ge=0, le=100)
    amount_unit: str = "paise"


class ReconciliationExceptionPage(BaseModel):
    items: list[ReconciliationRecord]
    total: int
    limit: int
    offset: int
    date_from: date
    date_to: date