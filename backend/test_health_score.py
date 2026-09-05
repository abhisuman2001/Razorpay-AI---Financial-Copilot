"""
Tests for financial health score, alerts, and data consistency.

Hits the live backend at http://localhost:8001/api (same pattern as the rest of this project).

Covers:
- Health Score calculation and component scores
- Alert severity rules and ordering
- Alert navigation targets (cta_path validity)
- Consistency between Overview and Reconciliation metrics
- Strongest positive/negative contributor identification
"""

import httpx
import pytest

API_URL = "http://localhost:8001/api"


# ── Shared helpers ─────────────────────────────────────────────────────────────

def get_health_score() -> dict:
    with httpx.Client(base_url=API_URL, timeout=30.0) as c:
        resp = c.get("/executive/dashboard")
    resp.raise_for_status()
    return resp.json()["health_score"]


def get_alerts() -> list:
    with httpx.Client(base_url=API_URL, timeout=30.0) as c:
        resp = c.get("/executive/dashboard")
    resp.raise_for_status()
    return resp.json()["alerts"]


def get_dashboard() -> dict:
    with httpx.Client(base_url=API_URL, timeout=30.0) as c:
        resp = c.get("/executive/dashboard")
    resp.raise_for_status()
    return resp.json()


def get_reconciliation_data() -> dict:
    with httpx.Client(base_url=API_URL, timeout=30.0) as c:
        resp = c.get("/reconciliation/summary")
    resp.raise_for_status()
    return resp.json()

def test_health_score_returns_valid_overall():
    """Overall score is a number in [0, 100] with a valid status label."""
    score = get_health_score()

    assert isinstance(score["overall_score"], (float, int))
    assert 0 <= score["overall_score"] <= 100
    assert score["overall_status"] in ("excellent", "good", "fair", "poor")


def test_health_score_has_six_components():
    """Exactly 6 weighted components are returned."""
    score = get_health_score()
    assert len(score["components"]) == 6


def test_health_score_component_fields():
    """Each component has required fields with values in expected ranges."""
    score = get_health_score()
    for component in score["components"]:
        assert "name" in component, "component missing 'name'"
        assert "score" in component, "component missing 'score'"
        assert "weight" in component, "component missing 'weight'"
        assert "contribution" in component, "component missing 'contribution'"
        assert "explanation" in component, "component missing 'explanation'"
        assert "status" in component, "component missing 'status'"
        assert 0 <= component["score"] <= 100, f"{component['name']} score out of range"
        assert 0 < component["weight"] <= 1, f"{component['name']} weight out of range"
        assert component["status"] in ("excellent", "good", "fair", "poor")


def test_health_score_weights_sum_to_one():
    """Component weights must sum to 1.0 (within floating-point tolerance)."""
    score = get_health_score()
    total_weight = sum(c["weight"] for c in score["components"])
    assert abs(total_weight - 1.0) < 0.01, f"Weights sum to {total_weight}, expected 1.0"


def test_health_score_contribution_equals_score_times_weight():
    """Contribution of each component must equal score × weight (within rounding)."""
    score = get_health_score()
    for c in score["components"]:
        expected_contribution = round(c["score"] * c["weight"], 2)
        assert abs(c["contribution"] - expected_contribution) < 0.1, (
            f"{c['name']}: contribution {c['contribution']} ≠ score {c['score']} × weight {c['weight']}"
        )


def test_health_score_overall_is_weighted_sum():
    """Overall score equals the sum of all component contributions."""
    score = get_health_score()
    computed = sum(c["score"] * c["weight"] for c in score["components"])
    assert abs(score["overall_score"] - round(computed, 1)) < 0.2, (
        f"overall_score {score['overall_score']} ≠ weighted sum {round(computed, 1)}"
    )


