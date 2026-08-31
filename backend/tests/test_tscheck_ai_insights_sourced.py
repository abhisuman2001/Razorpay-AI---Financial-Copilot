"""AI insights: most important AI CFO insights are actionable and sourced."""


def test_ai_insights_are_sourced_and_actionable(client):
    resp = client.get("/executive/dashboard")
    assert resp.status_code == 200, resp.text
    body = resp.json()

    insights = body["insights"]
    assert len(insights) == 5

    valid_severities = {"high", "medium", "low"}
    for insight in insights:
        assert insight["severity"] in valid_severities
        assert insight["title"]
        assert insight["summary"]  # explanation
        assert insight["metric_label"]
        assert insight["metric_value"]
        assert insight["source_tool"]
        assert insight["source_ref"]
        assert insight["action"]
        assert insight["classification"] in {"fact", "prediction"}

    # at least one high severity insight exists (needs attention framing)
    assert any(i["severity"] == "high" for i in insights)
