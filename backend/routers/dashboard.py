from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from lib.db import get_db
from models.financial import CfoResponse, DashboardResponse, ForecastResponse, ReconciliationResponse
from services.ai import StaticInsightGenerator
from services.financial import (
    load_transactions,
    make_forecast_response,
    make_reconciliation_response,
    make_summary,
)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


async def build_dashboard(session: AsyncSession) -> DashboardResponse:
    transactions = await load_transactions(session)
    reconciliation = make_reconciliation_response(transactions)
    forecast = make_forecast_response(transactions)
    cfo = StaticInsightGenerator().generate(reconciliation.summary, forecast)
    return DashboardResponse(
        summary=make_summary(transactions, forecast, reconciliation.summary),
        reconciliation=reconciliation.summary,
        forecast=forecast,
        insights=cfo.insights,
    )


@router.get("", response_model=DashboardResponse)
async def get_dashboard(session: AsyncSession = Depends(get_db)) -> DashboardResponse:
    return await build_dashboard(session)


@router.get("/reconciliation", response_model=ReconciliationResponse)
async def get_reconciliation(session: AsyncSession = Depends(get_db)) -> ReconciliationResponse:
    return make_reconciliation_response(await load_transactions(session))


@router.get("/forecast", response_model=ForecastResponse)
async def get_forecast(session: AsyncSession = Depends(get_db)) -> ForecastResponse:
    return make_forecast_response(await load_transactions(session))


@router.get("/cfo", response_model=CfoResponse)
async def get_cfo(session: AsyncSession = Depends(get_db)) -> CfoResponse:
    transactions = await load_transactions(session)
    reconciliation = make_reconciliation_response(transactions)
    forecast = make_forecast_response(transactions)
    return StaticInsightGenerator().generate(reconciliation.summary, forecast)