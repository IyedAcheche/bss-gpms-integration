"""Run HUMS and FDM polls once for all active mapped assets.

Does not start the scheduler. Useful after adding mappings or GPMS credentials.
Requires DATABASE_URL and GPMS_EMAIL / GPMS_PASSWORD in .env.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db import init_db
from app.jobs.fdm_poll import run_fdm_poll
from app.jobs.hums_poll import run_hums_poll


def main() -> None:
    init_db()
    run_hums_poll()
    run_fdm_poll()


if __name__ == "__main__":
    main()
