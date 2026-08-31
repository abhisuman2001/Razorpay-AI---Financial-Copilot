"""Criterion: AI CFO is read-only and handles insufficient data safely."""


def test_chat_response_reports_read_only_true(client):
    resp = client.post("/cfo/chat", json={"question": "How much revenue did we make this month?"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["read_only"] is True
    assert "insufficient_data" in body
    assert isinstance(body["insufficient_data"], bool)


def test_chat_rejects_too_short_question(client):
    """Response model validation guards against malformed/empty input; no mutation endpoints exist."""
    resp = client.post("/cfo/chat", json={"question": "ok"})
    assert resp.status_code == 422


def test_no_write_verbs_exist_on_cfo_router(client):
    # PUT/DELETE/PATCH should not be accepted on cfo endpoints (read-only surface)
    resp = client.delete("/cfo/tools/get_revenue")
    assert resp.status_code in (404, 405)
    resp2 = client.put("/cfo/chat", json={"question": "test"})
    assert resp2.status_code in (404, 405)
