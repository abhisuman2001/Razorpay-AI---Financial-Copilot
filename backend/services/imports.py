from __future__ import annotations

import csv
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import hashlib
import io
import json
import re
from typing import Any
from uuid import uuid4

import pandas as pd
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.import_tables import ImportBatch, ImportedTransaction, ImportRawRow, ImportReconciliation
from models.imports import (
    ColumnMapping,
    ImportBatchList,
    ImportBatchRead,
    ImportedTransactionPage,
    ImportedTransactionView,
    ImportPreviewRow,
    ImportReconciliationSummary,
    ImportResult,
    ImportWorkspaceResponse,
    MappingSuggestion,
    NormalizedPreview,
    SourceType,
)


MAX_FILE_BYTES = 25 * 1024 * 1024
MAX_ROWS = 100_000
PREVIEW_ROWS = 8
FIELDS = [
    "transaction_id", "reference", "date", "amount", "debit", "credit",
    "direction", "description", "currency", "status", "counterparty",
]
SYNONYMS = {
    "transaction_id": ["transaction_id", "transactionid", "txn_id", "txnid", "payment_id", "id", "utr", "bank_reference"],
    "reference": ["reference", "ref", "order_id", "orderid", "receipt", "invoice", "invoice_number", "merchant_reference"],
    "date": ["transaction_date", "date", "created_at", "payment_date", "settlement_date", "posted_at", "posting_date", "timestamp"],
    "amount": ["amount", "transaction_amount", "gross_amount", "net_amount", "value", "total", "paid_amount"],
    "debit": ["debit", "debit_amount", "withdrawal", "withdrawal_amount"],
    "credit": ["credit", "credit_amount", "deposit", "deposit_amount"],
    "direction": ["direction", "type", "transaction_type", "credit_debit", "dr_cr", "flow"],
    "description": ["description", "narration", "notes", "memo", "details", "particulars"],
    "currency": ["currency", "currency_code", "ccy"],
    "status": ["status", "payment_status", "transaction_status", "state"],
    "counterparty": ["counterparty", "customer", "customer_name", "vendor", "payee", "payer", "merchant"],
}


class ImportValidationError(ValueError):
    def __init__(self, errors: list[str]):
        super().__init__("; ".join(errors[:10]))
        self.errors = errors


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _header_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_")


def detect_mapping(headers: list[str]) -> tuple[ColumnMapping, list[MappingSuggestion]]:
    normalized = {header: _header_key(header) for header in headers}
    used: set[str] = set()
    detected: dict[str, str | None] = {}
    suggestions: list[MappingSuggestion] = []
    for field in FIELDS:
        ranked: list[tuple[float, str]] = []
        for header, key in normalized.items():
            if header in used:
                continue
            best = 0.0
            for index, synonym in enumerate(SYNONYMS[field]):
                if key == synonym:
                    best = max(best, 1.0 - index * 0.015)
                elif synonym in key or key in synonym:
                    best = max(best, 0.72 - index * 0.01)
            if best:
                ranked.append((best, header))
        ranked.sort(reverse=True)
        choice = ranked[0][1] if ranked and ranked[0][0] >= 0.65 else None
        if choice:
            used.add(choice)
        detected[field] = choice
        suggestions.append(MappingSuggestion(
            internal_field=field, detected_column=choice,
            confidence=round(ranked[0][0], 2) if choice else 0,
            alternatives=[item[1] for item in ranked[1:4]],
        ))
    if detected.get("amount"):
        detected["debit"] = None
        detected["credit"] = None
    return ColumnMapping(**detected), suggestions


def _clean_text(row: dict[str, str], column: str | None) -> str | None:
    if not column:
        return None
    value = str(row.get(column, "")).strip()
    return value or None


