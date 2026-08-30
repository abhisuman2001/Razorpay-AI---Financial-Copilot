# Razorpay AI — Financial Copilot Spec

## Current MVP

An unauthenticated financial intelligence dashboard with four routed views: Overview, Reconciliation, Forecast, and AI CFO. It uses synthetic transactions seeded into SQLite through SQLAlchemy and exposes read-only FastAPI endpoints under `/api/dashboard`.

## Data model

`FinancialTransaction`: id, transaction date, reference, category, direction, amount, expected amount, and deterministic status (`matched`, `exception`, or `pending`).

## Key flows

- Overview loads backend-owned cash, inflow, outflow, runway, reconciliation, forecast, and insight data.
- Reconciliation lists the deterministic transaction queue and mismatch variance.
- Forecast renders historical cash position plus a six-week Holt trend forecast with an 80% range.
- AI CFO presents static, explainable recommendations sourced from backend calculations.

## Auth and roles

No auth or roles in this cost-zero prototype. No credentials are seeded.