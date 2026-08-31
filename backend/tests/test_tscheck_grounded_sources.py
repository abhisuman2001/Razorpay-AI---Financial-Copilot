"""Criterion: Answers are grounded and cite financial data (source references traceable to tool results)."""


def test_chat_returns_source_refs_with_tool_classification_period(client):
    resp = client.post("/cfo/chat", json={"question": "What is our current cash balance?"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["sources"], "expected non-empty sources"
    for source in body["sources"]:
        assert source["tool_name"] in body["tools_used"]
        assert source["classification"] in ("fact", "prediction")
        assert isinstance(source["period"], str) and source["period"]
        assert isinstance(source["label"], str) and source["label"]


def test_source_tool_names_match_underlying_tool_endpoint(client):
    resp = client.post("/cfo/chat", json={"question": "What is our revenue this month?"})
    assert resp.status_code == 200
    body = resp.json()
    assert "get_revenue" in body["tools_used"]
    tool_resp = client.get("/cfo/tools/get_revenue")
    assert tool_resp.status_code == 200
    tool_body = tool_resp.json()
    # grounded: the chat mentions the revenue figure that is present in the tool's raw data
    revenue_rupees = tool_body["data"]["current_month_revenue"] / 100
    assert str(int(revenue_rupees)) in body["answer"].replace(",", "") or any(
        str(int(revenue_rupees)) in f.replace(",", "") for f in body["facts"]
    )