def test_health_score_strongest_positive_and_negative():
    """strongest_positive has the highest contribution; strongest_negative has the lowest score."""
    score = get_health_score()

    components = score["components"]
    expected_positive = max(components, key=lambda c: c["contribution"])["name"]
    expected_negative = min(components, key=lambda c: c["score"])["name"]

    assert score["strongest_positive"] == expected_positive, (
        f"strongest_positive is '{score['strongest_positive']}', expected '{expected_positive}'"
    )
    assert score["strongest_negative"] == expected_negative, (
        f"strongest_negative is '{score['strongest_negative']}', expected '{expected_negative}'"
    )


def test_health_score_has_how_calculated():
    """how_calculated field is a non-empty string describing the formula."""
    score = get_health_score()
    assert isinstance(score["how_calculated"], str)
    assert len(score["how_calculated"]) > 50, "how_calculated is too short to be meaningful"
    # Must not contain LLM-generated content markers
    assert "LLM" not in score["how_calculated"] or "No LLM" in score["how_calculated"]


# ─── Alert tests ──────────────────────────────────────────────────────────────

VALID_SEVERITIES = {"critical", "high", "medium", "low"}
VALID_CTA_PATHS = {"/", "/reconciliation", "/forecast", "/cfo", "/connect"}


def test_alerts_returns_list():
    """detect_alerts always returns a list."""
    alerts = get_alerts()
    assert isinstance(alerts, list)


def test_alerts_have_required_fields():
    """Every alert must carry all required fields."""
    alerts = get_alerts()
    required_fields = {
        "id", "severity", "category", "title",
        "metric_label", "metric_value",
        "explanation", "recommended_action",
        "what_happened", "why_it_matters", "financial_impact",
        "cta_label", "cta_path",
        "detected_at", "source",
    }
    for alert in alerts:
        missing = required_fields - set(alert.keys())
        assert not missing, f"Alert '{alert.get('id', '?')}' missing fields: {missing}"


def test_alerts_have_valid_severity():
    """Every alert severity must be one of the four valid values."""
    alerts = get_alerts()
    for alert in alerts:
        assert alert["severity"] in VALID_SEVERITIES, (
            f"Alert '{alert['id']}' has invalid severity '{alert['severity']}'"
        )


def test_alerts_have_valid_cta_path():
    """Every cta_path must be a known frontend route."""
    alerts = get_alerts()
    for alert in alerts:
        assert alert["cta_path"] in VALID_CTA_PATHS, (
            f"Alert '{alert['id']}' has unknown cta_path '{alert['cta_path']}'"
        )


def test_alerts_have_non_empty_actionable_fields():
    """what_happened, why_it_matters, financial_impact, cta_label must be non-empty strings."""
    alerts = get_alerts()
    for alert in alerts:
        for field in ("what_happened", "why_it_matters", "financial_impact", "cta_label"):
            assert isinstance(alert[field], str) and len(alert[field]) > 5, (
                f"Alert '{alert['id']}' has empty or too-short '{field}'"
            )


def test_alerts_sorted_by_severity_then_impact():
    """Alerts are sorted critical → high → medium → low."""
    alerts = get_alerts()
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    for i in range(len(alerts) - 1):
        current_rank = severity_order[alerts[i]["severity"]]
        next_rank = severity_order[alerts[i + 1]["severity"]]
        assert current_rank <= next_rank, (
            f"Alert ordering violated: '{alerts[i]['severity']}' before '{alerts[i + 1]['severity']}'"
        )


def test_reconciliation_alert_navigates_to_reconciliation():
    """Reconciliation-category alerts must point to /reconciliation."""
    alerts = get_alerts()
    for alert in alerts:
        if alert["category"] == "Reconciliation":
            assert alert["cta_path"] == "/reconciliation", (
                f"Alert '{alert['id']}' in Reconciliation category should navigate to /reconciliation, "
                f"got '{alert['cta_path']}'"
            )


