# Universal Financial Data Import

The import workspace accepts CSV exports only; it does not connect to bank, gateway, accounting, or marketplace APIs.

## Supported normalized fields

- Transaction ID and reference/order ID
- Transaction date
- Amount, or split debit and credit columns
- Direction, currency, description, counterparty, and status

Amounts in uploaded files are interpreted as major currency units and normalized to integer paise. INR is the default currency. Common ISO and Indian date formats are supported.

## Traceability

Every normalized transaction points to an immutable raw-row record containing the original header/value pairs, source row number, batch, source type, filename, and SHA-256 file hash. Reconciliation never edits those source values.

## Deterministic matching order

1. Shared transaction/reference/order identifier
2. Exact amount and date across different source types
3. Exact amount within a ±2-day window
4. Date mismatch when equal amounts are 3–7 days apart
5. Amount mismatch when a shared reference differs or same-day amounts are within 5%
6. Unmatched when no rule qualifies