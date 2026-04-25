#!/usr/bin/env python3
"""
One-shot loader: apply schema (via first DB connection) and import bundled CSVs
from `database import/`. Run locally or in a one-off Render shell with DATABASE_URL set.

Does not import `Mug Club recipes.txt` (unstructured); add recipes via the app or a future parser.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
IMPORT_DIR = ROOT / "database import"


def main() -> int:
    if not os.environ.get("DATABASE_URL"):
        print("DATABASE_URL is not set.", file=sys.stderr)
        return 1
    os.chdir(ROOT)
    sys.path.insert(0, str(ROOT))

    from app import import_financial_csv, import_inventory_csv, import_margins_csv

    inv = IMPORT_DIR / "Mug Club datasheet - inventory.csv"
    margins = IMPORT_DIR / "Mug Club datasheet - margins (1).csv"
    fin = IMPORT_DIR / "3_The Mug Club_Financials - Financial Tracker.csv"

    for label, path in (
        ("Inventory", inv),
        ("Margins", margins),
        ("Finance", fin),
    ):
        if not path.is_file():
            print(f"Skip {label}: missing file {path.name}")
            continue
        print(f"Importing {label} from {path.name} …")
        with path.open("rb") as f:
            if label == "Inventory":
                a, b = import_inventory_csv(f, replace=True)
                print(f"  → {a} items, {b} prep rows")
            elif label == "Margins":
                a, b = import_margins_csv(f, replace=True)
                print(f"  → {a} ingredients, {b} menu lines")
            else:
                a, b = import_financial_csv(f, replace=True)
                print(f"  → {a} inflows, {b} outflows")
    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
