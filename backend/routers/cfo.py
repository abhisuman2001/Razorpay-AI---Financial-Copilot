from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ai.service import answer_question, daily_insights
from lib.db import get_db
from models.cfo import CfoChatRequest, CfoChatResponse, DailyInsightsResponse, FinancialToolResult
from services.financial_tools import TOOL_REGISTRY

router = APIRouter(prefix="/cfo", tags=["ai cfo"])


@router.get("/insights", response_model=DailyInsightsResponse)
async def get_daily_insights(session: AsyncSession = Depends(get_db)) -> DailyInsightsResponse:
    return await daily_insights(session)


@router.post("/chat", response_model=CfoChatResponse)
async def chat(request: CfoChatRequest, session: AsyncSession = Depends(get_db)) -> CfoChatResponse:
    return await answer_question(session, request.question)


@router.get("/tools/{tool_name}", response_model=FinancialToolResult)
async def run_financial_tool(
    tool_name: str, session: AsyncSession = Depends(get_db)
) -> FinancialToolResult:
    tool = TOOL_REGISTRY.get(tool_name)
    if not tool:
        raise HTTPException(status_code=404, detail="Unknown financial tool")
    return await tool(session)