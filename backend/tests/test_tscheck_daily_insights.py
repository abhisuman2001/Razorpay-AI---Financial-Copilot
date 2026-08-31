"""Criterion: Daily insights cover requested financial signals."""

EXPECTED_CATEGORIES = {"Reconciliation", "Cash flow", "Revenue", "Payment failures", "Refunds"}


def test_daily_insights_covers_all_signal_categories(client):
    resp = client.get("/cfo/insights")
    assert resp.status_code == 200
    body = resp.json()
    assert body["insights"], "expected non-empty insights"
    categories = {i["category"] for i in body["insights"]}
    assert EXPECTED_CATEGORIES.issubset(categories), f"missing categories: {EXPECTED_CATEGORIES - categories}"
    for insight in body["insights"]:
        assert insight["classification"] in ("fact", "prediction")
        assert insight["source_tool"]
        assert insight["source_ref"]
        assert insight["severity"] in ("high", "medium", "low")
