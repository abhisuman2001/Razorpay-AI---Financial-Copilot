"""Criterion: Four universal CSV source types and limits are supported."""

import httpx
import pytest

from tests.conftest import API_URL
from tests.helpers_imports import analyze, build_csv, unique_suffix

SOURCE_TYPES = ["bank", "payment_gateway", "accounting", "marketplace"]


def _minimal_csv(suffix: str) -> bytes:
    return build_csv(
        ["Transaction ID", "Reference", "Date", "Amount", "Type", "Description"],
        [[f"tscheck-limits-{suffix}-1", f"tscheck-limits-ref-{suffix}-1", "2024-01-05", "1000.00", "credit", "sample row"]],
    )


def test_all_four_source_types_accept_valid_csv(client):
    suffix = unique_suffix()
    for source_type in SOURCE_TYPES:
        content = _minimal_csv(f"{suffix}-{source_type}")
        resp = analyze(client, source_type, f"tscheck-{suffix}-{source_type}.csv", content)
        assert resp.status_code == 200, f"{source_type}: {resp.status_code} {resp.text[:300]}"
        body = resp.json()
        assert body["batch"]["source_type"] == source_type
        assert body["batch"]["status"] == "ANALYZED"
        assert body["batch"]["row_count"] == 1


def test_empty_csv_rejected(client):
    resp = analyze(client, "bank", "tscheck-empty.csv", b"")
    assert resp.status_code == 422, resp.text[:300]
    assert "empty" in str(resp.json()["detail"]).lower()


def test_oversized_csv_rejected():
    # Content only needs to exceed the 25 MB cap; the size check runs before CSV parsing.
    oversized = b"a" * (25 * 1024 * 1024 + 2048)
    with httpx.Client(base_url=API_URL, timeout=60.0) as big_client:
        resp = analyze(big_client, "bank", "tscheck-oversized.csv", oversized, timeout=60.0)
    assert resp.status_code == 422, resp.text[:300]
    assert "25 mb" in str(resp.json()["detail"]).lower()


def test_row_limit_exceeded_rejected():
    suffix = unique_suffix()
    header = "Transaction ID,Reference,Date,Amount,Type,Description\n"
    row_template = f"tscheck-rowlimit-{suffix}-{{n}},ref-{{n}},2024-01-05,10.00,credit,bulk row\n"
    rows = "".join(row_template.format(n=i) for i in range(100_001))
    content = (header + rows).encode("utf-8")
    with httpx.Client(base_url=API_URL, timeout=90.0) as big_client:
        resp = analyze(big_client, "bank", f"tscheck-rowlimit-{suffix}.csv", content, timeout=90.0)
    assert resp.status_code == 422, resp.text[:300]
    assert "100,000" in str(resp.json()["detail"]) or "row limit" in str(resp.json()["detail"]).lower()
