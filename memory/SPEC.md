# Razorpay AI — Financial Copilot Spec

## Current MVP

An unauthenticated financial intelligence dashboard with four routed views: Overview, Reconciliation, Forecast, and AI CFO. It uses synthetic transactions seeded into SQLite through SQLAlchemy and exposes read-only FastAPI endpoints under `/api/dashboard`.

## Data model

`FinancialTransaction`: the compact dashboard demo ledger. The synthetic merchant environment adds relational Customers, Orders, Payments, Refunds, Settlements, Expenses, Chargebacks, FailedPayments, DatasetRuns, and FinancialAnomalies. Amount fields use integer paise.

## Key flows

- Overview loads backend-owned cash, inflow, outflow, runway, reconciliation, forecast, and insight data.
- Reconciliation lists the deterministic transaction queue and mismatch variance.
- Cash Flow renders 90 days of actual daily income, expenses, net flow, and cumulative balance plus selectable 7/30/90-day forecasts.
- AI CFO provides session-only chat, fresh daily insights, facts, predictions, reasoning, recommendations, and data citations from read-only financial tools.
- `python backend/generate_data.py` replaces only the synthetic merchant tables with at least 20,000 deterministic payments and proportionate related records.
- `/api/datasets/*` exposes paginated read endpoints plus a summary of counts and anomalies. Filters are available for common statuses, methods, categories, and anomaly types.

## Synthetic anomaly contract

Every injected anomaly has a row in `financial_anomalies` with its dataset run, type, entity, optional related entity, expected/actual amount, and explanation. Controlled types include duplicate-looking payments, unusual payment spikes, captured payments without settlements, orphan settlements, settlement amount mismatches, settlement component mismatches, delayed settlements, and chargebacks.

## Deterministic reconciliation

`/api/reconciliation/summary`, `/api/reconciliation/exceptions`, and `/api/reconciliation/{id}` compare each captured payment with its settlement. Expected net is calculated in integer paise as gross payment minus processed refunds, deterministic method fee, and 18% tax on fees. Exact net and component matches are `MATCHED`; equal net with a component difference is `PARTIALLY_MATCHED`; non-zero net difference is `MISMATCHED`; in-window/processing records are `PENDING`; missing, failed, or orphan links are `UNRESOLVED`. The default date range is the server-anchored last 90 days.

## Statistical cash-flow forecast

`/api/forecast/7`, `/api/forecast/30`, and `/api/forecast/90` use SQLite history only. Daily income is recognized from settled net cash on settlement dates; daily expenses come from booked expenses. Current balance equals configurable `OPENING_CASH_BALANCE_PAISE` plus all historical daily net cash flow. Separate additive Holt-Winters models apply a damped trend and weekly seasonality to income and expenses. Forecast responses include all predicted values, cumulative balance, an 80% residual-based balance range, methodology, and deterministic liquidity/concentration/volatility/expense risks. No LLM performs or adjusts numerical forecasting.

## AI CFO architecture

The read-only tool registry exposes `get_revenue`, `get_expenses`, `get_cash_balance`, `get_failed_payments`, `get_refunds`, `get_settlement_summary`, `get_reconciliation_exceptions`, `get_cashflow_forecast`, `get_top_customers`, and `get_customer_statistics`. Every tool returns structured, period-labeled JSON with source references and fact/prediction classification. `/api/cfo/chat` selects only relevant tools and returns grounded facts, predictions, reasoning, recommendations, and citations. `/api/cfo/insights` creates five fresh daily insights on request. `/api/cfo/tools/{tool_name}` makes tool output auditable.

`AI_CFO_PROVIDER=deterministic` is the zero-cost default. An optional loopback-only Ollama adapter can be enabled later with `AI_CFO_PROVIDER=ollama`; it receives only selected structured tool context, has no write capability, and is guarded against unsupported numeric output. Provider failures or ungrounded output fall back deterministically. Chat history is held only in the browser session and is never written to SQLite.

## Auth and roles

No auth or roles in this cost-zero prototype. No credentials are seeded.