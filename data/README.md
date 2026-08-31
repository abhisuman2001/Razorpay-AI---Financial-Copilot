# Synthetic financial data

The backend stores deterministic synthetic merchant records in `financial_copilot.db`. This directory is local-only prototype data and contains no Razorpay credentials or production records.

Regenerate the eight related datasets and their traceable anomaly registry:

```bash
cd /app/backend
python generate_data.py --scenario healthy_business
```

The default seed is `2026`, the default volume is 20,000 payments, and the default presentation scenario is `healthy_business`. Optional flags are `--seed`, `--payments` (minimum 20,000), and `--scenario`. Amounts are stored as integer paise to avoid floating-point errors.