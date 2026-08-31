"""Covers: every major metric has a backend Why explanation; drivers are deterministic and
ranked; comparison periods/methodology are explicit; facts vs predictions are distinguished.
"""

import httpx

ALL_METRICS = [
    "revenue", "cash_balance", "settlement_amount", "refund_rate",
    "payment_success_rate", "forecasted_balance", "reconciliation_exceptions",
]

FACT_METRICS = [
    "revenue", "cash_balance", "settlement_amount", "refund_rate",
    "payment_success_rate", "reconciliation_exceptions",
]


def test_every_major_metric_has_complete_why_contract(client: httpx.Client):
    for metric_id in ALL_METRICS:
        response = client.get(f"/why/{metric_id}")
        assert response.status_code == 200, f"{metric_id} -> {response.status_code} {response.text}"
        body = response.json()
        assert body["metric_id"] == metric_id
        for field in [
            "metric_label", "classification", "as_of_date", "current_period",
            "comparison_period", "current_value", "previous_value", "unit",
            "change_amount", "change_summary", "direction", "drivers",
            "explanation", "explanation_mode", "methodology", "source_refs",
            "drilldown_path",
        ]:
            assert field in body, f"{metric_id} missing field {field}"
        assert body["methodology"], f"{metric_id} methodology is empty"
        assert body["source_refs"], f"{metric_id} source_refs is empty"
        assert body["current_period"], f"{metric_id} current_period is empty"
        assert body["comparison_period"], f"{metric_id} comparison_period is empty"


def test_unknown_metric_returns_404(client: httpx.Client):
    response = client.get("/why/not_a_real_metric")
    assert response.status_code == 404


def test_drivers_are_ranked_and_within_one_to_four(client: httpx.Client):
    for metric_id in ALL_METRICS:
        body = client.get(f"/why/{metric_id}").json()
        drivers = body["drivers"]
        assert 1 <= len(drivers) <= 4, f"{metric_id} has {len(drivers)} drivers"
        scores = [driver["impact_score"] for driver in drivers]
        assert scores == sorted(scores, reverse=True), f"{metric_id} drivers not ranked by impact_score"
        for driver in drivers:
            for field in [
                "id", "label", "description", "current_value", "previous_value", "unit",
                "change_amount", "change_percent", "change_summary", "direction", "effect",
                "classification", "source_metrics",
            ]:
                assert field in driver, f"{metric_id} driver {driver.get('id')} missing {field}"
            assert driver["source_metrics"], f"{metric_id} driver {driver['id']} has empty source_metrics"
            assert driver["direction"] in {"increased", "decreased", "unchanged"}
            assert driver["effect"] in {"positive", "negative", "neutral"}


def test_seeded_dataset_returns_exactly_four_drivers(client: httpx.Client):
    for metric_id in ALL_METRICS:
        body = client.get(f"/why/{metric_id}").json()
        assert len(body["drivers"]) == 4, f"{metric_id} expected 4 drivers under seeded Healthy Business data"


def test_fact_metrics_use_calendar_month_comparison(client: httpx.Client):
    for metric_id in FACT_METRICS:
        body = client.get(f"/why/{metric_id}").json()
        assert body["classification"] == "fact", metric_id
        # cash_balance is point-in-time so uses month-end phrasing; others use month ranges.
        if metric_id == "cash_balance":
            assert "Balance as of" in body["current_period"]
            assert "Balance as of" in body["comparison_period"]
        else:
            assert " to " in body["current_period"]
            assert " to " in body["comparison_period"]


def test_forecasted_balance_is_classified_prediction_and_compares_to_current_balance(client: httpx.Client):
    body = client.get("/why/forecasted_balance").json()
    assert body["classification"] == "prediction"
    assert "30 days" in body["current_period"]
    assert "Recorded balance" in body["comparison_period"]
    for driver in body["drivers"]:
        assert driver["classification"] == "prediction"


def test_fact_metric_drivers_are_classified_fact(client: httpx.Client):
    body = client.get("/why/revenue").json()
    assert body["classification"] == "fact"
    for driver in body["drivers"]:
        assert driver["classification"] == "fact"
