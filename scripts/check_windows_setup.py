"""Windows setup diagnostics for nxnative_win.

Run from the repository root:
    py scripts/check_windows_setup.py
    py scripts/check_windows_setup.py --json

Forwards supported options to the existing Windows dependency doctor.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend-qt"

if str(FRONTEND) not in sys.path:
    sys.path.insert(0, str(FRONTEND))

from nspb_qt.win.doctor import main


if __name__ == "__main__":
    raise SystemExit(main())
