"""Demo Mode scenario pipeline: each scenario regenerates the shared synthetic dataset and
every downstream metric/API reads it through the normal deterministic calculation pipeline.

All tests below share the SAME global demo_scenario_state row, so they live in one module
(pytest.ini pins '--dist loadscope' to a single worker per module) and run strictly in
declaration order to avoid cross-test races on that shared state. Each test restores
Healthy Business via the `restore_healthy_business` fixture teardown, and the module also
activates Healthy Business up front so ordering is self-contained even under -p randomly.
"""

from tests.conftest import activate_scenario


def test_scenario_activation_persists_across_reload(restore_healthy_business):
    client = restore_healthy_business

    activation = activate_scenario(client, "revenue_decline")
    assert activation["active_scenario_id"] == "revenue_decline"
    assert activation["payment_count"] == 20000
    assert activation["generated_records"]["payments"] == 20000
    assert "dataset_run_id" in activation

    # Simulate a page reload: a fresh GET must report the same active scenario.
    body = client.get("/demo/scenarios").json()
    assert body["active_scenario_id"] == "revenue_decline"
    active = [s for s in body["scenarios"] if s["active"]]
    assert len(active) == 1 and active[0]["id"] == "revenue_decline"

    body2 = client.get("/demo/scenarios").json()
    assert body2["active_scenario_id"] == "revenue_decline"


def test_unknown_scenario_rejected(restore_healthy_business):
    client = restore_healthy_business
    resp = client.post("/demo/scenarios/not_a_real_scenario/activate")
    assert resp.status_code == 404, resp.text


def test_revenue_decline_lowers_revenue_through_pipeline(restore_healthy_business):
    client = restore_healthy_business

    baseline = activate_scenario(client, "healthy_business")
    assert baseline["generated_records"]["payments"] == 20000
    healthy_revenue = client.get("/cfo/tools/get_revenue").json()["data"]["current_month_revenue"]
    healthy_exec_revenue = next(
        m for m in client.get("/executive/dashboard").json()["metrics"] if m["id"] == "revenue"
    )["value"]

    decline = activate_scenario(client, "revenue_decline")
    assert decline["generated_records"]["payments"] == 20000

    tool_data = client.get("/cfo/tools/get_revenue").json()["data"]
    decline_revenue = tool_data["current_month_revenue"]
    assert decline_revenue < healthy_revenue * 0.7, (
        f"expected materially lower revenue: healthy={healthy_revenue} decline={decline_revenue}"
    )

    exec_dashboard = client.get("/executive/dashboard").json()
    exec_revenue_metric = next(m for m in exec_dashboard["metrics"] if m["id"] == "revenue")
    assert exec_revenue_metric["value"] < healthy_exec_revenue * 0.7
    assert exec_revenue_metric["value"] == decline_revenue
    assert exec_revenue_metric["trend"] == "down"


def test_payment_failure_spike_raises_failures_and_insights(restore_healthy_business):
    client = restore_healthy_business

    healthy = activate_scenario(client, "healthy_business")
    healthy_failed_records = healthy["generated_records"]["failed_payments"]
    healthy_failed_count = client.get("/cfo/tools/get_failed_payments").json()["data"]["current_month_failed_count"]

    spike = activate_scenario(client, "payment_failure_spike")
    spike_failed_records = spike["generated_records"]["failed_payments"]
    assert spike_failed_records > healthy_failed_records * 1.2, (
        f"expected materially more failed_payment records: healthy={healthy_failed_records} spike={spike_failed_records}"
    )

    spike_failed_count = client.get("/cfo/tools/get_failed_payments").json()["data"]["current_month_failed_count"]
    assert spike_failed_count > healthy_failed_count * 1.2, (
        f"expected materially higher current-month failure count: healthy={healthy_failed_count} spike={spike_failed_count}"
    )

    insights = client.get("/cfo/insights").json()["insights"]
    joined = " ".join((i.get("title", "") + " " + i.get("summary", "")).lower() for i in insights)
    assert "fail" in joined, f"expected AI insights to mention payment failures: {joined[:400]}"


