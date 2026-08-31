# Razorpay AI — Financial Copilot Spec

## Current MVP

An unauthenticated financial intelligence dashboard with four routed views: Overview, Reconciliation, Forecast, and AI CFO. It uses synthetic transactions seeded into SQLite through SQLAlchemy and exposes read-only FastAPI endpoints under `/api/dashboard`.

## Data model

`FinancialTransaction`: the compact dashboard demo ledger. The synthetic merchant environment adds relational Customers, Orders, Payments, Refunds, Settlements, Expenses, Chargebacks, FailedPayments, DatasetRuns, and FinancialAnomalies. Amount fields use integer paise.

## Key flows

- Overview loads backend-owned cash, inflow, outflow, runway, reconciliation, forecast, and insight data.
- Reconciliation lists the deterministic transaction queue and mismatch variance.
- Forecast renders historical cash position plus a six-week Holt trend forecast with an 80% range.
- AI CFO presents static, explainable recommendations sourced from backend calculations.
- `python backend/generate_data.py` replaces only the synthetic merchant tables with at least 20,000 deterministic payments and proportionate related records.
- `/api/datasets/*` exposes paginated read endpoints plus a summary of counts and anomalies. Filters are available for common statuses, methods, categories, and anomaly types.

## Synthetic anomaly contract

Every injected anomaly has a row in `financial_anomalies` with its dataset run, type, entity, optional related entity, expected/actual amount, and explanation. Controlled types include duplicate-looking payments, unusual payment spikes, captured payments without settlements, orphan settlements, settlement amount mismatches, delayed settlements, and chargebacks.

## Auth and roles

No auth or roles in this cost-zero prototype. No credentials are seeded.