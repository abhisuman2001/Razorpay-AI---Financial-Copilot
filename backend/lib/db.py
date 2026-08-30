"""Shared async SQLite + SQLAlchemy database boundary."""

import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

load_dotenv(Path(__file__).parent.parent / ".env")

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
DATABASE_URL = os.environ.get("DATABASE_URL", f"sqlite+aiosqlite:///{DATA_DIR / 'financial_copilot.db'}")


class Base(DeclarativeBase):
    pass


engine = create_async_engine(DATABASE_URL, future=True)
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_db() -> None:
    from models.tables import FinancialTransaction
    from services.synthetic import build_synthetic_transactions

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with SessionLocal() as session:
        count = await session.scalar(select(func.count(FinancialTransaction.id)))
        if not count:
            session.add_all(FinancialTransaction(**record) for record in build_synthetic_transactions())
            await session.commit()


async def get_db():
    async with SessionLocal() as session:
        yield session
