"""Criterion: Columns are auto-detected and manually mappable."""

from tests.helpers_imports import analyze, apply_mapping, build_csv, unique_suffix


def _csv_with_synonym_headers(suffix: str) -> bytes:
    return build_csv(
        ["Txn ID", "Order Ref", "Txn Date", "Amount (INR)", "Type", "Notes", "Currency", "Status", "Customer"],
        [
            [f"tscheck-map-{suffix}-1", f"tscheck-map-ref-{suffix}-1", "2024-02-01", "2500.00", "credit", "note one", "INR", "captured", "Acme Co"],
            [f"tscheck-map-{suffix}-2", f"tscheck-map-ref-{suffix}-2", "2024-02-02", "3000.00", "debit", "note two", "INR", "captured", "Beta Ltd"],
        ],
    )


def test_columns_auto_detected_with_confidence(client):
    suffix = unique_suffix()
    resp = analyze(client, "bank", f"tscheck-mapdetect-{suffix}.csv", _csv_with_synonym_headers(suffix))
    assert resp.status_code == 200, resp.text[:300]
    body = resp.json()
    suggestions = {item["internal_field"]: item for item in body["suggestions"]}
    assert suggestions["date"]["detected_column"] == "Txn Date"
    assert suggestions["date"]["confidence"] > 0
    assert suggestions["amount"]["detected_column"] == "Amount (INR)"
    assert suggestions["amount"]["confidence"] > 0
    # mapping auto-applied from the highest-confidence suggestions
    assert body["mapping"]["date"] == "Txn Date"
    assert body["mapping"]["amount"] == "Amount (INR)"


def test_manual_mapping_can_be_applied(client):
    suffix = unique_suffix()
    resp = analyze(client, "bank", f"tscheck-mapmanual-{suffix}.csv", _csv_with_synonym_headers(suffix))
    assert resp.status_code == 200, resp.text[:300]
    batch_id = resp.json()["batch"]["id"]
    new_mapping = {
        "transaction_id": "Txn ID", "reference": "Order Ref", "date": "Txn Date", "amount": "Amount (INR)",
        "debit": None, "credit": None, "direction": "Type", "description": "Notes",
        "currency": "Currency", "status": "Status", "counterparty": "Customer",
    }
    put_resp = apply_mapping(client, batch_id, new_mapping)
    assert put_resp.status_code == 200, put_resp.text[:300]
    updated = put_resp.json()
    assert updated["mapping"]["counterparty"] == "Customer"
    assert updated["mapping"]["description"] == "Notes"


def test_invalid_required_mapping_rejected(client):
    suffix = unique_suffix()
    resp = analyze(client, "bank", f"tscheck-mapinvalid-{suffix}.csv", _csv_with_synonym_headers(suffix))
    assert resp.status_code == 200, resp.text[:300]
    batch_id = resp.json()["batch"]["id"]

    # Missing required date mapping and no amount/debit/credit mapping at all.
    missing_required = {
        "transaction_id": "Txn ID", "reference": "Order Ref", "date": None, "amount": None,
        "debit": None, "credit": None, "direction": "Type", "description": "Notes",
        "currency": "Currency", "status": "Status", "counterparty": "Customer",
    }
    resp1 = apply_mapping(client, batch_id, missing_required)
    assert resp1.status_code == 422, resp1.text[:300]

    # Column that doesn't exist in this CSV's header row.
    unknown_column = {
        "transaction_id": "Txn ID", "reference": "Order Ref", "date": "Txn Date", "amount": "Does Not Exist",
        "debit": None, "credit": None, "direction": "Type", "description": "Notes",
        "currency": "Currency", "status": "Status", "counterparty": "Customer",
    }
    resp2 = apply_mapping(client, batch_id, unknown_column)
    assert resp2.status_code == 422, resp2.text[:300]
