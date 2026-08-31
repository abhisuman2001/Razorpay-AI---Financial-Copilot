from __future__ import annotations

import math
import random
from collections import defaultdict
from datetime import date, datetime, time, timedelta, timezone
from typing import Any
from uuid import NAMESPACE_URL, uuid5

import numpy as np
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from models.merchant_tables import (
    Chargeback,
    Customer,
    DatasetRun,
    Expense,
    FailedPayment,
    FinancialAnomaly,
    Order,
    Payment,
    Refund,
    Settlement,
)


FIRST_NAMES = [
    "Aarav", "Aditi", "Arjun", "Diya", "Ishaan", "Kavya", "Meera", "Neha",
    "Pranav", "Rhea", "Rohan", "Saanvi", "Siddharth", "Tara", "Vikram", "Zoya",
]
LAST_NAMES = [
    "Agarwal", "Bansal", "Desai", "Gupta", "Iyer", "Jain", "Kapoor", "Khan",
    "Mehta", "Nair", "Patel", "Rao", "Shah", "Sharma", "Singh", "Verma",
]
LOCATIONS = [
    ("Mumbai", "Maharashtra"), ("Bengaluru", "Karnataka"), ("Delhi", "Delhi"),
    ("Hyderabad", "Telangana"), ("Chennai", "Tamil Nadu"), ("Pune", "Maharashtra"),
    ("Ahmedabad", "Gujarat"), ("Kolkata", "West Bengal"), ("Jaipur", "Rajasthan"),
    ("Kochi", "Kerala"), ("Lucknow", "Uttar Pradesh"), ("Indore", "Madhya Pradesh"),
]
METHODS = ["upi", "card", "netbanking", "wallet", "emi"]
METHOD_WEIGHTS = [0.48, 0.31, 0.11, 0.07, 0.03]
FAILURES = [
    ("BAD_REQUEST_PAYMENT_FAILED", "Payment was declined by the customer's bank", "authorization", True),
    ("GATEWAY_ERROR", "Bank gateway did not respond in time", "gateway", True),
    ("BAD_REQUEST_INSUFFICIENT_FUNDS", "Insufficient funds in customer account", "authorization", True),
    ("BAD_REQUEST_OTP_INVALID", "Customer entered an invalid OTP", "authentication", True),
    ("BAD_REQUEST_CARD_EXPIRED", "The card has expired", "validation", False),
    ("SERVER_ERROR", "Payment network returned a temporary error", "gateway", True),
]
EXPENSES = {
    "Payroll": ["PeopleStrong Payroll", "Contractor Payouts", "Staff Benefits"],
    "Marketing": ["Meta Ads", "Google Ads", "Influencer Network", "Brand Studio"],
    "Inventory": ["Western India Supply Co", "Metro Wholesale", "Southline Distributors"],
    "Logistics": ["Delhivery", "Blue Dart", "Shiprocket", "Local Fleet Services"],
    "Software": ["Commerce SaaS", "Support Desk", "Cloud Tools", "Accounting Suite"],
    "Rent": ["Northstar Offices", "Warehouse Leasing Co"],
    "Professional services": ["KRM Legal", "Ledger Partners", "Audit Associates"],
    "Utilities": ["Electricity Board", "Broadband Services", "Mobile Services"],
}


def _stable_id(prefix: str, seed: int, index: int) -> str:
    token = uuid5(NAMESPACE_URL, f"razorpay-ai:{seed}:{prefix}:{index}").hex[:14]
    return f"{prefix}_{token}"


def _utc_naive(value: datetime) -> datetime:
    return value.astimezone(timezone.utc).replace(tzinfo=None)


def _random_datetime(rng: random.Random, start: date, days: int) -> datetime:
    day = start + timedelta(days=rng.randrange(days))
    hour = rng.choices(range(24), weights=[1, 1, 1, 1, 1, 2, 4, 7, 10, 12, 13, 13, 12, 11, 11, 12, 14, 16, 17, 15, 11, 7, 4, 2])[0]
    return datetime.combine(day, time(hour, rng.randrange(60), rng.randrange(60)))


