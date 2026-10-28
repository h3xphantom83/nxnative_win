"""Guided Windows setup for nxnative_win.

Usage:
    py -3.12 scripts/setup_windows.py

Diagnostic-only: does not install or modify dependencies.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

if sys.version_info[:2] != (3, 12):
    print(
        "ERROR: Python 3.12.x is required. "
        "Run: py -3.12 scripts/setup_windows.py",
        file=sys.stderr,
    )
    raise SystemExit(2)

if os.name != "nt":
    print("ERROR: This setup assistant requires Windows.", file=sys.stderr)
    raise SystemExit(2)

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend-qt"

if str(FRONTEND) not in sys.path:
    sys.path.insert(0, str(FRONTEND))

from nspb_qt.win import shim
from nspb_qt.win import toolchain as tc


def run_checks():
    env = shim.build_env()
    previous = {key: os.environ.get(key) for key in env}

    try:
        os.environ.update(env)
        return tc.check_all(deep=True)
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def main():
    print()
    print("=" * 62)
    print(" NXNATIVE_WIN - WINDOWS SETUP ASSISTANT")
    print("=" * 62)
    print()
    print(f"Python: {sys.version.split()[0]}")
    print(f"Repository: {ROOT}")
    print()
    print("Checking development tools...")
    print()

    probes = run_checks()
    missing = []

    for probe in probes:
        if probe.ok:
            status = "PASS"
        elif probe.required:
            status = "FAIL"
            missing.append(probe)
        else:
            status = "OPTIONAL"

        print(f"[{status:8}] {probe.name}")
        print(f"           {probe.detail}")

        if not probe.ok and probe.hint:
            print(f"           Fix: {probe.hint}")

        print()

    print("-" * 62)

    if missing:
        print(f"{len(missing)} required component(s) need attention.")
        print()
        print("Resolve the issues above and rerun:")
        print("  py -3.12 scripts/setup_windows.py")
        return 1

    print("All required Windows build dependencies are available.")
    print()
    print("Next steps:")
    print("  1. Prepare your legally obtained game files and keys.")
    print("  2. Build using scripts/build_ipa_windows.py.")
    print("  3. See docs/WINDOWS_SETUP.md for detailed instructions.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
