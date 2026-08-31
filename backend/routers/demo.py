from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from lib.db import get_db
from models.demo import DemoScenarioActivation, DemoScenarioList
from services.demo import activate_scenario, get_scenarios

router = APIRouter(prefix="/demo", tags=["demo mode"])


@router.get("/scenarios", response_model=DemoScenarioList)
async def list_scenarios(session: AsyncSession = Depends(get_db)) -> DemoScenarioList:
    return await get_scenarios(session)


@router.post("/scenarios/{scenario_id}/activate", response_model=DemoScenarioActivation)
async def set_scenario(
    scenario_id: str, session: AsyncSession = Depends(get_db)
) -> DemoScenarioActivation:
    try:
        return await activate_scenario(session, scenario_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc