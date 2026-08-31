"""Demo Mode lists all requested scenarios with descriptions/effects (API side)."""

EXPECTED_IDS = {
    "healthy_business",
    "revenue_decline",
    "payment_failure_spike",
    "cash_flow_risk",
    "settlement_discrepancy",
    "high_refund_rate",
}


def test_demo_scenarios_list_complete(client):
    resp = client.get("/demo/scenarios")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "active_scenario_id" in body
    scenarios = body["scenarios"]
    ids = {s["id"] for s in scenarios}
    assert ids == EXPECTED_IDS, f"scenario ids mismatch: {ids}"
    for s in scenarios:
        assert s["name"], s
        assert s["description"], s
        assert s["signal"], s
        assert isinstance(s["expected_effects"], list) and len(s["expected_effects"]) > 0, s
        assert isinstance(s["active"], bool)
    # exactly one active
    active_flags = [s["active"] for s in scenarios]
    assert active_flags.count(True) == 1