def test_cash_flow_risk_raises_outgoing_and_lowers_forecast(restore_healthy_business):
    client = restore_healthy_business

    activate_scenario(client, "healthy_business")
    healthy_forecast = client.get("/forecast/30").json()
    healthy_outgoing = healthy_forecast["expected_outgoing"]
    healthy_balance = healthy_forecast["forecasted_balance"]

    activate_scenario(client, "cash_flow_risk")
    risk_forecast = client.get("/forecast/30").json()
    risk_outgoing = risk_forecast["expected_outgoing"]
    risk_balance = risk_forecast["forecasted_balance"]

    assert risk_outgoing > healthy_outgoing * 1.2, (
        f"expected materially higher 30-day expected outgoing: healthy={healthy_outgoing} risk={risk_outgoing}"
    )
    assert risk_balance < healthy_balance, (
        f"expected lower forecasted balance: healthy={healthy_balance} risk={risk_balance}"
    )
    assert len(risk_forecast["forecast"]) == 30
    assert len(risk_forecast["historical"]) > 0
    assert isinstance(risk_forecast["risks"], list)

    exec_dashboard = client.get("/executive/dashboard").json()
    assert len(exec_dashboard["cashflow_forecast"]) == 30
    assert len(exec_dashboard["cashflow_actual"]) > 0


def test_settlement_discrepancy_raises_mismatches(restore_healthy_business):
    client = restore_healthy_business

    activate_scenario(client, "healthy_business")
    healthy_summary = client.get("/reconciliation/summary").json()
    healthy_mismatched = healthy_summary["mismatched_transactions"]
    healthy_discrepancy = healthy_summary["total_discrepancy"]

    activate_scenario(client, "settlement_discrepancy")
    disc_summary = client.get("/reconciliation/summary").json()
    disc_mismatched = disc_summary["mismatched_transactions"]
    disc_discrepancy = disc_summary["total_discrepancy"]

    assert disc_mismatched > healthy_mismatched * 1.2, (
        f"expected materially more mismatches: healthy={healthy_mismatched} scenario={disc_mismatched}"
    )
    assert disc_discrepancy > healthy_discrepancy * 1.2, (
        f"expected materially higher discrepancy: healthy={healthy_discrepancy} scenario={disc_discrepancy}"
    )

    exceptions = client.get("/reconciliation/exceptions").json()
    assert exceptions["total"] >= disc_mismatched
    assert len(exceptions["items"]) > 0
    first_id = exceptions["items"][0]["id"]
    detail = client.get(f"/reconciliation/{first_id}")
    assert detail.status_code == 200, detail.text


def test_high_refund_rate_raises_refund_rate(restore_healthy_business):
    client = restore_healthy_business

    activate_scenario(client, "healthy_business")
    healthy_rate = client.get("/cfo/tools/get_refunds").json()["data"]["refund_rate_percent"]

    activate_scenario(client, "high_refund_rate")
    refund_data = client.get("/cfo/tools/get_refunds").json()["data"]
    high_rate = refund_data["refund_rate_percent"]

    assert high_rate > healthy_rate * 1.5, (
        f"expected materially higher refund rate: healthy={healthy_rate} scenario={high_rate}"
    )
    assert refund_data["processed_refund_count"] > 0

    settlement_summary = client.get("/cfo/tools/get_settlement_summary").json()["data"]
    assert settlement_summary["settlement_count"] > 0
    assert settlement_summary["refund_amount"] > 0

    insights = client.get("/cfo/insights").json()["insights"]
    joined = " ".join((i.get("title", "") + " " + i.get("summary", "")).lower() for i in insights)
    assert "refund" in joined, f"expected AI insights to reference refunds: {joined[:400]}"

    exec_dashboard = client.get("/executive/dashboard").json()
    assert len(exec_dashboard["insights"]) > 0


def test_healthy_business_resets_baseline(restore_healthy_business):
    client = restore_healthy_business

    baseline = activate_scenario(client, "healthy_business")
    baseline_revenue = client.get("/cfo/tools/get_revenue").json()["data"]["current_month_revenue"]
    baseline_forecast = client.get("/forecast/30").json()["forecasted_balance"]

    activate_scenario(client, "revenue_decline")
    decline_revenue = client.get("/cfo/tools/get_revenue").json()["data"]["current_month_revenue"]
    assert decline_revenue != baseline_revenue

    restored = activate_scenario(client, "healthy_business")
    assert restored["active_scenario_id"] == "healthy_business"

    body = client.get("/demo/scenarios").json()
    assert body["active_scenario_id"] == "healthy_business"
    active = [s for s in body["scenarios"] if s["active"]]
    assert active[0]["id"] == "healthy_business"

    restored_revenue = client.get("/cfo/tools/get_revenue").json()["data"]["current_month_revenue"]
    restored_forecast = client.get("/forecast/30").json()["forecasted_balance"]
    # Same scenario definition + fixed seed regenerated deterministically -> identical baseline,
    # and materially different from the revenue_decline scenario that was active in between.
    assert restored_revenue > decline_revenue * 1.3
    assert restored_revenue == baseline_revenue
    assert restored_forecast == baseline_forecast
