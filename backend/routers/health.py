"""
Financial Health Score and Alerts endpoints.

The health score and alerts are calculated deterministically in the backend.
The LLM never calculates or modifies these values.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from lib.db import get_db
from services.alerts import Alert, detect_alerts
from services.health_score import HealthScore, calculate_health_score

router = APIRouter(prefix="/health", tags=["financial health"])


@router.get("/score", response_model=HealthScore)
async def get_health_score(session: AsyncSession = Depends(get_db)) -> HealthScore:
    """Get the deterministic financial health score."""
    return await calculate_health_score(session)


@router.get("/alerts", response_model=list[Alert])
async def get_alerts(session: AsyncSession = Depends(get_db)) -> list[Alert]:
    """Get proactive financial alerts based on deterministic rules."""
    return await detect_alerts(session)
