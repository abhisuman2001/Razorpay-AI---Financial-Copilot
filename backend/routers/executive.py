from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from lib.db import get_db
from models.executive import ExecutiveDashboardResponse
from services.executive import build_executive_dashboard

router = APIRouter(prefix="/executive", tags=["executive dashboard"])


@router.get("/dashboard", response_model=ExecutiveDashboardResponse)
async def executive_dashboard(
    session: AsyncSession = Depends(get_db),
) -> ExecutiveDashboardResponse:
    return await build_executive_dashboard(session)