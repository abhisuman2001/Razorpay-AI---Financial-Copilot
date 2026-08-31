"""Healthy Business baseline reset criterion (frontend half): no financial number is
hard-coded in the frontend dashboard views -- figures must come from the API, not from
bare numeric literals in JSX/TSX."""

import re
from pathlib import Path

FRONTEND_SRC = Path(__file__).resolve().parents[2] / "frontend" / "src"


def test_frontend_source_has_no_hardcoded_financial_literals():
    suspicious = []
    for path in FRONTEND_SRC.rglob("*.tsx"):
        if "ui" in path.parts:  # shadcn primitives, not app views
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        # Large bare numeric literals (6+ digits) directly in JSX text look like hardcoded
        # currency/paise amounts; legitimate pixel/id/date constants in this app are shorter.
        for match in re.finditer(r"[>\s](\d{6,})[<\s]", text):
            suspicious.append(f"{path.name}: {match.group(1)}")
    assert not suspicious, f"possible hardcoded financial literals found: {suspicious[:10]}"
