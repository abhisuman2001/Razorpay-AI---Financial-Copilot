"""Criterion: Import workspace remains separate from Demo Mode data."""

from tests.helpers_imports import analyze, build_csv, confirm_import, rerun_reconciliation, unique_suffix


def _csv(suffix: str) -> bytes:
    return build_csv(
        ["Transaction ID", "Reference", "Date", "Amount", "Type", "Description"],
        [
            [f"tscheck-isolation-{suffix}-1", f"tscheck-isolation-ref-{suffix}-1", "2024-06-01", "1500.00", "credit", "isolation check row 1"],
            [f"tscheck-isolation-{suffix}-2", f"tscheck-isolation-ref-{suffix}-2", "2024-06-02", "750.00", "debit", "isolation check row 2"],
        ],
    )


def test_import_and_reconcile_does_not_affect_demo_dataset(client):
    scenarios_before = client.get("/demo/scenarios")
    assert scenarios_before.status_code == 200
    active_before = scenarios_before.json()["active_scenario_id"]

    dashboard_before = client.get("/executive/dashboard")
    assert dashboard_before.status_code == 200
    metrics_before = {m["id"]: m["value"] for m in dashboard_before.json()["metrics"]}

    dataset_before = client.get("/datasets/summary")
    assert dataset_before.status_code == 200
    counts_before = dataset_before.json()["counts"]

    forecast_before = client.get("/forecast/30")
    assert forecast_before.status_code == 200
    forecast_balance_before = forecast_before.json()["forecasted_balance"]

    # Run a full import + reconcile cycle on unrelated CSV data.
    suffix = unique_suffix()
    resp = analyze(client, "bank", f"tscheck-isolation-{suffix}.csv", _csv(suffix))
    assert resp.status_code == 200, resp.text[:300]
    batch_id = resp.json()["batch"]["id"]
    import_resp = confirm_import(client, batch_id)
    assert import_resp.status_code == 200, import_resp.text[:300]
    reconcile_resp = rerun_reconciliation(client, batch_id)
    assert reconcile_resp.status_code == 200, reconcile_resp.text[:300]

    scenarios_after = client.get("/demo/scenarios")
    assert scenarios_after.status_code == 200
    active_after = scenarios_after.json()["active_scenario_id"]
    assert active_after == active_before, "active demo scenario must not change from CSV imports"

    dashboard_after = client.get("/executive/dashboard")
    assert dashboard_after.status_code == 200
    metrics_after = {m["id"]: m["value"] for m in dashboard_after.json()["metrics"]}
    assert metrics_after == metrics_before, "executive metrics must be unaffected by CSV import workspace"

    dataset_after = client.get("/datasets/summary")
    assert dataset_after.status_code == 200
    counts_after = dataset_after.json()["counts"]
    assert counts_after == counts_before, "synthetic dataset counts (incl. payments) must be unaffected by CSV import"

    forecast_after = client.get("/forecast/30")
    assert forecast_after.status_code == 200
    assert forecast_after.json()["forecasted_balance"] == forecast_balance_before
