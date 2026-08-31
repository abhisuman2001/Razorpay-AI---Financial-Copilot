from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


SourceType = Literal["bank", "payment_gateway", "accounting", "marketplace"]
ImportStatus = Literal["ANALYZED", "IMPORTED", "RECONCILED", "FAILED"]
MatchStatus = Literal["MATCHED", "UNMATCHED", "AMOUNT_MISMATCH", "DATE_MISMATCH", "DUPLICATE"]


class ColumnMapping(BaseModel):
    transaction_id: str | None = None
    reference: str | None = None
    date: str | None = None
    amount: str | None = None
    debit: str | None = None
    credit: str | None = None
    direction: str | None = None
    description: str | None = None
    currency: str | None = None
    status: str | None = None
    counterparty: str | None = None

class MappingUpdate(BaseModel):
    mapping: ColumnMapping


class MappingSuggestion(BaseModel):
    internal_field: str
    detected_column: str | None
    confidence: float = Field(ge=0, le=1)
    alternatives: list[str]


class NormalizedPreview(BaseModel):
    external_id: str | None
    reference: str | None
    transaction_date: date | None
    amount: int | None
    direction: str | None
    currency: str | None
    description: str | None
    counterparty: str | None
    status: str | None


class ImportPreviewRow(BaseModel):
    source_row_number: int
    original_data: dict[str, str]
    normalized: NormalizedPreview | None
    errors: list[str]


class ImportReconciliationSummary(BaseModel):
    total_transactions: int
    matched: int
    unmatched: int
    amount_mismatches: int
    date_mismatches: int
    duplicates: int
    average_confidence: float = Field(ge=0, le=100)


class ImportBatchRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    source_type: SourceType
    filename: str
    file_size: int
    file_sha256: str
    status: ImportStatus
    row_count: int
    normalized_count: int
    duplicate_count: int
    uploaded_at: datetime
    imported_at: datetime | None
    reconciled_at: datetime | None


class ImportWorkspaceResponse(BaseModel):
    batch: ImportBatchRead
    headers: list[str]
    mapping: ColumnMapping
    suggestions: list[MappingSuggestion]
    preview: list[ImportPreviewRow]
    reconciliation: ImportReconciliationSummary | None


class ImportBatchList(BaseModel):
    batches: list[ImportBatchRead]
    total: int


class ImportResult(BaseModel):
    batch: ImportBatchRead
    reconciliation: ImportReconciliationSummary
    message: str


class ImportedTransactionView(BaseModel):
    id: str
    batch_id: str
    source_type: SourceType
    source_row_number: int
    external_id: str | None
    reference: str | None
    transaction_date: date
    amount: int
    direction: str
    currency: str
    description: str | None
    counterparty: str | None
    status: str | None
    duplicate_of_id: str | None
    match_status: MatchStatus
    match_rule: str
    confidence: float
    matched_transaction_id: str | None
    amount_difference: int | None
    date_difference_days: int | None
    reason: str
    original_data: dict[str, str]


class ImportedTransactionPage(BaseModel):
    items: list[ImportedTransactionView]
    total: int
    limit: int
    offset: int