def _parse_date(value: str | None) -> date:
    if not value:
        raise ValueError("date is empty")
    clean = value.strip()
    formats = [
        "%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d", "%m/%d/%Y",
        "%Y-%m-%d %H:%M:%S", "%d/%m/%Y %H:%M:%S", "%Y-%m-%dT%H:%M:%S",
    ]
    for pattern in formats:
        try:
            return datetime.strptime(clean[:19], pattern).date()
        except ValueError:
            continue
    parsed = pd.to_datetime(clean, dayfirst=True, errors="coerce")
    if pd.isna(parsed):
        raise ValueError(f"unsupported date: {value}")
    return parsed.date()


def _parse_money(value: str | None) -> tuple[int, str | None]:
    if not value or value.strip().lower() in {"-", "na", "n/a", "null"}:
        raise ValueError("amount is empty")
    clean = value.strip()
    hinted_direction = None
    if clean.startswith("(") and clean.endswith(")"):
        clean = f"-{clean[1:-1]}"
    if re.search(r"\bdr\b", clean, re.IGNORECASE):
        hinted_direction = "debit"
    elif re.search(r"\bcr\b", clean, re.IGNORECASE):
        hinted_direction = "credit"
    clean = re.sub(r"(?i)inr|rs\.?|₹|,|\s|\bcr\b|\bdr\b", "", clean)
    try:
        amount = Decimal(clean)
    except InvalidOperation as exc:
        raise ValueError(f"invalid amount: {value}") from exc
    if amount < 0:
        hinted_direction = "debit"
    paise = int((abs(amount) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    return paise, hinted_direction


def _normalize_direction(value: str | None, hint: str | None) -> str:
    if value:
        key = _header_key(value)
        if key in {"debit", "dr", "withdrawal", "outflow", "expense", "paid"}:
            return "debit"
        if key in {"credit", "cr", "deposit", "inflow", "income", "received"}:
            return "credit"
    return hint or "credit"


def normalize_row(row: dict[str, str], mapping: ColumnMapping) -> tuple[dict[str, Any] | None, list[str]]:
    errors: list[str] = []
    transaction_date = None
    amount = None
    direction_hint = None
    try:
        transaction_date = _parse_date(_clean_text(row, mapping.date))
    except ValueError as exc:
        errors.append(str(exc))

    try:
        if mapping.amount:
            amount, direction_hint = _parse_money(_clean_text(row, mapping.amount))
        else:
            credit_text = _clean_text(row, mapping.credit)
            debit_text = _clean_text(row, mapping.debit)
            if credit_text and credit_text.strip() not in {"0", "0.00", "-"}:
                amount, _ = _parse_money(credit_text)
                direction_hint = "credit"
            elif debit_text and debit_text.strip() not in {"0", "0.00", "-"}:
                amount, _ = _parse_money(debit_text)
                direction_hint = "debit"
            else:
                raise ValueError("debit and credit are empty")
    except ValueError as exc:
        errors.append(str(exc))

    if errors:
        return None, errors
    normalized = {
        "external_id": _clean_text(row, mapping.transaction_id),
        "reference": _clean_text(row, mapping.reference),
        "transaction_date": transaction_date,
        "amount": amount,
        "direction": _normalize_direction(_clean_text(row, mapping.direction), direction_hint),
        "currency": (_clean_text(row, mapping.currency) or "INR").upper()[:3],
        "description": _clean_text(row, mapping.description),
        "counterparty": _clean_text(row, mapping.counterparty),
        "status": _clean_text(row, mapping.status),
    }
    return normalized, []


def validate_mapping(mapping: ColumnMapping, headers: list[str]) -> None:
    errors = []
    if not mapping.date:
        errors.append("Map a transaction date column")
    if not mapping.amount and not mapping.debit and not mapping.credit:
        errors.append("Map an amount column or debit/credit columns")
    selected = [value for value in mapping.model_dump().values() if value]
    missing = [value for value in selected if value not in headers]
    if missing:
        errors.append(f"Mapped columns are not in this CSV: {', '.join(missing)}")
    if errors:
        raise ImportValidationError(errors)


def _fingerprint(source_type: str, normalized: dict[str, Any]) -> str:
    if normalized["external_id"]:
        identity = f"{source_type}|id|{normalized['external_id'].lower()}"
    else:
        identity = "|".join([
            source_type, normalized["transaction_date"].isoformat(), str(normalized["amount"]),
            normalized["direction"], (normalized["reference"] or "").lower(),
            (normalized["description"] or "").lower(),
        ])
    return hashlib.sha256(identity.encode()).hexdigest()


async def analyze_csv(
    session: AsyncSession, source_type: SourceType, filename: str, content: bytes
) -> ImportWorkspaceResponse:
    if not content:
        raise ImportValidationError(["CSV file is empty"])
    if len(content) > MAX_FILE_BYTES:
        raise ImportValidationError(["CSV file exceeds the 25 MB limit"])
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = content.decode("latin-1")
    reader = csv.DictReader(io.StringIO(text))
    headers = [header.strip() for header in (reader.fieldnames or []) if header and header.strip()]
    if not headers:
        raise ImportValidationError(["CSV header row is missing"])
    rows: list[dict[str, str]] = []
    for index, raw in enumerate(reader, start=2):
        if len(rows) >= MAX_ROWS:
            raise ImportValidationError(["CSV exceeds the 100,000 row limit"])
        row = {str(key).strip(): "" if value is None else str(value).strip() for key, value in raw.items() if key}
        if any(row.values()):
            rows.append(row)
    if not rows:
        raise ImportValidationError(["CSV contains no transaction rows"])

    mapping, suggestions = detect_mapping(headers)
    batch_id = f"imp_{uuid4().hex[:16]}"
    uploaded_at = _now()
    batch = ImportBatch(
        id=batch_id, source_type=source_type, filename=filename[:255], file_size=len(content),
        file_sha256=hashlib.sha256(content).hexdigest(), status="ANALYZED", row_count=len(rows),
        normalized_count=0, duplicate_count=0, headers_json=json.dumps(headers),
        mapping_json=mapping.model_dump_json(), uploaded_at=uploaded_at.replace(tzinfo=None),
    )
    session.add(batch)
    raw_mappings = []
    for row_number, row in enumerate(rows, start=2):
        raw_json = json.dumps(row, ensure_ascii=False, sort_keys=True)
        raw_mappings.append({
            "id": f"raw_{batch_id}_{row_number}", "batch_id": batch_id,
            "source_row_number": row_number, "raw_data_json": raw_json,
            "raw_hash": hashlib.sha256(raw_json.encode()).hexdigest(),
        })
    await session.flush()
    await session.run_sync(lambda sync_session: sync_session.bulk_insert_mappings(ImportRawRow, raw_mappings))
    await session.commit()
    return await get_workspace(session, batch_id, suggestions=suggestions)


async def get_batch(session: AsyncSession, batch_id: str) -> ImportBatch:
    batch = await session.get(ImportBatch, batch_id)
    if not batch:
        raise LookupError("Import batch not found")
    return batch


async def update_mapping(
    session: AsyncSession, batch_id: str, mapping: ColumnMapping
) -> ImportWorkspaceResponse:
    batch = await get_batch(session, batch_id)
    if batch.status != "ANALYZED":
        raise ImportValidationError(["Mapping cannot change after import"])
    headers = json.loads(batch.headers_json)
    validate_mapping(mapping, headers)
    batch.mapping_json = mapping.model_dump_json()
    await session.commit()
    return await get_workspace(session, batch_id)


async def preview_rows(
    session: AsyncSession, batch_id: str, mapping: ColumnMapping, limit: int = PREVIEW_ROWS
) -> list[ImportPreviewRow]:
    rows = list((await session.scalars(
        select(ImportRawRow).where(ImportRawRow.batch_id == batch_id)
        .order_by(ImportRawRow.source_row_number).limit(limit)
    )).all())
    preview = []
    for raw in rows:
        original = json.loads(raw.raw_data_json)
        normalized, errors = normalize_row(original, mapping)
        preview.append(ImportPreviewRow(
            source_row_number=raw.source_row_number, original_data=original,
            normalized=NormalizedPreview(**normalized) if normalized else None, errors=errors,
        ))
    return preview


async def get_reconciliation_summary(
    session: AsyncSession, batch_id: str
) -> ImportReconciliationSummary | None:
    batch = await get_batch(session, batch_id)
    if batch.status not in {"IMPORTED", "RECONCILED"}:
        return None
    rows = (await session.execute(
        select(ImportReconciliation.match_status, func.count(ImportReconciliation.id), func.avg(ImportReconciliation.confidence))
        .join(ImportedTransaction, ImportedTransaction.id == ImportReconciliation.transaction_id)
        .where(ImportedTransaction.batch_id == batch_id)
        .group_by(ImportReconciliation.match_status)
    )).all()
    counts = {status: int(count) for status, count, _ in rows}
    average = await session.scalar(
        select(func.avg(ImportReconciliation.confidence)).join(
            ImportedTransaction, ImportedTransaction.id == ImportReconciliation.transaction_id
        ).where(ImportedTransaction.batch_id == batch_id)
    ) or 0
    return ImportReconciliationSummary(
        total_transactions=batch.normalized_count,
        matched=counts.get("MATCHED", 0), unmatched=counts.get("UNMATCHED", 0),
        amount_mismatches=counts.get("AMOUNT_MISMATCH", 0),
        date_mismatches=counts.get("DATE_MISMATCH", 0), duplicates=counts.get("DUPLICATE", 0),
        average_confidence=round(float(average), 1),
    )


async def get_workspace(
    session: AsyncSession, batch_id: str, suggestions: list[MappingSuggestion] | None = None
) -> ImportWorkspaceResponse:
    batch = await get_batch(session, batch_id)
    headers = json.loads(batch.headers_json)
    mapping = ColumnMapping.model_validate_json(batch.mapping_json)
    if suggestions is None:
        _, suggestions = detect_mapping(headers)
    return ImportWorkspaceResponse(
        batch=ImportBatchRead.model_validate(batch), headers=headers, mapping=mapping,
        suggestions=suggestions, preview=await preview_rows(session, batch_id, mapping),
        reconciliation=await get_reconciliation_summary(session, batch_id),
    )


async def list_batches(session: AsyncSession, limit: int = 20) -> ImportBatchList:
    total = await session.scalar(select(func.count()).select_from(ImportBatch)) or 0
    batches = list((await session.scalars(
        select(ImportBatch).order_by(ImportBatch.uploaded_at.desc()).limit(limit)
    )).all())
    return ImportBatchList(batches=[ImportBatchRead.model_validate(item) for item in batches], total=total)


async def import_batch(session: AsyncSession, batch_id: str) -> ImportResult:
    batch = await get_batch(session, batch_id)
    if batch.status in {"IMPORTED", "RECONCILED"}:
        summary = await get_reconciliation_summary(session, batch_id)
        return ImportResult(batch=ImportBatchRead.model_validate(batch), reconciliation=summary, message="Batch was already imported.")
    headers = json.loads(batch.headers_json)
    mapping = ColumnMapping.model_validate_json(batch.mapping_json)
    validate_mapping(mapping, headers)
    raw_rows = list((await session.scalars(
        select(ImportRawRow).where(ImportRawRow.batch_id == batch_id).order_by(ImportRawRow.source_row_number)
    )).all())
    existing = {
        fingerprint: transaction_id for fingerprint, transaction_id in (await session.execute(
            select(ImportedTransaction.fingerprint, ImportedTransaction.id)
        )).all()
    }
    records = []
    errors = []
    imported_at = _now().replace(tzinfo=None)
    for raw in raw_rows:
        original = json.loads(raw.raw_data_json)
        normalized, row_errors = normalize_row(original, mapping)
        if row_errors or not normalized:
            errors.extend([f"Row {raw.source_row_number}: {error}" for error in row_errors])
            continue
        fingerprint = _fingerprint(batch.source_type, normalized)
        transaction_id = f"txn_{batch_id[4:12]}_{raw.source_row_number}"
        duplicate_of = existing.get(fingerprint)
        records.append({
            "id": transaction_id, "batch_id": batch_id, "raw_row_id": raw.id,
            "source_type": batch.source_type, "source_row_number": raw.source_row_number,
            **normalized, "fingerprint": fingerprint, "duplicate_of_id": duplicate_of,
            "imported_at": imported_at,
        })
        if not duplicate_of:
            existing[fingerprint] = transaction_id
    if errors:
        raise ImportValidationError(errors)
    await session.run_sync(lambda sync_session: sync_session.bulk_insert_mappings(ImportedTransaction, records))
    batch.normalized_count = len(records)
    batch.duplicate_count = sum(bool(record["duplicate_of_id"]) for record in records)
    batch.status = "IMPORTED"
    batch.imported_at = imported_at
    await session.commit()
    summary = await reconcile_all(session)
    batch = await get_batch(session, batch_id)
    batch_summary = await get_reconciliation_summary(session, batch_id)
    return ImportResult(
        batch=ImportBatchRead.model_validate(batch), reconciliation=batch_summary,
        message=f"Imported {len(records):,} rows and reconciled {summary.total_transactions:,} workspace transactions.",
    )


def _identity_keys(transaction: ImportedTransaction) -> set[str]:
    return {
        value.strip().lower() for value in [transaction.external_id, transaction.reference]
        if value and value.strip()
    }


def _pair_result(left: ImportedTransaction, right: ImportedTransaction) -> tuple[str, str, float, int, int, str]:
    amount_difference = right.amount - left.amount
    date_difference = (right.transaction_date - left.transaction_date).days
    shared_reference = bool(_identity_keys(left) & _identity_keys(right))
    if shared_reference:
        if amount_difference != 0:
            return "AMOUNT_MISMATCH", "EXACT_REFERENCE_AMOUNT_DIFFERENCE", 78.0, amount_difference, date_difference, "Reference matches, but normalized amounts differ."
        if abs(date_difference) > 2:
            return "DATE_MISMATCH", "EXACT_REFERENCE_DATE_DIFFERENCE", 78.0, amount_difference, date_difference, "Reference and amount match, but dates differ by more than two days."
        confidence = 100.0 if date_difference == 0 else 96.0
        return "MATCHED", "EXACT_REFERENCE", confidence, amount_difference, date_difference, "Reference and amount match within the deterministic date window."
    if amount_difference == 0 and date_difference == 0:
        return "MATCHED", "EXACT_AMOUNT_DATE", 90.0, 0, 0, "Amount, direction, currency, and transaction date match exactly."
    if amount_difference == 0 and abs(date_difference) <= 2:
        return "MATCHED", "AMOUNT_FUZZY_DATE", 82.0, 0, date_difference, "Amount matches and transaction dates are within two days."
    if amount_difference == 0 and abs(date_difference) <= 7:
        return "DATE_MISMATCH", "AMOUNT_OUTSIDE_DATE_WINDOW", 62.0, 0, date_difference, "Amount matches, but the date falls outside the two-day matching window."
    relative_difference = abs(amount_difference) / max(left.amount, 1)
    if date_difference == 0 and relative_difference <= 0.05:
        return "AMOUNT_MISMATCH", "DATE_NEAR_AMOUNT", 58.0, amount_difference, 0, "Date matches, but amounts differ by up to five percent."
    return "UNMATCHED", "NO_DETERMINISTIC_MATCH", 0.0, amount_difference, date_difference, "No eligible transaction matched the deterministic rules."


async def reconcile_all(session: AsyncSession) -> ImportReconciliationSummary:
    transactions = list((await session.scalars(
        select(ImportedTransaction).order_by(ImportedTransaction.transaction_date, ImportedTransaction.id)
    )).all())
    await session.execute(delete(ImportReconciliation))
    nonduplicates = [item for item in transactions if not item.duplicate_of_id]
    by_identity: dict[str, list[ImportedTransaction]] = {}
    by_amount_direction: dict[tuple[int, str, str], list[ImportedTransaction]] = {}
    by_date_direction: dict[tuple[date, str, str], list[ImportedTransaction]] = {}
    for item in nonduplicates:
        for key in _identity_keys(item):
            by_identity.setdefault(key, []).append(item)
        by_amount_direction.setdefault((item.amount, item.direction, item.currency), []).append(item)
        by_date_direction.setdefault((item.transaction_date, item.direction, item.currency), []).append(item)

    used: set[str] = set()
    results: list[dict[str, Any]] = []
    reconciled_at = _now().replace(tzinfo=None)

    def eligible(source: ImportedTransaction, candidate: ImportedTransaction) -> bool:
        return candidate.id != source.id and candidate.id not in used and candidate.source_type != source.source_type and candidate.direction == source.direction and candidate.currency == source.currency

    for transaction in transactions:
        if transaction.duplicate_of_id:
            results.append({
                "id": f"match_{transaction.id}", "transaction_id": transaction.id,
                "matched_transaction_id": transaction.duplicate_of_id, "match_status": "DUPLICATE",
                "match_rule": "SOURCE_FINGERPRINT", "confidence": 100.0,
                "amount_difference": 0, "date_difference_days": 0,
                "reason": "Transaction duplicates an existing normalized source fingerprint.",
                "reconciled_at": reconciled_at,
            })
            continue
        if transaction.id in used:
            continue
        candidates: list[ImportedTransaction] = []
        for key in _identity_keys(transaction):
            candidates.extend(by_identity.get(key, []))
        candidates = [item for item in candidates if eligible(transaction, item)]
        candidates.sort(key=lambda item: (abs((item.transaction_date - transaction.transaction_date).days), abs(item.amount - transaction.amount), item.id))
        candidate = candidates[0] if candidates else None
        if not candidate:
            amount_candidates = [
                item for item in by_amount_direction.get((transaction.amount, transaction.direction, transaction.currency), [])
                if eligible(transaction, item) and abs((item.transaction_date - transaction.transaction_date).days) <= 7
            ]
            amount_candidates.sort(key=lambda item: (abs((item.transaction_date - transaction.transaction_date).days), item.id))
            candidate = amount_candidates[0] if amount_candidates else None
        if not candidate:
            nearby = [
                item for item in by_date_direction.get(
                    (transaction.transaction_date, transaction.direction, transaction.currency), []
                ) if eligible(transaction, item)
                and abs(item.amount - transaction.amount) / max(transaction.amount, 1) <= 0.05
            ]
            nearby.sort(key=lambda item: (abs(item.amount - transaction.amount), item.id))
            candidate = nearby[0] if nearby else None

        if candidate:
            status, rule, confidence, amount_difference, date_difference, reason = _pair_result(transaction, candidate)
            if status != "UNMATCHED":
                used.update({transaction.id, candidate.id})
                for left, right, signed_amount, signed_days in [
                    (transaction, candidate, amount_difference, date_difference),
                    (candidate, transaction, -amount_difference, -date_difference),
                ]:
                    results.append({
                        "id": f"match_{left.id}", "transaction_id": left.id,
                        "matched_transaction_id": right.id, "match_status": status,
                        "match_rule": rule, "confidence": confidence,
                        "amount_difference": signed_amount, "date_difference_days": signed_days,
                        "reason": reason, "reconciled_at": reconciled_at,
                    })
                continue
        results.append({
            "id": f"match_{transaction.id}", "transaction_id": transaction.id,
            "matched_transaction_id": None, "match_status": "UNMATCHED",
            "match_rule": "NO_DETERMINISTIC_MATCH", "confidence": 0.0,
            "amount_difference": None, "date_difference_days": None,
            "reason": "No transaction from another source matched by reference or amount and date.",
            "reconciled_at": reconciled_at,
        })
        used.add(transaction.id)

    await session.run_sync(lambda sync_session: sync_session.bulk_insert_mappings(ImportReconciliation, results))
    imported_batches = list((await session.scalars(
        select(ImportBatch).where(ImportBatch.status.in_(["IMPORTED", "RECONCILED"]))
    )).all())
    for batch in imported_batches:
        batch.status = "RECONCILED"
        batch.reconciled_at = reconciled_at
    await session.commit()

    counts: dict[str, int] = {}
    for result in results:
        counts[result["match_status"]] = counts.get(result["match_status"], 0) + 1
    confidence = sum(float(result["confidence"]) for result in results) / len(results) if results else 0
    return ImportReconciliationSummary(
        total_transactions=len(results), matched=counts.get("MATCHED", 0),
        unmatched=counts.get("UNMATCHED", 0), amount_mismatches=counts.get("AMOUNT_MISMATCH", 0),
        date_mismatches=counts.get("DATE_MISMATCH", 0), duplicates=counts.get("DUPLICATE", 0),
        average_confidence=round(confidence, 1),
    )


async def reconcile_batch(session: AsyncSession, batch_id: str) -> ImportResult:
    batch = await get_batch(session, batch_id)
    if batch.status not in {"IMPORTED", "RECONCILED"}:
        raise ImportValidationError(["Import the batch before reconciliation"])
    await reconcile_all(session)
    batch = await get_batch(session, batch_id)
    summary = await get_reconciliation_summary(session, batch_id)
    return ImportResult(
        batch=ImportBatchRead.model_validate(batch), reconciliation=summary,
        message="Reconciliation rerun with deterministic reference, amount, and date rules.",
    )


async def transaction_page(
    session: AsyncSession, batch_id: str, match_status: str | None, limit: int, offset: int
) -> ImportedTransactionPage:
    await get_batch(session, batch_id)
    conditions = [ImportedTransaction.batch_id == batch_id]
    if match_status:
        conditions.append(ImportReconciliation.match_status == match_status)
    count = await session.scalar(
        select(func.count()).select_from(ImportedTransaction)
        .join(ImportReconciliation, ImportReconciliation.transaction_id == ImportedTransaction.id)
        .where(*conditions)
    ) or 0
    rows = (await session.execute(
        select(ImportedTransaction, ImportReconciliation, ImportRawRow)
        .join(ImportReconciliation, ImportReconciliation.transaction_id == ImportedTransaction.id)
        .join(ImportRawRow, ImportRawRow.id == ImportedTransaction.raw_row_id)
        .where(*conditions).order_by(ImportedTransaction.transaction_date.desc(), ImportedTransaction.id)
        .offset(offset).limit(limit)
    )).all()
    items = [ImportedTransactionView(
        id=transaction.id, batch_id=transaction.batch_id, source_type=transaction.source_type,
        source_row_number=transaction.source_row_number, external_id=transaction.external_id,
        reference=transaction.reference, transaction_date=transaction.transaction_date,
        amount=transaction.amount, direction=transaction.direction, currency=transaction.currency,
        description=transaction.description, counterparty=transaction.counterparty, status=transaction.status,
        duplicate_of_id=transaction.duplicate_of_id, match_status=match.match_status,
        match_rule=match.match_rule, confidence=match.confidence,
        matched_transaction_id=match.matched_transaction_id,
        amount_difference=match.amount_difference, date_difference_days=match.date_difference_days,
        reason=match.reason, original_data=json.loads(raw.raw_data_json),
    ) for transaction, match, raw in rows]
    return ImportedTransactionPage(items=items, total=count, limit=limit, offset=offset)