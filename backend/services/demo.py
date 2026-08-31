import asyncio
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from models.demo import DemoScenario, DemoScenarioActivation, DemoScenarioList
from models.merchant_tables import DemoScenarioState
from services.data_generator import replace_merchant_dataset


SCENARIO_DEFINITIONS = [
    {
        "id": "healthy_business", "name": "Healthy Business", "signal": "Stable",
        "description": "Baseline merchant performance with healthy cash generation and manageable exceptions.",
        "expected_effects": ["Stable revenue", "Positive cash outlook", "Low operational risk"],
    },
    {
        "id": "revenue_decline", "name": "Revenue Decline", "signal": "Revenue",
        "description": "Current-month captured payment value falls sharply against the previous month.",
        "expected_effects": ["Lower current revenue", "Weaker settled income", "Revenue decline insight"],
    },
    {
        "id": "payment_failure_spike", "name": "Payment Failure Spike", "signal": "Payments",
        "description": "A recent gateway incident raises failed payments and reduces successful conversion.",
        "expected_effects": ["Higher failure count", "Lower captured revenue", "Failure risk insight"],
    },
    {
        "id": "cash_flow_risk", "name": "Cash Flow Risk", "signal": "Liquidity",
        "description": "Recent operating expenses surge and pressure the modeled cash outlook.",
        "expected_effects": ["Higher outgoing cash", "Lower forecast balance", "Liquidity warning"],
    },
    {
        "id": "settlement_discrepancy", "name": "Settlement Discrepancy", "signal": "Reconciliation",
        "description": "A controlled group of net settlements differs from deterministic expected amounts.",
        "expected_effects": ["More mismatches", "Higher discrepancy", "Reconciliation alert"],
    },
    {
        "id": "high_refund_rate", "name": "High Refund Rate", "signal": "Refunds",
        "description": "Processed refunds increase across recent captured payments while links remain traceable.",
        "expected_effects": ["Higher refund value", "Lower net settlements", "Refund-rate insight"],
    },
]

_activation_lock = asyncio.Lock()


async def get_scenarios(session: AsyncSession) -> DemoScenarioList:
    state = await session.get(DemoScenarioState, "global")
    active_id = state.scenario_id if state else "healthy_business"
    return DemoScenarioList(
        active_scenario_id=active_id,
        scenarios=[DemoScenario(**definition, active=definition["id"] == active_id) for definition in SCENARIO_DEFINITIONS],
    )


async def activate_scenario(
    session: AsyncSession,
    scenario_id: str,
    payment_count: int = 20_000,
    seed: int = 2026,
) -> DemoScenarioActivation:
    if scenario_id not in {item["id"] for item in SCENARIO_DEFINITIONS}:
        raise ValueError("Unknown demo scenario")

    async with _activation_lock:
        counts = await replace_merchant_dataset(
            session, payment_count=payment_count, seed=seed, scenario_id=scenario_id
        )
        activated_at = datetime.now(timezone.utc).replace(microsecond=0)
        state = await session.get(DemoScenarioState, "global")
        if not state:
            state = DemoScenarioState(
                id="global", scenario_id=scenario_id,
                activated_at=activated_at.replace(tzinfo=None),
                dataset_run_id=str(counts["dataset_run_id"]),
                payment_count=payment_count, seed=seed,
            )
            session.add(state)
        else:
            state.scenario_id = scenario_id
            state.activated_at = activated_at.replace(tzinfo=None)
            state.dataset_run_id = str(counts["dataset_run_id"])
            state.payment_count = payment_count
            state.seed = seed
        await session.commit()
        generated_records = {
            key: int(value) for key, value in counts.items() if key != "dataset_run_id"
        }
        return DemoScenarioActivation(
            active_scenario_id=scenario_id, activated_at=activated_at,
            dataset_run_id=str(counts["dataset_run_id"]), payment_count=payment_count,
            generated_records=generated_records,
            message="Scenario activated. All dashboards now use the regenerated SQLite dataset.",
        )