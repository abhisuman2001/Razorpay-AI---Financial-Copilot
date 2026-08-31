"""Criterion: AI CFO chat selects only relevant backend tools for the asked question."""


def _ask(client, question: str):
    resp = client.post("/cfo/chat", json={"question": question})
    assert resp.status_code == 200, f"{question} -> {resp.status_code}: {resp.text[:300]}"
    return resp.json()


def test_cash_question_selects_cash_related_tools(client):
    body = _ask(client, "Will I have enough cash next month?")
    assert body["tools_used"], "no tools used"
    assert any(t in body["tools_used"] for t in ("get_cash_balance", "get_cashflow_forecast"))
    assert body["answer"]


def test_revenue_question_selects_revenue_tool(client):
    body = _ask(client, "Why did revenue fall this month compared to last month?")
    assert "get_revenue" in body["tools_used"]


def test_reconciliation_question_selects_reconciliation_or_settlement_tool(client):
    body = _ask(client, "Show me my biggest reconciliation and settlement problems.")
    assert any(t in body["tools_used"] for t in ("get_reconciliation_exceptions", "get_settlement_summary"))


def test_risk_question_selects_failed_payments_or_refunds(client):
    body = _ask(client, "What financial risks should I be concerned about today, especially failed payments?")
    assert any(t in body["tools_used"] for t in ("get_failed_payments", "get_refunds", "get_reconciliation_exceptions", "get_cashflow_forecast"))


def test_customer_question_selects_customer_tool(client):
    body = _ask(client, "Which customers are most valuable to us?")
    assert any(t in body["tools_used"] for t in ("get_top_customers", "get_customer_statistics"))