def test_forecast_alert_navigates_to_forecast():
    """Forecast-category alerts must point to /forecast."""
    alerts = get_alerts()
    for alert in alerts:
        if alert["category"] in ("Forecast", "Cash Flow"):
            assert alert["cta_path"] == "/forecast", (
                f"Alert '{alert['id']}' in {alert['category']} should navigate to /forecast, "
                f"got '{alert['cta_path']}'"
            )


def test_revenue_alert_navigates_to_cfo():
    """Revenue alerts must point to /cfo."""
    alerts = get_alerts()
    for alert in alerts:
        if alert["category"] == "Revenue":
            assert alert["cta_path"] == "/cfo", (
                f"Alert '{alert['id']}' in Revenue category should navigate to /cfo, "
                f"got '{alert['cta_path']}'"
            )


# ─── Data consistency tests ───────────────────────────────────────────────────

def test_overview_reconciliation_rate_matches_engine():
    """
    The reconciliation rate on the Overview dashboard must match
    the value reported by the reconciliation summary endpoint directly.
    """
    dashboard = get_dashboard()
    recon = get_reconciliation_data()

    dashboard_rate = dashboard["reconciliation"]["reconciliation_rate"]
    engine_rate = recon["reconciliation_rate"]

    assert abs(dashboard_rate - engine_rate) < 0.01, (
        f"Overview rate {dashboard_rate} ≠ engine rate {engine_rate}"
    )


def test_overview_reconciliation_counts_match_engine():
    """Mismatched and unresolved counts on the Overview must match the reconciliation engine."""
    dashboard = get_dashboard()
    recon = get_reconciliation_data()

    # Dashboard reconciliation sub-object uses short keys (mismatched, unresolved, etc.)
    # reconciliation/summary uses _transactions suffix (mismatched_transactions, etc.)
    assert dashboard["reconciliation"]["mismatched"] == recon["mismatched_transactions"], (
        f"Overview mismatched {dashboard['reconciliation']['mismatched']} ≠ "
        f"engine {recon['mismatched_transactions']}"
    )
    assert dashboard["reconciliation"]["unresolved"] == recon["unresolved_transactions"], (
        f"Overview unresolved {dashboard['reconciliation']['unresolved']} ≠ "
        f"engine {recon['unresolved_transactions']}"
    )


def test_overview_exception_count_is_consistent():
    """
    The reconciliation_exceptions metric value on the Overview must equal
    PARTIALLY_MATCHED + MISMATCHED + PENDING + UNRESOLVED from the engine.
    """
    dashboard = get_dashboard()
    recon = get_reconciliation_data()

    engine_exceptions = (
        recon["mismatched_transactions"]
        + recon["partially_matched_transactions"]
        + recon["pending_transactions"]
        + recon["unresolved_transactions"]
    )
    metrics = dashboard.get("metrics", [])
    overview_exception_metric = next(
        (m["value"] for m in metrics if m.get("id") == "reconciliation_exceptions"), None
    )
    assert overview_exception_metric is not None, (
        "reconciliation_exceptions metric missing from Overview"
    )
    assert overview_exception_metric == engine_exceptions, (
        f"Overview exceptions {overview_exception_metric} ≠ engine total {engine_exceptions}"
    )


def test_health_score_in_dashboard_is_consistent():
    """
    The health_score returned by the dashboard endpoint must have
    a valid overall_score (called twice, checks stability).
    """
    score1 = get_health_score()
    score2 = get_health_score()

    assert abs(score1["overall_score"] - score2["overall_score"]) < 0.1, (
        f"Health score is not stable: {score1['overall_score']} vs {score2['overall_score']}"
    )


def test_dashboard_alerts_match_detect_alerts():
    """
    Two calls to the dashboard must return the same alert IDs in the same order.
    Deterministic ordering is required.
    """
    alerts1 = get_alerts()
    alerts2 = get_alerts()

    ids1 = [a["id"] for a in alerts1]
    ids2 = [a["id"] for a in alerts2]

    assert ids1 == ids2, (
        f"Alert ordering is non-deterministic: {ids1} ≠ {ids2}"
    )
