"""Criterion: Rows normalize into one internal transaction model."""

from tests.helpers_imports import analyze, apply_mapping, build_csv, confirm_import, get_transactions, unique_suffix


def _messy_csv(suffix: str) -> bytes:
    return build_csv(
        ["Transaction ID", "Reference", "Date", "Amount", "Type", "Description", "Currency", "Status", "Counterparty"],
        [
            [f"tscheck-norm-{suffix}-1", f"tscheck-norm-ref-{suffix}-1", "05/01/2024", "Rs. 1,234.50", "credit", "Card settlement", "inr", "captured", "Acme Co"],
            [f"tscheck-norm-{suffix}-2", f"tscheck-norm-ref-{suffix}-2", "2024-01-06", "(500.75)", "debit", "Refund issued", "INR", "refunded", "Beta Ltd"],
        ],
    )


def test_preview_normalizes_amounts_dates_and_direction(client):
    suffix = unique_suffix()
    resp = analyze(client, "bank", f"tscheck-normprev-{suffix}.csv", _messy_csv(suffix))
    assert resp.status_code == 200, resp.text[:300]
    body = resp.json()
    preview_by_row = {row["source_row_number"]: row for row in body["preview"]}
    assert len(preview_by_row) == 2
    row1 = preview_by_row[2]["normalized"]
    assert row1["amount"] == 123450  # rupees -> integer paise
    assert row1["transaction_date"] == "2024-01-05"
    assert row1["direction"] == "credit"
    assert row1["external_id"] == f"tscheck-norm-{suffix}-1"
    assert row1["reference"] == f"tscheck-norm-ref-{suffix}-1"

    row2 = preview_by_row[3]["normalized"]
    assert row2["amount"] == 50075  # parenthesised amount normalized to a positive paise value
    assert row2["direction"] == "debit"
    assert row2["transaction_date"] == "2024-01-06"


def test_imported_transactions_expose_full_normalized_model(client):
    suffix = unique_suffix()
    resp = analyze(client, "bank", f"tscheck-normimport-{suffix}.csv", _messy_csv(suffix))
    assert resp.status_code == 200, resp.text[:300]
    batch_id = resp.json()["batch"]["id"]
    mapping = {
        "transaction_id": "Transaction ID", "reference": "Reference", "date": "Date", "amount": "Amount",
        "debit": None, "credit": None, "direction": "Type", "description": "Description",
        "currency": "Currency", "status": "Status", "counterparty": "Counterparty",
    }
    put_resp = apply_mapping(client, batch_id, mapping)
    assert put_resp.status_code == 200, put_resp.text[:300]

    import_resp = confirm_import(client, batch_id)
    assert import_resp.status_code == 200, import_resp.text[:300]

    tx_resp = get_transactions(client, batch_id)
    assert tx_resp.status_code == 200, tx_resp.text[:300]
    items = tx_resp.json()["items"]
    assert len(items) == 2
    by_external = {item["external_id"]: item for item in items}
    credit_item = by_external[f"tscheck-norm-{suffix}-1"]
    assert credit_item["amount"] == 123450
    assert credit_item["direction"] == "credit"
    assert credit_item["currency"] == "INR"
    assert credit_item["description"] == "Card settlement"
    assert credit_item["status"] == "captured"
    assert credit_item["counterparty"] == "Acme Co"
    assert credit_item["reference"] == f"tscheck-norm-ref-{suffix}-1"
    assert credit_item["transaction_date"] == "2024-01-05"

    debit_item = by_external[f"tscheck-norm-{suffix}-2"]
    assert debit_item["amount"] == 50075
    assert debit_item["direction"] == "debit"
    assert debit_item["status"] == "refunded"
