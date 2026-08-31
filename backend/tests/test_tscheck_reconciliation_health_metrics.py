"""Reconciliation section: dashboard totals stay consistent with /reconciliation/summary."""


def test_reconciliation_health_metrics_present_and_consistent(client):
    dash_resp = client.get("/executive/dashboard")
    assert dash_resp.status_code == 200, dash_resp.text
    recon = dash_resp.json()["reconciliation"]

    required_fields = [
        "transactions_analyzed",
        "matched",
        "mismatched",
        "pending",
        "total_discrepancy",
        "reconciliation_rate",
    ]
    for field in required_fields:
        assert field in recon, f"missing {field}"
        assert recon[field] is not None

    assert 0 <= recon["reconciliation_rate"] <= 100
    assert recon["transactions_analyzed"] >= recon["matched"]

    summary_resp = client.get("/reconciliation/summary")
    assert summary_resp.status_code == 200, summary_resp.text
    summary = summary_resp.json()

    # Cross-check that dashboard's reconciliation numbers are backed by the same
    # underlying reconciliation status source as the dedicated reconciliation endpoint.
    assert summary["total_transactions"] == recon["transactions_analyzed"]
    assert summary["matched_transactions"] == recon["matched"]
    assert summary["mismatched_transactions"] == recon["mismatched"]
    assert summary["pending_transactions"] == recon["pending"]
    assert summary["total_discrepancy"] == recon["total_discrepancy"]
    assert summary["reconciliation_rate"] == recon["reconciliation_rate"]
