from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from lib.db import get_db
from models.reconciliation import (
    ReconciliationExceptionPage,
    ReconciliationRecord,
    ReconciliationStatus,
    ReconciliationSummary,
)
from services.reconciliation import (
    EXCEPTION_STATUSES,
    calculate_records,
    default_date_range,
    get_record,
    summarize_records,
)

router = APIRouter(prefix="/reconciliation", tags=["reconciliation"])


def resolved_range(date_from: date | None, date_to: date | None) -> tuple[date, date]:
    default_from, default_to = default_date_range()
    start, end = date_from or default_from, date_to or default_to
    if start > end:
        raise HTTPException(status_code=422, detail="date_from must be on or before date_to")
    return start, end


@router.get("/summary", response_model=ReconciliationSummary)
async def reconciliation_summary(
    date_from: date | None = None,
    date_to: date | None = None,
    session: AsyncSession = Depends(get_db),
) -> ReconciliationSummary:
    start, end = resolved_range(date_from, date_to)
    records = await calculate_records(session, start, end)
    return summarize_records(records, start, end)


@router.get("/exceptions", response_model=ReconciliationExceptionPage)
async def reconciliation_exceptions(
    date_from: date | None = None,
    date_to: date | None = None,
    status: ReconciliationStatus | None = None,
    payment_method: str | None = None,
    search: str | None = Query(None, max_length=80),
    limit: int = Query(25, ge=1, le=100),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_db),
) -> ReconciliationExceptionPage:
    start, end = resolved_range(date_from, date_to)
    records = await calculate_records(session, start, end)
    records = [record for record in records if record.status in EXCEPTION_STATUSES]
    if status:
        records = [record for record in records if record.status == status]
    if payment_method:
        records = [record for record in records if record.payment_method == payment_method]
    if search:
        needle = search.lower()
        records = [record for record in records if needle in " ".join(filter(None, [
            record.id, record.payment_id, record.settlement_id, record.order_id,
        ])).lower()]
    total = len(records)
    return ReconciliationExceptionPage(
        items=records[offset:offset + limit], total=total, limit=limit, offset=offset,
        date_from=start, date_to=end,
    )


@router.get("/{reconciliation_id}", response_model=ReconciliationRecord)
async def reconciliation_detail(
    reconciliation_id: str,
    session: AsyncSession = Depends(get_db),
) -> ReconciliationRecord:
    record = await get_record(session, reconciliation_id)
    if not record:
        raise HTTPException(status_code=404, detail="Reconciliation record not found")
    return record