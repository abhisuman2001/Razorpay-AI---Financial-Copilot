from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from lib.db import Base


class DatasetRun(Base):
    __tablename__ = "dataset_runs"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    seed: Mapped[int] = mapped_column(Integer)
    payment_count: Mapped[int] = mapped_column(Integer)
    generated_at: Mapped[datetime] = mapped_column(DateTime)
    period_start: Mapped[date] = mapped_column(Date)
    period_end: Mapped[date] = mapped_column(Date)


class DemoScenarioState(Base):
    __tablename__ = "demo_scenario_state"

    id: Mapped[str] = mapped_column(String(20), primary_key=True, default="global")
    scenario_id: Mapped[str] = mapped_column(String(40))
    activated_at: Mapped[datetime] = mapped_column(DateTime)
    dataset_run_id: Mapped[str] = mapped_column(String(40))
    payment_count: Mapped[int] = mapped_column(Integer)
    seed: Mapped[int] = mapped_column(Integer)


class Customer(Base):
    __tablename__ = "customers"

    customer_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(160), index=True)
    phone: Mapped[str] = mapped_column(String(20))
    city: Mapped[str] = mapped_column(String(60))
    state: Mapped[str] = mapped_column(String(60))
    segment: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(DateTime)


class Order(Base):
    __tablename__ = "orders"

    order_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.customer_id"), index=True)
    amount: Mapped[int] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(3), default="INR")
    status: Mapped[str] = mapped_column(String(24), index=True)
    receipt: Mapped[str] = mapped_column(String(48))
    created_at: Mapped[datetime] = mapped_column(DateTime, index=True)


class Payment(Base):
    __tablename__ = "payments"
    __table_args__ = (
        Index("ix_payments_order_created", "order_id", "created_at"),
        Index("ix_payments_customer_created", "customer_id", "created_at"),
    )

    payment_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    order_id: Mapped[str] = mapped_column(ForeignKey("orders.order_id"), index=True)
    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.customer_id"), index=True)
    amount: Mapped[int] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(3), default="INR")
    status: Mapped[str] = mapped_column(String(20), index=True)
    payment_method: Mapped[str] = mapped_column(String(20), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    captured_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class Refund(Base):
    __tablename__ = "refunds"

    refund_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    payment_id: Mapped[str] = mapped_column(ForeignKey("payments.payment_id"), index=True)
    amount: Mapped[int] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(3), default="INR")
    status: Mapped[str] = mapped_column(String(20), index=True)
    reason: Mapped[str] = mapped_column(String(60))
    created_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class Settlement(Base):
    __tablename__ = "settlements"

    settlement_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    payment_id: Mapped[str | None] = mapped_column(ForeignKey("payments.payment_id"), nullable=True, index=True)
    external_reference: Mapped[str] = mapped_column(String(48))
    gross_amount: Mapped[int] = mapped_column(Integer)
    refund_amount: Mapped[int] = mapped_column(Integer)
    fees: Mapped[int] = mapped_column(Integer)
    taxes: Mapped[int] = mapped_column(Integer)
    net_settlement: Mapped[int] = mapped_column(Integer)
    settlement_date: Mapped[date] = mapped_column(Date, index=True)
    status: Mapped[str] = mapped_column(String(20), index=True)


class Expense(Base):
    __tablename__ = "expenses"

    expense_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    category: Mapped[str] = mapped_column(String(40), index=True)
    vendor: Mapped[str] = mapped_column(String(100))
    amount: Mapped[int] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(3), default="INR")
    date: Mapped[date] = mapped_column(Date, index=True)
    recurring: Mapped[bool] = mapped_column(Boolean)
    payment_mode: Mapped[str] = mapped_column(String(20))


class Chargeback(Base):
    __tablename__ = "chargebacks"

    chargeback_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    payment_id: Mapped[str] = mapped_column(ForeignKey("payments.payment_id"), index=True)
    amount: Mapped[int] = mapped_column(Integer)
    reason_code: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(24), index=True)
    opened_at: Mapped[datetime] = mapped_column(DateTime)
    due_at: Mapped[datetime] = mapped_column(DateTime)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class FailedPayment(Base):
    __tablename__ = "failed_payments"

    failed_payment_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    payment_id: Mapped[str] = mapped_column(ForeignKey("payments.payment_id"), unique=True, index=True)
    error_code: Mapped[str] = mapped_column(String(48), index=True)
    error_description: Mapped[str] = mapped_column(String(160))
    failure_stage: Mapped[str] = mapped_column(String(30))
    retryable: Mapped[bool] = mapped_column(Boolean)
    failed_at: Mapped[datetime] = mapped_column(DateTime, index=True)


class FinancialAnomaly(Base):
    __tablename__ = "financial_anomalies"

    anomaly_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    dataset_run_id: Mapped[str] = mapped_column(ForeignKey("dataset_runs.id"), index=True)
    anomaly_type: Mapped[str] = mapped_column(String(48), index=True)
    entity_type: Mapped[str] = mapped_column(String(24))
    entity_id: Mapped[str] = mapped_column(String(40), index=True)
    related_entity_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    expected_amount: Mapped[int | None] = mapped_column(Integer, nullable=True)
    actual_amount: Mapped[int | None] = mapped_column(Integer, nullable=True)
    description: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime)
