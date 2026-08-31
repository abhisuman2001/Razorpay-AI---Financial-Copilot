"""Criterion: Every normalized transaction is traceable to original source information."""

import hashlib

from tests.helpers_imports import analyze, build_csv, confirm_import, get_transactions, unique_suffix


def _csv(suffix: str) -> bytes:
    return build_csv(
        ["Transaction ID", "Reference", "Date", "Amount", "Type", "Description"],
        [[f"tscheck-trace-{suffix}-1", f"tscheck-trace-ref-{suffix}-1", "2024-05-05", "4321.00", "credit", "traceable row"]],
    )


def test_transaction_trace_exposes_batch_row_and_original_fields(client):
    suffix = unique_suffix()
    filename = f"tscheck-trace-{suffix}.csv"
    content = _csv(suffix)
    expected_sha256 = hashlib.sha256(content).hexdigest()

    resp = analyze(client, "bank", filename, content)
    assert resp.status_code == 200, resp.text[:300]
    batch = resp.json()["batch"]
    batch_id = batch["id"]
    assert batch["filename"] == filename
    assert batch["file_sha256"] == expected_sha256

    import_resp = confirm_import(client, batch_id)
    assert import_resp.status_code == 200, import_resp.text[:300]

    workspace_resp = client.get(f"/imports/{batch_id}")
    assert workspace_resp.status_code == 200, workspace_resp.text[:300]
    workspace_batch = workspace_resp.json()["batch"]
    assert workspace_batch["file_sha256"] == expected_sha256
    assert workspace_batch["source_type"] == "bank"

    tx_resp = get_transactions(client, batch_id)
    assert tx_resp.status_code == 200, tx_resp.text[:300]
    items = tx_resp.json()["items"]
    assert len(items) == 1
    item = items[0]
    assert item["batch_id"] == batch_id
    assert item["source_type"] == "bank"
    assert item["source_row_number"] == 2  # header is row 1, first data row is row 2
    # normalized values traceable back to the raw source row
    assert item["amount"] == 432100
    assert item["transaction_date"] == "2024-05-05"
    assert item["external_id"] == f"tscheck-trace-{suffix}-1"
    # match evidence is present even for a lone, unmatched row
    assert item["match_status"] in {"UNMATCHED", "MATCHED", "AMOUNT_MISMATCH", "DATE_MISMATCH", "DUPLICATE"}
    assert item["match_rule"]
    assert isinstance(item["confidence"], (int, float))
    # untouched original CSV header/value fields are preserved verbatim
    original = item["original_data"]
    assert original["Transaction ID"] == f"tscheck-trace-{suffix}-1"
    assert original["Reference"] == f"tscheck-trace-ref-{suffix}-1"
    assert original["Date"] == "2024-05-05"
    assert original["Amount"] == "4321.00"
    assert original["Type"] == "credit"
    assert original["Description"] == "traceable row"
