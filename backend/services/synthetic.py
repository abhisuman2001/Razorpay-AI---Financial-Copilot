from datetime import date, timedelta

from lib.dates import today_iso


def build_synthetic_transactions() -> list[dict]:
    """Return stable demo records; no external credentials or APIs are needed."""
    start = date.fromisoformat(today_iso()) - timedelta(days=77)
    records = [
        ("settlement-001", 0, "Card settlements", "inflow", 42000, 42000, "matched"),
        ("payroll-001", 1, "Payroll", "outflow", 18500, 18500, "matched"),
        ("settlement-002", 7, "Card settlements", "inflow", 46500, 46500, "matched"),
        ("ads-001", 8, "Marketing", "outflow", 7200, 7600, "exception"),
        ("settlement-003", 14, "Card settlements", "inflow", 39200, 39200, "matched"),
        ("vendor-001", 15, "Inventory", "outflow", 12800, 12800, "matched"),
        ("settlement-004", 21, "Card settlements", "inflow", 51400, 51400, "matched"),
        ("rent-001", 22, "Workspace", "outflow", 9800, 9800, "matched"),
        ("settlement-005", 28, "Card settlements", "inflow", 47800, 47800, "matched"),
        ("vendor-002", 29, "Inventory", "outflow", 15600, 16250, "exception"),
        ("settlement-006", 35, "Card settlements", "inflow", 53200, 53200, "matched"),
        ("payroll-002", 36, "Payroll", "outflow", 18500, 18500, "matched"),
        ("settlement-007", 42, "Card settlements", "inflow", 55800, 55800, "matched"),
        ("software-001", 43, "Software", "outflow", 4200, 4200, "pending"),
        ("settlement-008", 49, "Card settlements", "inflow", 57600, 57600, "matched"),
        ("vendor-003", 50, "Inventory", "outflow", 17400, 18100, "exception"),
        ("settlement-009", 56, "Card settlements", "inflow", 60400, 60400, "matched"),
        ("rent-002", 57, "Workspace", "outflow", 9800, 9800, "matched"),
        ("settlement-010", 63, "Card settlements", "inflow", 62800, 62800, "matched"),
        ("tax-001", 64, "Tax reserve", "outflow", 11200, 11200, "pending"),
        ("settlement-011", 70, "Card settlements", "inflow", 65200, 65200, "matched"),
        ("vendor-004", 71, "Inventory", "outflow", 19200, 19950, "exception"),
        ("settlement-012", 77, "Card settlements", "inflow", 67900, 67900, "pending"),
        ("payroll-003", 78, "Payroll", "outflow", 21000, 21000, "pending"),
    ]
    return [
        {
            "id": reference,
            "transaction_date": start + timedelta(days=offset),
            "reference": reference.upper(),
            "category": category,
            "direction": direction,
            "amount": amount,
            "expected_amount": expected_amount,
            "status": status,
        }
        for reference, offset, category, direction, amount, expected_amount, status in records
    ]