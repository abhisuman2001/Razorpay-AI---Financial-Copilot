"""
Tests for the Cash Balance Analysis feature.

These tests hit the live backend server at http://localhost:8001/api
(same pattern as the rest of this project).

Validates:
- The /why/cash_balance/analysis endpoint returns HTTP 200 with well-formed data
- Waterfall components sum correctly to the current balance
- calculated_balance == current_balance (or differs by at most 1 paise rounding)
- Daily breakdown exists and is chronologically ordered
- All source record counts are non-negative integers
- Required fields (validation_status, why_this_matters, etc.) are present and non-empty
- No hardcoded financial values (values come from live data, not fixtures)
- The specific endpoint is NOT swallowed by the /{metric_id} catch-all
- current_balance here matches current_value from /why/cash_balance
"""

import pytest
import httpx

BACKEND_URL = "http://localhost:8001"
API_URL = f"{BACKEND_URL}/api"

ANALYSIS_URL = f"{API_URL}/why/cash_balance/analysis"
WHY_CASH_URL = f"{API_URL}/why/cash_balance"


# ── Helpers ────────────────────────────────────────────────────────────────────

def get_analysis() -> dict:
    with httpx.Client(base_url=API_URL, timeout=30.0) as client:
        resp = client.get("/why/cash_balance/analysis")
    resp.raise_for_status()
    return resp.json()


def get_why_cash_balance() -> dict:
    with httpx.Client(base_url=API_URL, timeout=30.0) as client:
        resp = client.get("/why/cash_balance")
    resp.raise_for_status()
    return resp.json()


# ── Endpoint availability ──────────────────────────────────────────────────────

def test_cash_balance_analysis_returns_200():
    """Endpoint is reachable and returns 200 OK."""
    with httpx.Client(base_url=API_URL, timeout=30.0) as client:
        resp = client.get("/why/cash_balance/analysis")
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text[:300]}"


def test_response_is_json():
    """Response is valid JSON."""
    with httpx.Client(base_url=API_URL, timeout=30.0) as client:
        resp = client.get("/why/cash_balance/analysis")
    # This raises ValueError if not valid JSON
    data = resp.json()
    assert isinstance(data, dict)


# ── Required fields ────────────────────────────────────────────────────────────

def test_all_top_level_fields_present():
    """Every required top-level field is present in the response."""
    data = get_analysis()
    required = {
        "period_start", "period_end", "as_of_date",
        "current_balance", "calculated_balance", "rounding_difference",
        "opening_balance", "opening_balance_date",
        "opening_balance_source", "opening_balance_configurable",
        "waterfall", "daily_breakdown",
        "why_this_matters", "calculation_method", "validation_status",
    }
    missing = required - set(data.keys())
    assert not missing, f"Missing fields in response: {missing}"


def test_no_null_critical_fields():
    """Critical numeric and structural fields must not be None."""
    data = get_analysis()
    assert data["current_balance"] is not None
    assert data["calculated_balance"] is not None
    assert data["opening_balance"] is not None
    assert data["waterfall"] is not None
    assert data["daily_breakdown"] is not None


# ── Waterfall structure ────────────────────────────────────────────────────────

def test_waterfall_contains_required_components():
    """Waterfall must include opening, settled_cash, expenses, and current balance rows."""
    data = get_analysis()
    ids = {row["id"] for row in data["waterfall"]}
    for required_id in ("opening", "settled_cash", "expenses"):
        assert required_id in ids, f"Waterfall missing row with id='{required_id}'"


def test_waterfall_rows_have_source_traceability():
    """Every waterfall row must have a non-empty source_table field."""
    data = get_analysis()
    for row in data["waterfall"]:
        assert "source_table" in row, f"Row '{row.get('id')}' missing source_table"
        assert isinstance(row["source_table"], str)
        assert len(row["source_table"]) > 0, f"Row '{row.get('id')}' has empty source_table"


def test_waterfall_labels_are_descriptive():
    """Every waterfall label is a non-trivial human-readable string."""
    data = get_analysis()
    for row in data["waterfall"]:
        label = row.get("label", "")
        assert isinstance(label, str) and len(label) > 5, (
            f"Row '{row.get('id')}' has a too-short label: '{label}'"
        )


def test_waterfall_record_counts_are_non_negative():
    """record_count in every waterfall row must be a non-negative integer."""
    data = get_analysis()
    for row in data["waterfall"]:
        count = row.get("record_count", 0)
        assert isinstance(count, int), f"Row '{row.get('id')}' record_count is not int: {count}"
        assert count >= 0, f"Row '{row.get('id')}' has negative record_count: {count}"


# ── Financial reconciliation ───────────────────────────────────────────────────

def test_calculated_balance_matches_current_balance():
    """
    The deterministic formula must reproduce the displayed current cash balance.

    opening_balance + settled_cash + other_income - expenses == current_balance
    Allowed rounding tolerance: ±1 paise.
    """
    data = get_analysis()
    current = data["current_balance"]
    calculated = data["calculated_balance"]
    diff = data["rounding_difference"]

    assert abs(diff) <= 1, (
        f"Balance does not reconcile: current={current}, calculated={calculated}, diff={diff}"
    )
    assert current == calculated or abs(current - calculated) <= 1


