from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from lib.db import Base


class ImportBatch(Base):
    __tablename__ = "import_batches"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    source_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    file_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, index=True)
    row_count: Mapped[int] = mapped_column(Integer, nullable=False)
    normalized_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duplicate_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    headers_json: Mapped[str] = mapped_column(Text, nullable=False)
    mapping_json: Mapped[str] = mapped_column(Text, nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    imported_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    reconciled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class ImportRawRow(Base):
    __tablename__ = "import_raw_rows"
    __table_args__ = (Index("ix_import_raw_batch_row", "batch_id", "source_row_number", unique=True),)

    id: Mapped[str] = mapped_column(String(48), primary_key=True)
    batch_id: Mapped[str] = mapped_column(ForeignKey("import_batches.id", ondelete="CASCADE"), nullable=False, index=True)
    source_row_number: Mapped[int] = mapped_column(Integer, nullable=False)
    raw_data_json: Mapped[str] = mapped_column(Text, nullable=False)
    raw_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)


class ImportedTransaction(Base):
    __tablename__ = "imported_transactions"
    __table_args__ = (
        Index("ix_imported_txn_date_amount", "transaction_date", "amount"),
        Index("ix_imported_txn_reference", "reference"),
    )

    id: Mapped[str] = mapped_column(String(48), primary_key=True)
    batch_id: Mapped[str] = mapped_column(ForeignKey("import_batches.id", ondelete="CASCADE"), nullable=False, index=True)
    raw_row_id: Mapped[str] = mapped_column(ForeignKey("import_raw_rows.id", ondelete="CASCADE"), nullable=False, unique=True)
    source_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    source_row_number: Mapped[int] = mapped_column(Integer, nullable=False)
    external_id: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    reference: Mapped[str | None] = mapped_column(String(160), nullable=True, index=True)
    transaction_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    direction: Mapped[str] = mapped_column(String(12), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    counterparty: Mapped[str | None] = mapped_column(String(180), nullable=True)
    status: Mapped[str | None] = mapped_column(String(40), nullable=True)
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    duplicate_of_id: Mapped[str | None] = mapped_column(ForeignKey("imported_transactions.id"), nullable=True, index=True)
    imported_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class ImportReconciliation(Base):
    __tablename__ = "import_reconciliations"

    id: Mapped[str] = mapped_column(String(48), primary_key=True)
    transaction_id: Mapped[str] = mapped_column(ForeignKey("imported_transactions.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    matched_transaction_id: Mapped[str | None] = mapped_column(ForeignKey("imported_transactions.id"), nullable=True, index=True)
    match_status: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    match_rule: Mapped[str] = mapped_column(String(60), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    amount_difference: Mapped[int | None] = mapped_column(Integer, nullable=True)
    date_difference_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    reconciled_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)