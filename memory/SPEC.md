# Razorpay AI — Financial Copilot Spec

## Current MVP

An unauthenticated financial intelligence workspace with Executive Overview, Reconciliation, Cash Flow, AI CFO, Demo Mode, and Connect Financial Sources. It uses SQLite through SQLAlchemy and exposes FastAPI endpoints under `/api`.

## Data model

`FinancialTransaction`: the compact dashboard demo ledger. The synthetic merchant environment adds relational Customers, Orders, Payments, Refunds, Settlements, Expenses, Chargebacks, FailedPayments, DatasetRuns, and FinancialAnomalies. Amount fields use integer paise.

## Key flows

- Executive Overview loads one backend-owned view model with current-month revenue, current balance, 30-day cash forecast, reconciliation exceptions, 60 actual cash-flow days, 30 forecast days, reconciliation health, AI CFO attention items, metric explanations, and underlying evidence.
- Reconciliation lists the deterministic transaction queue and mismatch variance.
- Cash Flow renders 90 days of actual daily income, expenses, net flow, and cumulative balance plus selectable 7/30/90-day forecasts.
- AI CFO provides session-only chat, fresh daily insights, facts, predictions, reasoning, recommendations, and data citations from read-only financial tools.
- Connect Financial Sources analyzes, maps, previews, imports, traces, and reconciles bank, payment gateway, accounting, and marketplace CSV files in a workspace separate from Demo Mode data.
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

## Executive dashboard

`GET /api/executive/dashboard` is the overview source of truth. Its four top metrics include a deterministic explanation, calculation statement, source metric/tool, drill-down route, and recent payment/settlement/expense/forecast/reconciliation evidence. On mobile, AI attention items precede metrics and chart content; on desktop, metrics lead, followed by cash flow, reconciliation, and insights.

## Demo Mode

The global presentation scenario is persisted in the single-row SQLite `demo_scenario_state` table. `GET /api/demo/scenarios` returns Healthy Business, Revenue Decline, Payment Failure Spike, Cash Flow Risk, Settlement Discrepancy, and High Refund Rate. `POST /api/demo/scenarios/{scenario_id}/activate` atomically replaces only synthetic merchant tables with a deterministic 20,000-payment scenario, then records the active state. Healthy Business is the baseline/reset. Because scenarios regenerate the same relational tables, Executive Dashboard, Reconciliation, Cash Flow, AI CFO, and dataset APIs all continue through their existing calculation pipelines rather than receiving hard-coded UI numbers.

## Universal Financial Data Import

Imports are isolated from synthetic Demo Mode tables. `/api/imports/analyze` accepts CSV files up to 25 MB and 100,000 rows for `bank`, `payment_gateway`, `accounting`, or `marketplace`, detects common headers, stores every untouched raw row with its batch/file hash and source row number, and returns a normalized preview. Mappings can be corrected at `PUT /api/imports/{batch_id}/mapping`; import and automatic reconciliation run at `POST /api/imports/{batch_id}/import`; `POST /api/imports/{batch_id}/reconcile` reruns matching; batch, workspace, and traceable transaction reads are available under `/api/imports`.

The internal imported transaction model stores source/batch lineage, external ID, reference, date, integer-paise amount, direction, currency, description, counterparty, status, fingerprint, and duplicate link. Duplicate detection is source-scoped and deterministic. Cross-source matching prioritizes shared IDs/references, then exact amount/date, then equal amount within ±2 days. Shared-reference amount differences become `AMOUNT_MISMATCH`; equal amounts outside the window become `DATE_MISMATCH`; remaining records are `UNMATCHED`. Every result records its rule, confidence, matched transaction, differences, reason, and reconciliation timestamp.

## Why explainability

`GET /api/why/{metric_id}` supports revenue, cash balance, settlement amount, refund rate, payment success rate, forecasted balance, and reconciliation exceptions. The deterministic analytics layer compares current and previous calendar months (or current vs 30-day prediction for forecasted balance), calculates candidate contributors, assigns direction/effect/impact, ranks the top four, and attaches source metrics. Only those structured findings are passed to the AI CFO deterministic renderer, which performs no financial calculation and cannot add contributors. Responses label facts vs predictions, include the concise explanation, methodology, periods, source references, and detailed driver values.

## Auth and roles

No auth or roles in this cost-zero prototype. No credentials are seeded.