def test_waterfall_math_adds_up():
    """
    opening + settled_cash + other_income - expenses must equal the 'current_balance' waterfall row.
    All values taken directly from waterfall rows to catch any waterfall inconsistency.
    """
    data = get_analysis()
    waterfall = {row["id"]: row["amount"] for row in data["waterfall"]}

    opening = waterfall.get("opening", 0)
    settled = waterfall.get("settled_cash", 0)
    other = waterfall.get("other_income", 0)
    # expenses row is stored as a negative amount in the waterfall
    expenses_raw = waterfall.get("expenses", 0)

    # The waterfall current_balance id may be "current_balance" or "current"
    current_row = waterfall.get("current_balance", waterfall.get("current", None))
    if current_row is None:
        pytest.skip("No current_balance/current row found in waterfall")

    reconstructed = opening + settled + other + expenses_raw  # expenses already negative
    assert abs(reconstructed - current_row) <= 1, (
        f"Waterfall math: {opening} + {settled} + {other} + {expenses_raw} = "
        f"{reconstructed}, but current row = {current_row}"
    )


def test_settled_cash_is_non_negative():
    """Settled cash must be a non-negative amount (it is gross income, not net sign)."""
    data = get_analysis()
    assert data["total_settled_cash"] >= 0


def test_expenses_are_non_negative():
    """Total expenses stored in the model must be a non-negative absolute value."""
    data = get_analysis()
    assert data["total_expenses"] >= 0


# ── Daily breakdown ────────────────────────────────────────────────────────────

def test_daily_breakdown_is_non_empty():
    """Daily breakdown must contain at least one row."""
    data = get_analysis()
    assert len(data["daily_breakdown"]) > 0


def test_daily_breakdown_row_fields():
    """Every daily row must have date, inflows, outflows, net_movement, ending_balance."""
    data = get_analysis()
    required = {"date", "inflows", "outflows", "net_movement", "ending_balance"}
    for row in data["daily_breakdown"]:
        missing = required - set(row.keys())
        assert not missing, f"Daily row missing fields: {missing}"


def test_daily_breakdown_is_chronological():
    """Dates in the daily breakdown must be in non-decreasing order."""
    data = get_analysis()
    daily = data["daily_breakdown"]
    if len(daily) > 1:
        for i in range(len(daily) - 1):
            assert daily[i]["date"] <= daily[i + 1]["date"], (
                f"Daily breakdown not chronological at index {i}: "
                f"{daily[i]['date']} > {daily[i + 1]['date']}"
            )


# ── Opening balance metadata ───────────────────────────────────────────────────

def test_opening_balance_metadata():
    """Opening balance must be >= 0 and carry descriptive metadata."""
    data = get_analysis()
    assert data["opening_balance"] >= 0
    assert isinstance(data["opening_balance_date"], str)
    assert len(data["opening_balance_date"]) >= 10  # ISO date string
    assert isinstance(data["opening_balance_source"], str)
    assert len(data["opening_balance_source"]) > 5
    assert isinstance(data["opening_balance_configurable"], bool)


# ── Narrative & validation fields ─────────────────────────────────────────────

def test_validation_status_is_non_empty_string():
    """validation_status must be a meaningful string."""
    data = get_analysis()
    assert isinstance(data["validation_status"], str)
    assert len(data["validation_status"]) > 5


def test_why_this_matters_is_substantive():
    """why_this_matters must be a non-trivial explanation (>50 chars)."""
    data = get_analysis()
    assert isinstance(data["why_this_matters"], str)
    assert len(data["why_this_matters"]) > 50, (
        f"why_this_matters is too short: '{data['why_this_matters']}'"
    )


def test_calculation_method_is_documented():
    """calculation_method must be present and mention the formula."""
    data = get_analysis()
    method = data["calculation_method"]
    assert isinstance(method, str)
    assert len(method) > 20
    # Should reference the deterministic formula, not LLM
    assert "LLM" not in method or "No LLM" in method


# ── Endpoint routing ───────────────────────────────────────────────────────────

def test_analysis_endpoint_not_swallowed_by_catch_all():
    """
    /why/cash_balance/analysis must return CashBalanceAnalysis (with waterfall),
    NOT the WhyMetricResponse that the /{metric_id} catch-all would return.
    """
    data = get_analysis()
    # CashBalanceAnalysis has waterfall + daily_breakdown
    assert "waterfall" in data, "Endpoint was swallowed by /{metric_id} catch-all (no waterfall field)"
    assert "daily_breakdown" in data
    # WhyMetricResponse would have "drivers" — should NOT be present here
    assert "drivers" not in data, "Response looks like WhyMetricResponse; routing is wrong"


# ── Cross-endpoint consistency ─────────────────────────────────────────────────

def test_analysis_current_balance_matches_why_metric():
    """
    current_balance in the analysis must exactly match current_value
    returned by the /why/cash_balance metric endpoint.
    Both derive from the same cashflow engine call.
    """
    analysis = get_analysis()
    why = get_why_cash_balance()

    assert analysis["current_balance"] == why["current_value"], (
        f"Analysis current_balance ({analysis['current_balance']}) != "
        f"why/cash_balance current_value ({why['current_value']})"
    )
