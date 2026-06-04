"""Seed default customer and GPMS ↔ Brazos mappings (idempotent).

Default: gpms_asset_id 223 → brazos tail N407NW.
Only active mappings are included in background polls.
Run: python scripts/seed_mappings.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.seed import seed_mappings

if __name__ == "__main__":
    seed_mappings()
    print("Seed complete (gpms_asset_id=223 → N407NW)")
