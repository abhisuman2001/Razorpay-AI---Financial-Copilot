from datetime import date

from sqlalchemy import Date, Float, String
from sqlalchemy.orm import Mapped, mapped_column

from lib.db import Base


class FinancialTransaction(Base):
    __tablename__ = "financial_transactions"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    transaction_date: Mapped[date] = mapped_column(Date, index=True)
    reference: Mapped[str] = mapped_column(String(80))
    category: Mapped[str] = mapped_column(String(40))
    direction: Mapped[str] = mapped_column(String(10))
    amount: Mapped[float] = mapped_column(Float)
    expected_amount: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(15))
