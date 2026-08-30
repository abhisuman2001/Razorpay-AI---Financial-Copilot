# Razorpay AI — Financial Copilot

## Prototype boundaries

This prototype uses synthetic financial transactions stored in SQLite through SQLAlchemy. It does not connect to Razorpay production, payment providers, cloud services, or paid AI APIs.

The flow is deliberately separated:

1. **Reconcile** — deterministic amount and status rules produce the reconciliation queue.
2. **Predict** — a Holt exponential-smoothing trend model produces the six-week cash forecast and range.
3. **Decide** — `services/ai.py` formats backend-calculated facts into explainable recommendations.

All numbers in the UI originate from Pydantic response models returned by the FastAPI API. The recommendation generator never calculates or invents financial numbers.

## Ollama seam

`StaticInsightGenerator` is the current provider and requires no credentials. A future `OllamaInsightGenerator` can implement the same `generate(reconciliation, forecast)` contract, receiving only validated backend facts and returning structured `Insight` objects. The frontend should remain unchanged.

## Runtime layout

- `backend/models/` — Pydantic API schemas and SQLAlchemy tables
- `backend/services/` — synthetic data, deterministic financial logic, and insight provider
- `backend/routers/` — `/api/dashboard` endpoints
- `data/` — local SQLite file created on first backend startup
- `ai/` — future local-model adapters and prompt contracts
- `frontend/src/pages/` — routed dashboard views