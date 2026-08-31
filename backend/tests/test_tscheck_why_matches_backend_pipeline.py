"""Covers: Why calculations remain in the backend pipeline -- revenue equals
get_revenue's current-month value, refund rate equals get_refunds's rate, forecasted
balance equals /api/forecast/30, and the frontend Why panel contains no hard-coded
metric values or contributor math (values are rendered straight from the API response).
"""

import re
from pathlib import Path

import httpx

FRONTEND_SRC = Path(__file__).resolve().parents[2] / "frontend" / "src"


def test_why_revenue_matches_get_revenue_tool(client: httpx.Client):
    why = client.get("/why/revenue").json()
    tool = client.get("/cfo/tools/get_revenue").json()["data"]
    assert why["current_value"] == tool["current_month_revenue"]
    assert why["previous_value"] == tool["previous_month_revenue"]


def test_why_refund_rate_matches_get_refunds_tool(client: httpx.Client):
    why = client.get("/why/refund_rate").json()
    tool = client.get("/cfo/tools/get_refunds").json()["data"]
    assert why["current_value"] == tool["refund_rate_percent"]


def test_why_forecasted_balance_matches_forecast_endpoint(client: httpx.Client):
    why = client.get("/why/forecasted_balance").json()
    forecast = client.get("/forecast/30").json()
    assert why["current_value"] == forecast["forecasted_balance"]
    assert why["previous_value"] == forecast["current_cash_balance"]


def test_why_values_are_stable_across_repeated_calls(client: httpx.Client):
    """Deterministic pipeline: same seeded data in, same numbers out on every call."""
    first = client.get("/why/settlement_amount").json()
    second = client.get("/why/settlement_amount").json()
    assert first["current_value"] == second["current_value"]
    assert first["drivers"] == second["drivers"]


def test_why_frontend_panel_has_no_hardcoded_metric_values():
    """WhyMetricSheet.tsx must render values from the API response object, not literals."""
    sheet_path = FRONTEND_SRC / "components" / "WhyMetricSheet.tsx"
    content = sheet_path.read_text()
    # No bare 5+ digit numeric literals (which would indicate a hard-coded rupee/paise figure)
    bare_numbers = re.findall(r"(?<![\w.])\d{5,}(?![\w])", content)
    assert not bare_numbers, f"WhyMetricSheet.tsx contains suspicious numeric literals: {bare_numbers}"
    # Values must be sourced from the query response object, not computed contributor math.
    assert "data.current_value" in content
    assert "data.drivers" in content
    assert "data.explanation" in content
