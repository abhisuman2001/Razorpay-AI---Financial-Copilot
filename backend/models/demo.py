from datetime import datetime

from pydantic import BaseModel


class DemoScenario(BaseModel):
    id: str
    name: str
    description: str
    signal: str
    expected_effects: list[str]
    active: bool


class DemoScenarioList(BaseModel):
    active_scenario_id: str
    scenarios: list[DemoScenario]


class DemoScenarioActivation(BaseModel):
    active_scenario_id: str
    activated_at: datetime
    dataset_run_id: str
    payment_count: int
    generated_records: dict[str, int]
    message: str