from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from lib.db import get_db
from models.why import WhyMetricResponse
from services.why import WHY_REGISTRY

router = APIRouter(prefix="/why", tags=["financial explainability"])


@router.get("/{metric_id}", response_model=WhyMetricResponse)
async def explain_metric(
    metric_id: str, session: AsyncSession = Depends(get_db)
) -> WhyMetricResponse:
    analyzer = WHY_REGISTRY.get(metric_id)
    if not analyzer:
        raise HTTPException(status_code=404, detail="Unknown explainable metric")
    return await analyzer(session)