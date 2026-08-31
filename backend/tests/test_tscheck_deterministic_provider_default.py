"""Criterion: Local Ollama is optional and zero-cost default works without it (AI_CFO_PROVIDER=deterministic)."""

import os


def test_env_configured_for_deterministic_provider():
    assert os.environ.get("AI_CFO_PROVIDER", "deterministic") == "deterministic"


def test_chat_succeeds_in_deterministic_mode_without_ollama(client):
    resp = client.post("/cfo/chat", json={"question": "What is our current cash position?"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["mode"] in ("deterministic", "deterministic_fallback")
    assert "ollama" in body["provider_message"].lower() or "deterministic" in body["provider_message"].lower()
    assert "disabled" in body["provider_message"].lower() or "deterministic" in body["provider_message"].lower()


def test_insights_mode_is_deterministic(client):
    resp = client.get("/cfo/insights")
    assert resp.status_code == 200
    body = resp.json()
    assert body["mode"] in ("deterministic", "deterministic_fallback")
    assert "deterministic" in body["disclaimer"].lower()
