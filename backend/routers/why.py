from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from lib.db import get_db
from models.why import CashBalanceAnalysis, WhyMetricResponse
from services.why import WHY_REGISTRY, cash_balance_analysis

router = APIRouter(prefix="/why", tags=["financial explainability"])


@router.get("/cash_balance/analysis", response_model=CashBalanceAnalysis)
async def cash_balance_analysis_endpoint(
    session: AsyncSession = Depends(get_db),
) -> CashBalanceAnalysis:
    """
    Full auditable breakdown of how the current cash balance was calculated.

    Returns the complete waterfall (opening → inflows → outflows → current),
    a daily cash-movement table, and a validation check that the calculated
    balance equals the value shown on the Cash Flow page.

    No LLM is involved. All values come from the deterministic financial engine.
    """
    return await cash_balance_analysis(session)


@router.get("/{metric_id}", response_model=WhyMetricResponse)
async def explain_metric(
    metric_id: str, session: AsyncSession = Depends(get_db)
) -> WhyMetricResponse:
    analyzer = WHY_REGISTRY.get(metric_id)
    if not analyzer:
        raise HTTPException(status_code=404, detail="Unknown explainable metric")
    return await analyzer(session)
