from typing import Any, TypeVar

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from lib.db import get_db
from models.datasets import (
    AnomalyCount,
    AnomalyRead,
    ChargebackRead,
    CustomerRead,
    DatasetCounts,
    DatasetPage,
    DatasetSummary,
    ExpenseRead,
    FailedPaymentRead,
    OrderRead,
    PaymentRead,
    RefundRead,
    SettlementRead,
)
from models.merchant_tables import (
    Chargeback,
    Customer,
    DatasetRun,
    Expense,
    FailedPayment,
    FinancialAnomaly,
    Order,
    Payment,
    Refund,
    Settlement,
)

router = APIRouter(prefix="/datasets", tags=["synthetic datasets"])
ModelT = TypeVar("ModelT")


async def page_for(
    session: AsyncSession,
    model: type[ModelT],
    order_column: Any,
    limit: int,
    offset: int,
    filters: list[Any] | None = None,
) -> DatasetPage:
    conditions = filters or []
    total = await session.scalar(select(func.count()).select_from(model).where(*conditions)) or 0
    result = await session.execute(
        select(model).where(*conditions).order_by(order_column.desc()).offset(offset).limit(limit)
    )
    return DatasetPage(items=list(result.scalars().all()), total=total, limit=limit, offset=offset)


@router.get("/summary", response_model=DatasetSummary)
async def dataset_summary(session: AsyncSession = Depends(get_db)) -> DatasetSummary:
    run = await session.scalar(select(DatasetRun).order_by(DatasetRun.generated_at.desc()).limit(1))
    if not run:
        raise HTTPException(status_code=404, detail="Synthetic dataset has not been generated")

    models = [Customer, Order, Payment, Refund, Settlement, Expense, Chargeback, FailedPayment, FinancialAnomaly]
    values = [await session.scalar(select(func.count()).select_from(model)) or 0 for model in models]
    anomaly_rows = (
        await session.execute(
            select(FinancialAnomaly.anomaly_type, func.count(FinancialAnomaly.anomaly_id))
            .group_by(FinancialAnomaly.anomaly_type)
            .order_by(FinancialAnomaly.anomaly_type)
        )
    ).all()
    return DatasetSummary(
        dataset_run_id=run.id,
        seed=run.seed,
        generated_at=run.generated_at,
        period_start=run.period_start,
        period_end=run.period_end,
        counts=DatasetCounts(
            customers=values[0], orders=values[1], payments=values[2], refunds=values[3],
            settlements=values[4], expenses=values[5], chargebacks=values[6],
            failed_payments=values[7], anomalies=values[8],
        ),
        anomalies_by_type=[AnomalyCount(anomaly_type=row[0], count=row[1]) for row in anomaly_rows],
    )


@router.get("/customers", response_model=DatasetPage[CustomerRead])
async def customers(
    limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_db),
) -> DatasetPage[CustomerRead]:
    return await page_for(session, Customer, Customer.created_at, limit, offset)


@router.get("/orders", response_model=DatasetPage[OrderRead])
async def orders(
    limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0), status: str | None = None,
    session: AsyncSession = Depends(get_db),
) -> DatasetPage[OrderRead]:
    filters = [Order.status == status] if status else []
    return await page_for(session, Order, Order.created_at, limit, offset, filters)


@router.get("/payments", response_model=DatasetPage[PaymentRead])
async def payments(
    limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0),
    status: str | None = None, payment_method: str | None = None,
    session: AsyncSession = Depends(get_db),
) -> DatasetPage[PaymentRead]:
    filters = []
    if status:
        filters.append(Payment.status == status)
    if payment_method:
        filters.append(Payment.payment_method == payment_method)
    return await page_for(session, Payment, Payment.created_at, limit, offset, filters)


@router.get("/refunds", response_model=DatasetPage[RefundRead])
async def refunds(
    limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0), status: str | None = None,
    session: AsyncSession = Depends(get_db),
) -> DatasetPage[RefundRead]:
    filters = [Refund.status == status] if status else []
    return await page_for(session, Refund, Refund.created_at, limit, offset, filters)


@router.get("/settlements", response_model=DatasetPage[SettlementRead])
async def settlements(
    limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0), status: str | None = None,
    session: AsyncSession = Depends(get_db),
) -> DatasetPage[SettlementRead]:
    filters = [Settlement.status == status] if status else []
    return await page_for(session, Settlement, Settlement.settlement_date, limit, offset, filters)


@router.get("/expenses", response_model=DatasetPage[ExpenseRead])
async def expenses(
    limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0),
    category: str | None = None, recurring: bool | None = None,
    session: AsyncSession = Depends(get_db),
) -> DatasetPage[ExpenseRead]:
    filters = []
    if category:
        filters.append(Expense.category == category)
    if recurring is not None:
        filters.append(Expense.recurring == recurring)
    return await page_for(session, Expense, Expense.date, limit, offset, filters)


@router.get("/chargebacks", response_model=DatasetPage[ChargebackRead])
async def chargebacks(
    limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0), status: str | None = None,
    session: AsyncSession = Depends(get_db),
) -> DatasetPage[ChargebackRead]:
    filters = [Chargeback.status == status] if status else []
    return await page_for(session, Chargeback, Chargeback.opened_at, limit, offset, filters)


@router.get("/failed-payments", response_model=DatasetPage[FailedPaymentRead])
async def failed_payments(
    limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0), error_code: str | None = None,
    session: AsyncSession = Depends(get_db),
) -> DatasetPage[FailedPaymentRead]:
    filters = [FailedPayment.error_code == error_code] if error_code else []
    return await page_for(session, FailedPayment, FailedPayment.failed_at, limit, offset, filters)


@router.get("/anomalies", response_model=DatasetPage[AnomalyRead])
async def anomalies(
    limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0), anomaly_type: str | None = None,
    session: AsyncSession = Depends(get_db),
) -> DatasetPage[AnomalyRead]:
    filters = [FinancialAnomaly.anomaly_type == anomaly_type] if anomaly_type else []
    return await page_for(session, FinancialAnomaly, FinancialAnomaly.created_at, limit, offset, filters)