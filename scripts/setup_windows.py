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


def remediation(probe):
    """Return actionable instructions for a failed dependency."""
    steps = {
        "llvm": (
            "Install LLVM-MinGW using the existing Windows doctor:\n"
            "  py -3.12 scripts/check_windows_setup.py --fix"
        ),
        "lld": (
            "The Mach-O linker is provided by LLVM-MinGW.\n"
            "Verify the LLVM installation and rerun the dependency checker:\n"
            "  py -3.12 scripts/check_windows_setup.py"
        ),
        "dotnet": (
            "Install the .NET SDK 10 from Microsoft's official downloads:\n"
            "  https://dotnet.microsoft.com/download/dotnet/10.0"
        ),
        "metal": (
            "Install Metal Developer Tools for Windows from Apple:\n"
            "  https://developer.apple.com/download/all/?q=metal%20developer%20tools"
        ),
        "zstd": (
            "Install the zstd command-line utility:\n"
            "  https://github.com/facebook/zstd/releases"
        ),
        "ios_sdk": (
            "Configure a valid iPhoneOS SDK with NSPB_IOS_SDK, or import one:\n"
            "  py -3.12 scripts/check_windows_setup.py --import-sdk <SDK_FOLDER>\n"
            "Obtain and use SDK files only in accordance with applicable licenses."
        ),
    }

    if probe.id == "ios_sdk" and tc.setting("ios_sdk"):
        return (
            "Correct the configured SDK path or remove the override.\n"
            "Current SDK: " + tc.setting("ios_sdk") + "\n"
            "PowerShell, current session:\n"
            "  Remove-Item Env:NSPB_IOS_SDK"
        )

    return steps.get(probe.id, probe.hint or "Review the dependency checker output.")


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
        print("RECOMMENDED ACTIONS")
        print("-" * 62)

        for probe in missing:
            print()
            print(f"{probe.name}:")
            print(remediation(probe))
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
