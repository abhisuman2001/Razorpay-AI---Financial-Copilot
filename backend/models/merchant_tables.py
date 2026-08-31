from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from lib.db import Base


class DatasetRun(Base):
    __tablename__ = "dataset_runs"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    seed: Mapped[int] = mapped_column(Integer, nullable=False)
    payment_count: Mapped[int] = mapped_column(Integer, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)


class Customer(Base):
    __tablename__ = "customers"

    customer_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    phone: Mapped[str] = mapped_column(String(20), nullable=False)
    city: Mapped[str] = mapped_column(String(60), nullable=False)
    state: Mapped[str] = mapped_column(String(60), nullable=False)
    segment: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class Order(Base):
    __tablename__ = "orders"

    order_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.customer_id"), nullable=False, index=True)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="INR")
    status: Mapped[str] = mapped_column(String(24), nullable=False, index=True)
    receipt: Mapped[str] = mapped_column(String(48), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)


class Payment(Base):
    __tablename__ = "payments"
    __table_args__ = (
        Index("ix_payments_order_created", "order_id", "created_at"),
        Index("ix_payments_customer_created", "customer_id", "created_at"),
    )

    payment_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    order_id: Mapped[str] = mapped_column(ForeignKey("orders.order_id"), nullable=False, index=True)
    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.customer_id"), nullable=False, index=True)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="INR")
    status: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    payment_method: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    captured_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class Refund(Base):
    __tablename__ = "refunds"

    refund_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    payment_id: Mapped[str] = mapped_column(ForeignKey("payments.payment_id"), nullable=False, index=True)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="INR")
    status: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    reason: Mapped[str] = mapped_column(String(60), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class Settlement(Base):
    __tablename__ = "settlements"

    settlement_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    payment_id: Mapped[str | None] = mapped_column(ForeignKey("payments.payment_id"), nullable=True, index=True)
    external_reference: Mapped[str] = mapped_column(String(48), nullable=False)
    gross_amount: Mapped[int] = mapped_column(Integer, nullable=False)
    refund_amount: Mapped[int] = mapped_column(Integer, nullable=False)
    fees: Mapped[int] = mapped_column(Integer, nullable=False)
    taxes: Mapped[int] = mapped_column(Integer, nullable=False)
    net_settlement: Mapped[int] = mapped_column(Integer, nullable=False)
    settlement_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, index=True)


class Expense(Base):
    __tablename__ = "expenses"

    expense_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    category: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    vendor: Mapped[str] = mapped_column(String(100), nullable=False)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="INR")
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    recurring: Mapped[bool] = mapped_column(Boolean, nullable=False)
    payment_mode: Mapped[str] = mapped_column(String(20), nullable=False)


class Chargeback(Base):
    __tablename__ = "chargebacks"

    chargeback_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    payment_id: Mapped[str] = mapped_column(ForeignKey("payments.payment_id"), nullable=False, index=True)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    reason_code: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, index=True)
    opened_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    due_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class FailedPayment(Base):
    __tablename__ = "failed_payments"

    failed_payment_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    payment_id: Mapped[str] = mapped_column(ForeignKey("payments.payment_id"), nullable=False, unique=True, index=True)
    error_code: Mapped[str] = mapped_column(String(48), nullable=False, index=True)
    error_description: Mapped[str] = mapped_column(String(160), nullable=False)
    failure_stage: Mapped[str] = mapped_column(String(30), nullable=False)
    retryable: Mapped[bool] = mapped_column(Boolean, nullable=False)
    failed_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)


class FinancialAnomaly(Base):
    __tablename__ = "financial_anomalies"

    anomaly_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    dataset_run_id: Mapped[str] = mapped_column(ForeignKey("dataset_runs.id"), nullable=False, index=True)
    anomaly_type: Mapped[str] = mapped_column(String(48), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(24), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    related_entity_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    expected_amount: Mapped[int | None] = mapped_column(Integer, nullable=True)
    actual_amount: Mapped[int | None] = mapped_column(Integer, nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)