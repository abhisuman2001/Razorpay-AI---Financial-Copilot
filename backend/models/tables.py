from datetime import date

from sqlalchemy import Date, Float, String
from sqlalchemy.orm import Mapped, mapped_column

from lib.db import Base


class FinancialTransaction(Base):
    __tablename__ = "financial_transactions"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    transaction_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    reference: Mapped[str] = mapped_column(String(80), nullable=False)
    category: Mapped[str] = mapped_column(String(40), nullable=False)
    direction: Mapped[str] = mapped_column(String(10), nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    expected_amount: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String(15), nullable=False)