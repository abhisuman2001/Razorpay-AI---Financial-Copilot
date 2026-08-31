"""Shared CSV-building helpers for the financial data import test suite."""

from __future__ import annotations

import csv
import io
import time
import uuid


def unique_suffix() -> str:
    return f"{int(time.time() * 1000) % 10_000_000}{uuid.uuid4().hex[:6]}"


def build_csv(headers: list[str], rows: list[list[str]]) -> bytes:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(headers)
    writer.writerows(rows)
    return buffer.getvalue().encode("utf-8")


def analyze(client, source_type: str, filename: str, content: bytes, timeout: float = 30.0):
    return client.post(
        "/imports/analyze",
        data={"source_type": source_type},
        files={"file": (filename, content, "text/csv")},
        timeout=timeout,
    )


def apply_mapping(client, batch_id: str, mapping: dict):
    return client.put(f"/imports/{batch_id}/mapping", json={"mapping": mapping})


def confirm_import(client, batch_id: str):
    return client.post(f"/imports/{batch_id}/import")


def rerun_reconciliation(client, batch_id: str):
    return client.post(f"/imports/{batch_id}/reconcile")


def get_transactions(client, batch_id: str, match_status: str | None = None, limit: int = 200):
    params = {"limit": limit}
    if match_status:
        params["match_status"] = match_status
    return client.get(f"/imports/{batch_id}/transactions", params=params)
