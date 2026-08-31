import csv

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from lib.db import get_db
from models.imports import (
    ImportBatchList,
    ImportedTransactionPage,
    ImportResult,
    ImportWorkspaceResponse,
    MappingUpdate,
    MatchStatus,
    SourceType,
)
from services.imports import (
    ImportValidationError,
    analyze_csv,
    get_workspace,
    import_batch,
    list_batches,
    reconcile_batch,
    transaction_page,
    update_mapping,
)

router = APIRouter(prefix="/imports", tags=["financial data import"])


def import_error(exc: Exception) -> HTTPException:
    if isinstance(exc, LookupError):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, ImportValidationError):
        return HTTPException(status_code=422, detail=exc.errors[:25])
    return HTTPException(status_code=400, detail=str(exc))


@router.post("/analyze", response_model=ImportWorkspaceResponse)
async def analyze_import(
    source_type: SourceType = Form(...),
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_db),
) -> ImportWorkspaceResponse:
    try:
        content = await file.read(25 * 1024 * 1024 + 1)
        return await analyze_csv(session, source_type, file.filename or "upload.csv", content)
    except (ImportValidationError, UnicodeError, csv.Error) as exc:
        raise import_error(exc) from exc


@router.get("/batches", response_model=ImportBatchList)
async def import_batches(session: AsyncSession = Depends(get_db)) -> ImportBatchList:
    return await list_batches(session)


@router.get("/{batch_id}", response_model=ImportWorkspaceResponse)
async def import_workspace(
    batch_id: str, session: AsyncSession = Depends(get_db)
) -> ImportWorkspaceResponse:
    try:
        return await get_workspace(session, batch_id)
    except LookupError as exc:
        raise import_error(exc) from exc


@router.put("/{batch_id}/mapping", response_model=ImportWorkspaceResponse)
async def set_mapping(
    batch_id: str, request: MappingUpdate, session: AsyncSession = Depends(get_db)
) -> ImportWorkspaceResponse:
    try:
        return await update_mapping(session, batch_id, request.mapping)
    except (LookupError, ImportValidationError) as exc:
        raise import_error(exc) from exc


@router.post("/{batch_id}/import", response_model=ImportResult)
async def confirm_import(
    batch_id: str, session: AsyncSession = Depends(get_db)
) -> ImportResult:
    try:
        return await import_batch(session, batch_id)
    except (LookupError, ImportValidationError) as exc:
        raise import_error(exc) from exc


@router.post("/{batch_id}/reconcile", response_model=ImportResult)
async def rerun_reconciliation(
    batch_id: str, session: AsyncSession = Depends(get_db)
) -> ImportResult:
    try:
        return await reconcile_batch(session, batch_id)
    except (LookupError, ImportValidationError) as exc:
        raise import_error(exc) from exc


@router.get("/{batch_id}/transactions", response_model=ImportedTransactionPage)
async def imported_transactions(
    batch_id: str,
    match_status: MatchStatus | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_db),
) -> ImportedTransactionPage:
    try:
        return await transaction_page(session, batch_id, match_status, limit, offset)
    except LookupError as exc:
        raise import_error(exc) from exc