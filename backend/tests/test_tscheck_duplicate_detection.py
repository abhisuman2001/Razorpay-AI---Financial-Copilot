"""Criterion: Duplicate transactions are detected deterministically."""

from tests.helpers_imports import analyze, build_csv, confirm_import, get_transactions, unique_suffix


def _csv_with_repeated_id(suffix: str) -> bytes:
    txn_id = f"tscheck-dup-{suffix}-shared"
    return build_csv(
        ["Transaction ID", "Reference", "Date", "Amount", "Type", "Description"],
        [
            [txn_id, f"tscheck-dup-ref-{suffix}-1", "2024-03-01", "800.00", "credit", "first occurrence"],
            [txn_id, f"tscheck-dup-ref-{suffix}-2", "2024-03-01", "800.00", "credit", "repeated source id"],
        ],
    )


def test_repeated_source_id_marked_duplicate(client):
    suffix = unique_suffix()
    resp = analyze(client, "bank", f"tscheck-dupfile-{suffix}.csv", _csv_with_repeated_id(suffix))
    assert resp.status_code == 200, resp.text[:300]
    batch_id = resp.json()["batch"]["id"]
    # Auto-detected mapping already maps Transaction ID/Date/Amount for these headers.

    import_resp = confirm_import(client, batch_id)
    assert import_resp.status_code == 200, import_resp.text[:300]

    dup_resp = get_transactions(client, batch_id, match_status="DUPLICATE")
    assert dup_resp.status_code == 200, dup_resp.text[:300]
    dup_items = dup_resp.json()["items"]
    assert len(dup_items) == 1, f"expected exactly one duplicate row, got {dup_resp.text[:500]}"
    duplicate = dup_items[0]
    assert duplicate["match_status"] == "DUPLICATE"
    assert duplicate["match_rule"] == "SOURCE_FINGERPRINT"
    assert duplicate["confidence"] == 100.0
    assert duplicate["duplicate_of_id"] is not None

    all_resp = get_transactions(client, batch_id)
    all_items = all_resp.json()["items"]
    original_ids = {item["id"] for item in all_items if item["match_status"] != "DUPLICATE"}
    assert duplicate["duplicate_of_id"] in original_ids
