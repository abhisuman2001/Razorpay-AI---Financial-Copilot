"""Cash-flow section: exactly 60 historical daily balance points and 30 forecast points."""


def test_cashflow_actual_and_forecast_point_counts(client):
    resp = client.get("/executive/dashboard")
    assert resp.status_code == 200, resp.text
    body = resp.json()

    actual = body["cashflow_actual"]
    forecast = body["cashflow_forecast"]
    assert len(actual) == 60, f"expected 60 actual points, got {len(actual)}"
    assert len(forecast) == 30, f"expected 30 forecast points, got {len(forecast)}"

    for point in actual:
        assert "date" in point
        assert "cumulative_cash_balance" in point
        assert point["cumulative_cash_balance"] is not None

    for point in forecast:
        assert "date" in point
        assert "predicted_balance" in point
        assert "balance_lower" in point
        assert "balance_upper" in point
        assert point["balance_lower"] <= point["predicted_balance"] <= point["balance_upper"]

    # forecast should chronologically continue after the actual history
    assert forecast[0]["date"] > actual[-1]["date"]
