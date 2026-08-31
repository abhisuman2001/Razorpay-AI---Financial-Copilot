from datetime import date, datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field


class OrmModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class CustomerRead(OrmModel):
    customer_id: str
    name: str
    email: str
    phone: str
    city: str
    state: str
    segment: str
    created_at: datetime


class OrderRead(OrmModel):
    order_id: str
    customer_id: str
    amount: int
    currency: str
    status: str
    receipt: str
    created_at: datetime


class PaymentRead(OrmModel):
    payment_id: str
    order_id: str
    customer_id: str
    amount: int
    currency: str
    status: str
    payment_method: str
    created_at: datetime
    captured_at: datetime | None


class RefundRead(OrmModel):
    refund_id: str
    payment_id: str
    amount: int
    currency: str
    status: str
    reason: str
    created_at: datetime
    processed_at: datetime | None


class SettlementRead(OrmModel):
    settlement_id: str
    payment_id: str | None
    external_reference: str
    gross_amount: int
    refund_amount: int
    fees: int
    taxes: int
    net_settlement: int
    settlement_date: date
    status: str


class ExpenseRead(OrmModel):
    expense_id: str
    category: str
    vendor: str
    amount: int
    currency: str
    date: date
    recurring: bool
    payment_mode: str


class ChargebackRead(OrmModel):
    chargeback_id: str
    payment_id: str
    amount: int
    reason_code: str
    status: str
    opened_at: datetime
    due_at: datetime
    resolved_at: datetime | None


class FailedPaymentRead(OrmModel):
    failed_payment_id: str
    payment_id: str
    error_code: str
    error_description: str
    failure_stage: str
    retryable: bool
    failed_at: datetime


class AnomalyRead(OrmModel):
    anomaly_id: str
    dataset_run_id: str
    anomaly_type: str
    entity_type: str
    entity_id: str
    related_entity_id: str | None
    expected_amount: int | None
    actual_amount: int | None
    description: str
    created_at: datetime


ItemT = TypeVar("ItemT")


class DatasetPage(BaseModel, Generic[ItemT]):
    items: list[ItemT]
    total: int
    limit: int
    offset: int


class DatasetCounts(BaseModel):
    customers: int
    orders: int
    payments: int
    refunds: int
    settlements: int
    expenses: int
    chargebacks: int
    failed_payments: int
    anomalies: int


class AnomalyCount(BaseModel):
    anomaly_type: str
    count: int


class DatasetSummary(BaseModel):
    dataset_run_id: str
    seed: int
    generated_at: datetime
    period_start: date
    period_end: date
    amount_unit: str = Field(default="paise")
    counts: DatasetCounts
    anomalies_by_type: list[AnomalyCount]