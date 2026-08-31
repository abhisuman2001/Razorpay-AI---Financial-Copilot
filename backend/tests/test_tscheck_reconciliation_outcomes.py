"""Criterion: Deterministic reconciliation identifies all requested outcomes."""

from tests.helpers_imports import analyze, build_csv, confirm_import, get_transactions, unique_suffix


def _bank_csv(suffix: str) -> bytes:
    return build_csv(
        ["Transaction ID", "Reference", "Date", "Amount", "Type", "Description"],
        [
            [f"tscheck-recon-bank-{suffix}-1", f"tscheck-recon-ref-{suffix}-match", "2024-04-10", "1000.00", "credit", "exact match"],
            [f"tscheck-recon-bank-{suffix}-2", f"tscheck-recon-ref-{suffix}-amt", "2024-04-11", "500.00", "credit", "amount differs downstream"],
            [f"tscheck-recon-bank-{suffix}-3", f"tscheck-recon-ref-{suffix}-date", "2024-04-01", "700.00", "credit", "date differs downstream"],
            [f"tscheck-recon-bank-{suffix}-4", f"tscheck-recon-ref-{suffix}-onlybank", "2024-04-15", "999.00", "credit", "no counterpart"],
        ],
    )


def _gateway_csv(suffix: str) -> bytes:
    return build_csv(
        ["Transaction ID", "Reference", "Date", "Amount", "Type", "Description"],
        [
            [f"tscheck-recon-gw-{suffix}-1", f"tscheck-recon-ref-{suffix}-match", "2024-04-10", "1000.00", "credit", "exact match"],
            [f"tscheck-recon-gw-{suffix}-2", f"tscheck-recon-ref-{suffix}-amt", "2024-04-11", "550.00", "credit", "amount differs upstream"],
            [f"tscheck-recon-gw-{suffix}-3", f"tscheck-recon-ref-{suffix}-date", "2024-04-10", "700.00", "credit", "date differs upstream (9 days)"],
        ],
    )


def _upload_and_import(client, source_type, filename, content):
    resp = analyze(client, source_type, filename, content)
    assert resp.status_code == 200, resp.text[:300]
    batch_id = resp.json()["batch"]["id"]
    import_resp = confirm_import(client, batch_id)
    assert import_resp.status_code == 200, import_resp.text[:300]
    return batch_id


def test_reconciliation_covers_matched_unmatched_amount_and_date_mismatch(client):
    suffix = unique_suffix()
    bank_batch_id = _upload_and_import(client, "bank", f"tscheck-recon-bank-{suffix}.csv", _bank_csv(suffix))
    gateway_batch_id = _upload_and_import(client, "payment_gateway", f"tscheck-recon-gw-{suffix}.csv", _gateway_csv(suffix))

    bank_items = get_transactions(client, bank_batch_id).json()["items"]
    by_bank_ref = {item["reference"]: item for item in bank_items}

    matched = by_bank_ref[f"tscheck-recon-ref-{suffix}-match"]
    assert matched["match_status"] == "MATCHED", matched
    assert matched["match_rule"] == "EXACT_REFERENCE"
    assert matched["confidence"] == 100.0
    assert matched["reason"]

    amount_mismatch = by_bank_ref[f"tscheck-recon-ref-{suffix}-amt"]
    assert amount_mismatch["match_status"] == "AMOUNT_MISMATCH", amount_mismatch
    assert amount_mismatch["match_rule"] == "EXACT_REFERENCE_AMOUNT_DIFFERENCE"
    assert amount_mismatch["amount_difference"] == 5000  # 550.00 - 500.00 in paise
    assert amount_mismatch["reason"]

    date_mismatch = by_bank_ref[f"tscheck-recon-ref-{suffix}-date"]
    assert date_mismatch["match_status"] == "DATE_MISMATCH", date_mismatch
    assert date_mismatch["match_rule"] == "EXACT_REFERENCE_DATE_DIFFERENCE"
    assert date_mismatch["date_difference_days"] == 9
    assert date_mismatch["reason"]

    unmatched = by_bank_ref[f"tscheck-recon-ref-{suffix}-onlybank"]
    assert unmatched["match_status"] == "UNMATCHED", unmatched
    assert unmatched["match_rule"] == "NO_DETERMINISTIC_MATCH"
    assert unmatched["confidence"] == 0.0
    assert unmatched["reason"]

    # The gateway side of the matched/mismatched pairs reflects the same deterministic outcome.
    gateway_items = get_transactions(client, gateway_batch_id).json()["items"]
    by_gateway_ref = {item["reference"]: item for item in gateway_items}
    assert by_gateway_ref[f"tscheck-recon-ref-{suffix}-match"]["match_status"] == "MATCHED"
    assert by_gateway_ref[f"tscheck-recon-ref-{suffix}-amt"]["match_status"] == "AMOUNT_MISMATCH"
    assert by_gateway_ref[f"tscheck-recon-ref-{suffix}-date"]["match_status"] == "DATE_MISMATCH"
