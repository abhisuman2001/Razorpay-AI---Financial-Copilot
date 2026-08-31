from collections import defaultdict
from datetime import date, datetime, time, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from lib.dates import today_iso
from models.merchant_tables import Payment, Refund, Settlement
from models.reconciliation import (
    ComponentComparison,
    ReconciliationRecord,
    ReconciliationStatus,
    ReconciliationSummary,
)


EXCEPTION_STATUSES: set[ReconciliationStatus] = {
    "PARTIALLY_MATCHED", "MISMATCHED", "PENDING", "UNRESOLVED",
}


def default_date_range() -> tuple[date, date]:
    date_to = date.fromisoformat(today_iso())
    return date_to - timedelta(days=89), date_to


def expected_fee(amount: int, payment_method: str) -> int:
    """Fee schedule is deterministic and matches the synthetic merchant contract."""
    return int(round(amount * (0.018 if payment_method == "upi" else 0.021)))


def expected_tax(fee: int) -> int:
    return int(round(fee * 0.18))


def _comparison(component: str, expected: int, actual: int | None) -> ComponentComparison:
    return ComponentComparison(
        component=component,
        expected_amount=expected,
        actual_amount=actual,
        difference_amount=None if actual is None else actual - expected,
        matches=actual == expected,
    )


def reconcile_payment(
    payment: Payment,
    settlement: Settlement | None,
    processed_refunds: int,
    today: date,
) -> ReconciliationRecord:
    fee = expected_fee(payment.amount, payment.payment_method)
    tax = expected_tax(fee)
    refund_amount = min(processed_refunds, payment.amount)
    expected_net = payment.amount - refund_amount - fee - tax

    if settlement is None:
        age_days = (today - payment.created_at.date()).days
        status: ReconciliationStatus = "PENDING" if age_days <= 2 else "UNRESOLVED"
        reason = (
            "Captured payment is still within the expected T+2 settlement window."
            if status == "PENDING"
            else "Captured payment has no settlement after the expected T+2 window."
        )
        comparisons = [
            _comparison("gross_payment", payment.amount, None),
            _comparison("refunds", refund_amount, None),
            _comparison("fees", fee, None),
            _comparison("taxes", tax, None),
            _comparison("net_settlement", expected_net, None),
        ]
        return ReconciliationRecord(
            id=f"rcn_{payment.payment_id}", payment_id=payment.payment_id, settlement_id=None,
            order_id=payment.order_id, customer_id=payment.customer_id,
            payment_method=payment.payment_method, currency=payment.currency,
            payment_created_at=payment.created_at, settlement_date=None,
            gross_payment=payment.amount, refund_amount=refund_amount, fees=fee, taxes=tax,
            expected_settlement=expected_net, actual_settlement=None,
            difference_amount=None, difference_percentage=None, status=status,
            possible_reason=reason, component_comparisons=comparisons,
        )

    comparisons = [
        _comparison("gross_payment", payment.amount, settlement.gross_amount),
        _comparison("refunds", refund_amount, settlement.refund_amount),
        _comparison("fees", fee, settlement.fees),
        _comparison("taxes", tax, settlement.taxes),
        _comparison("net_settlement", expected_net, settlement.net_settlement),
    ]
    difference = settlement.net_settlement - expected_net
    difference_percentage = round((difference / expected_net) * 100, 4) if expected_net else None
    component_mismatches = [item.component for item in comparisons[:-1] if not item.matches]
    settlement_delay = (settlement.settlement_date - payment.captured_at.date()).days if payment.captured_at else 0

    if settlement.status == "processing":
        status = "PENDING"
        reason = "Settlement record exists but is still processing."
    elif settlement.status == "failed":
        status = "UNRESOLVED"
        reason = "Settlement record is marked failed and requires operational review."
    elif difference != 0:
        status = "MISMATCHED"
        reason = (
            "Actual net is lower than expected; an extra deduction, refund, fee, or tax may have been applied."
            if difference < 0
            else "Actual net is higher than expected; a refund, fee, or tax deduction may be missing."
        )
    elif component_mismatches:
        status = "PARTIALLY_MATCHED"
        reason = f"Net amount matches, but component values differ: {', '.join(component_mismatches)}."
    else:
        status = "MATCHED"
        reason = (
            f"All amounts match exactly; settlement arrived after {settlement_delay} days."
            if settlement_delay > 2
            else "Gross, refunds, fees, taxes, and net settlement match exactly."
        )

    return ReconciliationRecord(
        id=f"rcn_{payment.payment_id}", payment_id=payment.payment_id,
        settlement_id=settlement.settlement_id, order_id=payment.order_id,
        customer_id=payment.customer_id, payment_method=payment.payment_method,
        currency=payment.currency, payment_created_at=payment.created_at,
        settlement_date=settlement.settlement_date, gross_payment=payment.amount,
        refund_amount=refund_amount, fees=fee, taxes=tax,
        expected_settlement=expected_net, actual_settlement=settlement.net_settlement,
        difference_amount=difference, difference_percentage=difference_percentage,
        status=status, possible_reason=reason, component_comparisons=comparisons,
    )


