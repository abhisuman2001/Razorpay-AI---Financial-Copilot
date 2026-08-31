"""Criterion: All ten requested financial tools are available and deterministic."""

TOOL_NAMES = [
    "get_revenue",
    "get_expenses",
    "get_cash_balance",
    "get_failed_payments",
    "get_refunds",
    "get_settlement_summary",
    "get_reconciliation_exceptions",
    "get_cashflow_forecast",
    "get_top_customers",
    "get_customer_statistics",
]


def test_all_ten_tools_return_structured_json(client):
    for tool_name in TOOL_NAMES:
        resp = client.get(f"/cfo/tools/{tool_name}")
        assert resp.status_code == 200, f"{tool_name} -> {resp.status_code}: {resp.text[:300]}"
        body = resp.json()
        assert body["tool_name"] == tool_name
        assert body["classification"] in ("fact", "prediction")
        assert isinstance(body["period_label"], str) and body["period_label"]
        assert isinstance(body["data"], dict) and body["data"], f"{tool_name} data empty"
        assert isinstance(body["source_refs"], list) and body["source_refs"]


def test_tool_determinism_two_calls_match(client):
    """Same tool called twice in quick succession should return identical facts (deterministic, not LLM-random)."""
    resp1 = client.get("/cfo/tools/get_revenue")
    resp2 = client.get("/cfo/tools/get_revenue")
    assert resp1.status_code == 200 and resp2.status_code == 200
    body1, body2 = resp1.json(), resp2.json()
    assert body1["data"]["current_month_revenue"] == body2["data"]["current_month_revenue"]
    assert body1["data"]["payment_method_mix"] == body2["data"]["payment_method_mix"]


def test_unknown_tool_returns_404(client):
    resp = client.get("/cfo/tools/get_nonexistent_tool")
    assert resp.status_code == 404
