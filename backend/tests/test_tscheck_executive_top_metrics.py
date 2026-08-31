"""Top executive metrics: revenue, current balance, 30-day cash forecast, reconciliation exceptions.

Verifies GET /api/executive/dashboard returns the four backend-owned metrics with
current-month revenue comparison and non-empty evidence/details.
"""


def test_dashboard_has_four_complete_metrics(client):
    resp = client.get("/executive/dashboard")
    assert resp.status_code == 200, resp.text
    body = resp.json()

    assert "as_of_date" in body and body["as_of_date"]
    metrics = body["metrics"]
    assert len(metrics) == 4
    ids = {m["id"] for m in metrics}
    assert ids == {"revenue", "current_balance", "cash_forecast", "reconciliation_exceptions"}

    for metric in metrics:
        assert metric["label"]
        assert metric["value"] is not None
        assert metric["period_label"]
        assert metric["detail"]
        assert metric["explanation"]
        assert metric["calculation"]
        assert metric["source_metric"]
        assert metric["source_tool"]
        assert metric["drilldown_path"]
        assert isinstance(metric["evidence"], list) and len(metric["evidence"]) > 0

    revenue = next(m for m in metrics if m["id"] == "revenue")
    assert "month" in revenue["period_label"].lower()
    assert revenue["change_percent"] is not None
    assert revenue["trend"] in {"up", "down", "neutral"}


def test_reconciliation_metric_links_to_reconciliation_workflow(client):
    resp = client.get("/executive/dashboard")
    assert resp.status_code == 200
    body = resp.json()
    recon = next(m for m in body["metrics"] if m["id"] == "reconciliation_exceptions")
    assert recon["drilldown_path"] == "/reconciliation"

    cash_forecast = next(m for m in body["metrics"] if m["id"] == "cash_forecast")
    current_balance = next(m for m in body["metrics"] if m["id"] == "current_balance")
    assert cash_forecast["drilldown_path"] == "/forecast"
    assert current_balance["drilldown_path"] == "/forecast"

    revenue = next(m for m in body["metrics"] if m["id"] == "revenue")
    assert revenue["drilldown_path"] == "/cfo"
