import argparse
import asyncio

from lib.db import Base, SessionLocal, engine
from models import merchant_tables  # noqa: F401
from services.data_generator import replace_merchant_dataset


async def generate(payment_count: int, seed: int) -> None:
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with SessionLocal() as session:
        counts = await replace_merchant_dataset(session, payment_count=payment_count, seed=seed)
    await engine.dispose()
    print("Synthetic merchant dataset generated")
    for name, count in counts.items():
        print(f"  {name}: {count}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Regenerate the local Razorpay-like merchant dataset.")
    parser.add_argument("--payments", type=int, default=20_000, help="Payment records to generate (minimum 20,000).")
    parser.add_argument("--seed", type=int, default=2026, help="Deterministic random seed.")
    args = parser.parse_args()
    asyncio.run(generate(args.payments, args.seed))


if __name__ == "__main__":
    main()