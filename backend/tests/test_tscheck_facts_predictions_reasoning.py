"""Criterion: Answers distinguish facts from predictions and explain reasoning."""


def test_cash_forecast_question_has_facts_predictions_reasoning(client):
    resp = client.post("/cfo/chat", json={"question": "Will I have enough cash next month based on forecast?"})
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body["facts"], list)
    assert isinstance(body["predictions"], list) and len(body["predictions"]) > 0, "expected a prediction for a forecast question"
    assert isinstance(body["reasoning"], list) and len(body["reasoning"]) > 0
    assert isinstance(body["recommendations"], list)
    # every prediction string should be distinguishable/labeled
    for p in body["predictions"]:
        assert isinstance(p, str) and p


def test_fact_only_question_still_has_reasoning(client):
    resp = client.post("/cfo/chat", json={"question": "What is our current failed payments count?"})
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["facts"]) > 0
    assert len(body["reasoning"]) > 0