def build_merchant_dataset(payment_count: int = 20_000, seed: int = 2026) -> dict[str, list[dict[str, Any]]]:
    if payment_count < 20_000:
        raise ValueError("payment_count must be at least 20,000")

    rng = random.Random(seed)
    np_rng = np.random.default_rng(seed)
    generated_at = datetime.now(timezone.utc).replace(microsecond=0)
    period_end = generated_at.date()
    period_start = period_end - timedelta(days=364)
    run_id = _stable_id("run", seed, int(generated_at.timestamp()))

    customer_count = max(3_500, int(payment_count * 0.22))
    order_count = int(payment_count * 0.86)
    customers: list[dict[str, Any]] = []
    for index in range(customer_count):
        first = rng.choice(FIRST_NAMES)
        last = rng.choice(LAST_NAMES)
        city, state = rng.choice(LOCATIONS)
        created_at = _random_datetime(rng, period_start - timedelta(days=365), 365)
        customers.append({
            "customer_id": _stable_id("cust", seed, index),
            "name": f"{first} {last}",
            "email": f"{first}.{last}.{index}@example.in".lower(),
            "phone": f"+91{rng.randrange(7000000000, 9999999999)}",
            "city": city,
            "state": state,
            "segment": rng.choices(["new", "repeat", "vip"], weights=[0.48, 0.44, 0.08])[0],
            "created_at": created_at,
        })

    customer_weights = np_rng.pareto(2.8, customer_count) + 0.25
    customer_weights = customer_weights / customer_weights.sum()
    customer_indices = np_rng.choice(customer_count, size=order_count, p=customer_weights)
    spike_days = [period_end - timedelta(days=92), period_end - timedelta(days=47), period_end - timedelta(days=16)]
    spike_order_indices = set(rng.sample(range(order_count), max(75, payment_count // 250)))
    spike_by_index = {idx: spike_days[pos % len(spike_days)] for pos, idx in enumerate(sorted(spike_order_indices))}

    orders: list[dict[str, Any]] = []
    for index in range(order_count):
        customer = customers[int(customer_indices[index])]
        created_at = _random_datetime(rng, period_start, 365)
        base_rupees = float(np_rng.lognormal(mean=math.log(1_450), sigma=0.78))
        amount = int(round(min(max(base_rupees, 149), 85_000) * 100))
        if index in spike_by_index:
            spike_day = spike_by_index[index]
            created_at = datetime.combine(spike_day, time(rng.randrange(10, 22), rng.randrange(60), rng.randrange(60)))
            amount = int(amount * rng.uniform(4.5, 8.0))
        orders.append({
            "order_id": _stable_id("order", seed, index),
            "customer_id": customer["customer_id"],
            "amount": amount,
            "currency": "INR",
            "status": "created",
            "receipt": f"rcpt_{period_end.year}_{index + 1:06d}",
            "created_at": created_at,
        })

    payments: list[dict[str, Any]] = []
    attempts_by_order: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for index in range(payment_count):
        order_index = index if index < order_count else rng.randrange(order_count)
        order = orders[order_index]
        attempt_number = len(attempts_by_order[order["order_id"]])
        created_at = order["created_at"] + timedelta(minutes=attempt_number * rng.randint(3, 45), seconds=rng.randrange(60))
        status = rng.choices(["captured", "failed", "authorized"], weights=[0.91, 0.07, 0.02])[0]
        captured_at = created_at + timedelta(seconds=rng.randrange(2, 140)) if status == "captured" else None
        payment = {
            "payment_id": _stable_id("pay", seed, index),
            "order_id": order["order_id"],
            "customer_id": order["customer_id"],
            "amount": order["amount"],
            "currency": "INR",
            "status": status,
            "payment_method": rng.choices(METHODS, weights=METHOD_WEIGHTS)[0],
            "created_at": created_at,
            "captured_at": captured_at,
        }
        payments.append(payment)
        attempts_by_order[order["order_id"]].append(payment)

    anomalies: list[dict[str, Any]] = []

    def add_anomaly(
        anomaly_type: str,
        entity_type: str,
        entity_id: str,
        description: str,
        related_entity_id: str | None = None,
        expected_amount: int | None = None,
        actual_amount: int | None = None,
    ) -> None:
        index = len(anomalies)
        anomalies.append({
            "anomaly_id": _stable_id("anom", seed, index),
            "dataset_run_id": run_id,
            "anomaly_type": anomaly_type,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "related_entity_id": related_entity_id,
            "expected_amount": expected_amount,
            "actual_amount": actual_amount,
            "description": description,
            "created_at": _utc_naive(generated_at),
        })

    retry_candidates = [items for items in attempts_by_order.values() if len(items) > 1]
    duplicate_groups = rng.sample(retry_candidates, min(max(40, payment_count // 500), len(retry_candidates)))
    for attempts in duplicate_groups:
        original, duplicate = attempts[0], attempts[1]
        duplicate["status"] = "captured"
        duplicate["created_at"] = original["created_at"] + timedelta(seconds=rng.randrange(20, 90))
        duplicate["captured_at"] = duplicate["created_at"] + timedelta(seconds=rng.randrange(2, 20))
        add_anomaly(
            "duplicate_looking_payment", "payment", duplicate["payment_id"],
            "Same order, customer, and amount appeared within 90 seconds; IDs remain distinct.",
            related_entity_id=original["payment_id"], expected_amount=original["amount"], actual_amount=duplicate["amount"],
        )

    payment_by_order = {payment["order_id"]: payment for payment in payments}
    for order_index in spike_order_indices:
        payment = payment_by_order.get(orders[order_index]["order_id"])
        if payment:
            add_anomaly(
                "unusual_payment_spike", "payment", payment["payment_id"],
                "Payment belongs to a controlled high-value sales spike window.", actual_amount=payment["amount"],
            )

    captured = [payment for payment in payments if payment["status"] == "captured"]
    failed = [payment for payment in payments if payment["status"] == "failed"]
    failed_payments: list[dict[str, Any]] = []
    for index, payment in enumerate(failed):
        code, description, stage, retryable = rng.choice(FAILURES)
        failed_payments.append({
            "failed_payment_id": _stable_id("fail", seed, index),
            "payment_id": payment["payment_id"],
            "error_code": code,
            "error_description": description,
            "failure_stage": stage,
            "retryable": retryable,
            "failed_at": payment["created_at"] + timedelta(seconds=rng.randrange(1, 60)),
        })

    refundable = [payment for payment in captured if payment["created_at"].date() <= period_end - timedelta(days=7)]
    refund_targets = rng.sample(refundable, min(int(len(captured) * 0.055), len(refundable)))
    refunds: list[dict[str, Any]] = []
    refunds_by_payment: dict[str, int] = defaultdict(int)
    for index, payment in enumerate(refund_targets):
        full = rng.random() < 0.38
        amount = payment["amount"] if full else max(100, int(payment["amount"] * rng.uniform(0.12, 0.72)))
        created_at = payment["captured_at"] + timedelta(days=rng.randint(1, 21), minutes=rng.randrange(1440))
        status = rng.choices(["processed", "pending", "failed"], weights=[0.94, 0.04, 0.02])[0]
        refunds.append({
            "refund_id": _stable_id("rfnd", seed, index),
            "payment_id": payment["payment_id"],
            "amount": amount,
            "currency": "INR",
            "status": status,
            "reason": rng.choice(["customer_request", "item_returned", "duplicate_order", "service_issue", "fraud_review"]),
            "created_at": created_at,
            "processed_at": created_at + timedelta(hours=rng.randint(1, 36)) if status == "processed" else None,
        })
        if status == "processed":
            refunds_by_payment[payment["payment_id"]] += amount

    for order in orders:
        attempts = attempts_by_order[order["order_id"]]
        captured_attempts = [payment for payment in attempts if payment["status"] == "captured"]
        if captured_attempts:
            refund_total = sum(refunds_by_payment[payment["payment_id"]] for payment in captured_attempts)
            order["status"] = "refunded" if refund_total >= order["amount"] else "partially_refunded" if refund_total else "paid"
        elif any(payment["status"] == "authorized" for payment in attempts):
            order["status"] = "authorized"
        else:
            order["status"] = "attempted"

    settlement_eligible = [payment for payment in captured if payment["captured_at"].date() <= period_end - timedelta(days=2)]
    missing_targets = {payment["payment_id"] for payment in rng.sample(settlement_eligible, max(30, payment_count // 500))}
    remaining_for_anomalies = [payment for payment in settlement_eligible if payment["payment_id"] not in missing_targets]
    mismatch_targets = {payment["payment_id"] for payment in rng.sample(remaining_for_anomalies, max(35, payment_count // 450))}
    delayed_pool = [payment for payment in remaining_for_anomalies if payment["payment_id"] not in mismatch_targets]
    delayed_targets = {payment["payment_id"] for payment in rng.sample(delayed_pool, max(45, payment_count // 400))}
    settlements: list[dict[str, Any]] = []
    for payment in settlement_eligible:
        if payment["payment_id"] in missing_targets:
            add_anomaly(
                "unmatched_captured_payment", "payment", payment["payment_id"],
                "Captured payment intentionally has no corresponding settlement row.", actual_amount=payment["amount"],
            )
            continue
        gross = payment["amount"]
        refund_amount = min(refunds_by_payment[payment["payment_id"]], gross)
        fees = int(round(gross * (0.018 if payment["payment_method"] == "upi" else 0.021)))
        taxes = int(round(fees * 0.18))
        expected_net = gross - refund_amount - fees - taxes
        net = expected_net
        settlement_delay = 2
        if payment["payment_id"] in mismatch_targets:
            net += rng.choice([-1, 1]) * rng.randint(125, 2500)
        if payment["payment_id"] in delayed_targets:
            settlement_delay = rng.randint(7, 14)
        settlement_id = _stable_id("setl", seed, len(settlements))
        settlements.append({
            "settlement_id": settlement_id,
            "payment_id": payment["payment_id"],
            "external_reference": f"utr{seed}{len(settlements):09d}",
            "gross_amount": gross,
            "refund_amount": refund_amount,
            "fees": fees,
            "taxes": taxes,
            "net_settlement": net,
            "settlement_date": min(payment["captured_at"].date() + timedelta(days=settlement_delay), period_end),
            "status": rng.choices(["settled", "processing", "failed"], weights=[0.975, 0.02, 0.005])[0],
        })
        if payment["payment_id"] in mismatch_targets:
            add_anomaly(
                "settlement_amount_mismatch", "settlement", settlement_id,
                "Net settlement differs from gross minus refunds, fees, and taxes.",
                related_entity_id=payment["payment_id"], expected_amount=expected_net, actual_amount=net,
            )
        if payment["payment_id"] in delayed_targets:
            add_anomaly(
                "delayed_settlement", "settlement", settlement_id,
                f"Settlement posted after {settlement_delay} days instead of the expected T+2 window.",
                related_entity_id=payment["payment_id"], expected_amount=expected_net, actual_amount=net,
            )

    orphan_count = max(20, payment_count // 800)
    for index in range(orphan_count):
        gross = rng.randint(20_000, 300_000)
        fees = int(gross * 0.02)
        taxes = int(fees * 0.18)
        settlement_id = _stable_id("orphan", seed, index)
        settlements.append({
            "settlement_id": settlement_id,
            "payment_id": None,
            "external_reference": f"utr_orphan_{seed}_{index:05d}",
            "gross_amount": gross,
            "refund_amount": 0,
            "fees": fees,
            "taxes": taxes,
            "net_settlement": gross - fees - taxes,
            "settlement_date": period_end - timedelta(days=rng.randrange(90)),
            "status": "settled",
        })
        add_anomaly(
            "unmatched_settlement", "settlement", settlement_id,
            "Settlement intentionally has no payment reference for reconciliation testing.", actual_amount=gross - fees - taxes,
        )

    chargeback_targets = rng.sample(
        [payment for payment in captured if payment["captured_at"].date() <= period_end - timedelta(days=30)],
        max(55, int(payment_count * 0.0035)),
    )
    chargebacks: list[dict[str, Any]] = []
    for index, payment in enumerate(chargeback_targets):
        opened_at = payment["captured_at"] + timedelta(days=rng.randint(5, 45))
        status = rng.choices(["open", "under_review", "won", "lost"], weights=[0.28, 0.34, 0.23, 0.15])[0]
        resolved_at = opened_at + timedelta(days=rng.randint(7, 28)) if status in {"won", "lost"} else None
        chargeback_id = _stable_id("cbk", seed, index)
        amount = payment["amount"] if rng.random() < 0.82 else int(payment["amount"] * rng.uniform(0.3, 0.8))
        chargebacks.append({
            "chargeback_id": chargeback_id,
            "payment_id": payment["payment_id"],
            "amount": amount,
            "reason_code": rng.choice(["fraudulent", "product_not_received", "duplicate_processing", "credit_not_processed", "not_as_described"]),
            "status": status,
            "opened_at": opened_at,
            "due_at": opened_at + timedelta(days=10),
            "resolved_at": resolved_at,
        })
        add_anomaly(
            "chargeback", "chargeback", chargeback_id,
            "Controlled chargeback linked to a captured payment.", related_entity_id=payment["payment_id"], actual_amount=amount,
        )

    expense_count = max(1_800, payment_count // 10)
    expense_categories = list(EXPENSES)
    category_weights = [0.22, 0.17, 0.21, 0.14, 0.08, 0.06, 0.06, 0.06]
    expenses: list[dict[str, Any]] = []
    for index in range(expense_count):
        category = rng.choices(expense_categories, weights=category_weights)[0]
        recurring = category in {"Payroll", "Software", "Rent", "Utilities"} and rng.random() < 0.78
        base = {
            "Payroll": 450_000, "Marketing": 85_000, "Inventory": 180_000, "Logistics": 42_000,
            "Software": 18_000, "Rent": 120_000, "Professional services": 75_000, "Utilities": 14_000,
        }[category]
        amount = max(500, int(np_rng.lognormal(math.log(base), 0.55)))
        expenses.append({
            "expense_id": _stable_id("exp", seed, index),
            "category": category,
            "vendor": rng.choice(EXPENSES[category]),
            "amount": amount,
            "currency": "INR",
            "date": period_start + timedelta(days=rng.randrange(365)),
            "recurring": recurring,
            "payment_mode": rng.choice(["bank_transfer", "corporate_card", "upi", "direct_debit"]),
        })

    return {
        "dataset_runs": [{
            "id": run_id,
            "seed": seed,
            "payment_count": payment_count,
            "generated_at": _utc_naive(generated_at),
            "period_start": period_start,
            "period_end": period_end,
        }],
        "customers": customers,
        "orders": orders,
        "payments": payments,
        "refunds": refunds,
        "settlements": settlements,
        "expenses": expenses,
        "chargebacks": chargebacks,
        "failed_payments": failed_payments,
        "anomalies": anomalies,
    }


async def replace_merchant_dataset(
    session: AsyncSession, payment_count: int = 20_000, seed: int = 2026
) -> dict[str, int | str]:
    dataset = build_merchant_dataset(payment_count=payment_count, seed=seed)
    delete_order = [
        FinancialAnomaly, Chargeback, FailedPayment, Settlement, Refund, Payment, Order, Customer, Expense, DatasetRun,
    ]
    for model in delete_order:
        await session.execute(delete(model))

    insert_plan = [
        (DatasetRun, "dataset_runs"), (Customer, "customers"), (Order, "orders"),
        (Payment, "payments"), (Refund, "refunds"), (Settlement, "settlements"),
        (Expense, "expenses"), (Chargeback, "chargebacks"),
        (FailedPayment, "failed_payments"), (FinancialAnomaly, "anomalies"),
    ]
    for model, key in insert_plan:
        await session.run_sync(lambda sync_session, m=model, rows=dataset[key]: sync_session.bulk_insert_mappings(m, rows))
    await session.commit()
    return {
        "dataset_run_id": dataset["dataset_runs"][0]["id"],
        **{key: len(rows) for key, rows in dataset.items() if key != "dataset_runs"},
    }