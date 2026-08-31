from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from lib.db import get_db
from models.cashflow import CashFlowForecastResponse
from services.cashflow import build_cashflow_forecast

router = APIRouter(prefix="/forecast", tags=["cash-flow forecast"])


async def response_for(horizon: int, session: AsyncSession) -> CashFlowForecastResponse:
    try:
        return await build_cashflow_forecast(session, horizon)  # type: ignore[arg-type]
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/7", response_model=CashFlowForecastResponse)
async def forecast_7(session: AsyncSession = Depends(get_db)) -> CashFlowForecastResponse:
    return await response_for(7, session)


@router.get("/30", response_model=CashFlowForecastResponse)
async def forecast_30(session: AsyncSession = Depends(get_db)) -> CashFlowForecastResponse:
    return await response_for(30, session)


@router.get("/90", response_model=CashFlowForecastResponse)
async def forecast_90(session: AsyncSession = Depends(get_db)) -> CashFlowForecastResponse:
    return await response_for(90, session)