def reconcile_orphan(settlement: Settlement) -> ReconciliationRecord:
    actual = settlement.net_settlement
    comparisons = [
        _comparison("gross_payment", 0, settlement.gross_amount),
        _comparison("refunds", 0, settlement.refund_amount),
        _comparison("fees", 0, settlement.fees),
        _comparison("taxes", 0, settlement.taxes),
        _comparison("net_settlement", 0, actual),
    ]
    return ReconciliationRecord(
        id=f"rcn_{settlement.settlement_id}", payment_id=None,
        settlement_id=settlement.settlement_id, order_id=None, customer_id=None,
        payment_method=None, currency="INR", payment_created_at=None,
        settlement_date=settlement.settlement_date, gross_payment=0,
        refund_amount=0, fees=0, taxes=0, expected_settlement=0,
        actual_settlement=actual, difference_amount=actual,
        difference_percentage=None, status="UNRESOLVED",
        possible_reason="Settlement has no linked payment and cannot be reconciled automatically.",
        component_comparisons=comparisons,
    )


async def calculate_records(
    session: AsyncSession, date_from: date, date_to: date
) -> list[ReconciliationRecord]:
    payments = list((await session.scalars(
        select(Payment).where(
            Payment.status == "captured",
            Payment.created_at >= datetime.combine(date_from, time.min),
            Payment.created_at < datetime.combine(date_to + timedelta(days=1), time.min),
        ).order_by(Payment.created_at.desc())
    )).all())
    payment_ids = [payment.payment_id for payment in payments]
    settlements = list((await session.scalars(
        select(Settlement).where(Settlement.payment_id.in_(payment_ids))
    )).all()) if payment_ids else []
    refunds = list((await session.scalars(
        select(Refund).where(Refund.payment_id.in_(payment_ids), Refund.status == "processed")
    )).all()) if payment_ids else []

    settlement_by_payment = {item.payment_id: item for item in settlements if item.payment_id}
    refunds_by_payment: dict[str, int] = defaultdict(int)
    for refund in refunds:
        refunds_by_payment[refund.payment_id] += refund.amount

    today = date.fromisoformat(today_iso())
    records = [
        reconcile_payment(payment, settlement_by_payment.get(payment.payment_id), refunds_by_payment[payment.payment_id], today)
        for payment in payments
    ]
    orphan_settlements = list((await session.scalars(
        select(Settlement).where(
            Settlement.payment_id.is_(None),
            Settlement.settlement_date >= date_from,
            Settlement.settlement_date <= date_to,
        ).order_by(Settlement.settlement_date.desc())
    )).all())
    records.extend(reconcile_orphan(settlement) for settlement in orphan_settlements)
    return records


def summarize_records(
    records: list[ReconciliationRecord], date_from: date, date_to: date
) -> ReconciliationSummary:
    counts = {status: sum(record.status == status for record in records) for status in (
        "MATCHED", "PARTIALLY_MATCHED", "MISMATCHED", "PENDING", "UNRESOLVED"
    )}
    matched_for_rate = counts["MATCHED"] + counts["PARTIALLY_MATCHED"]
    return ReconciliationSummary(
        date_from=date_from, date_to=date_to, total_transactions=len(records),
        matched_transactions=counts["MATCHED"],
        partially_matched_transactions=counts["PARTIALLY_MATCHED"],
        mismatched_transactions=counts["MISMATCHED"],
        pending_transactions=counts["PENDING"],
        unresolved_transactions=counts["UNRESOLVED"],
        total_expected_amount=sum(record.expected_settlement for record in records),
        total_actual_amount=sum(record.actual_settlement or 0 for record in records),
        total_discrepancy=sum(abs(record.difference_amount or 0) for record in records),
        reconciliation_rate=round((matched_for_rate / len(records)) * 100, 2) if records else 0,
    )


async def get_record(session: AsyncSession, reconciliation_id: str) -> ReconciliationRecord | None:
    entity_id = reconciliation_id.removeprefix("rcn_")
    if entity_id.startswith("pay_"):
        payment = await session.get(Payment, entity_id)
        if not payment or payment.status != "captured":
            return None
        settlement = await session.scalar(select(Settlement).where(Settlement.payment_id == entity_id).limit(1))
        processed_refunds = await session.scalar(
            select(func.coalesce(func.sum(Refund.amount), 0)).where(
                Refund.payment_id == entity_id, Refund.status == "processed"
            )
        ) or 0
        return reconcile_payment(payment, settlement, processed_refunds, date.fromisoformat(today_iso()))
    settlement = await session.get(Settlement, entity_id)
    if settlement and settlement.payment_id is None:
        return reconcile_orphan(settlement)
    return None