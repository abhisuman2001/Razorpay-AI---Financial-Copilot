import argparse
import asyncio

from lib.db import Base, SessionLocal, engine
from models import merchant_tables  # noqa: F401
from services.demo import SCENARIO_DEFINITIONS, activate_scenario


async def generate(payment_count: int, seed: int, scenario_id: str) -> None:
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with SessionLocal() as session:
        result = await activate_scenario(
            session, scenario_id=scenario_id, payment_count=payment_count, seed=seed
        )
    await engine.dispose()
    print("Synthetic merchant dataset generated")
    print(f"  active_scenario: {result.active_scenario_id}")
    print(f"  dataset_run_id: {result.dataset_run_id}")
    for name, count in result.generated_records.items():
        print(f"  {name}: {count}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Regenerate the local Razorpay-like merchant dataset.")
    parser.add_argument("--payments", type=int, default=20_000, help="Payment records to generate (minimum 20,000).")
    parser.add_argument("--seed", type=int, default=2026, help="Deterministic random seed.")
    parser.add_argument(
        "--scenario", choices=[item["id"] for item in SCENARIO_DEFINITIONS],
        default="healthy_business", help="Demo scenario to activate.",
    )
    args = parser.parse_args()
    asyncio.run(generate(args.payments, args.seed, args.scenario))


if __name__ == "__main__":
    main()