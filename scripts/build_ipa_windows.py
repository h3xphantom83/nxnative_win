#!/usr/bin/env python3
"""Standalone Windows entry point for nxnative's NX2Apple-compatible backend.

Usage: py scripts/build_ipa_windows.py "<NSP folder>" -k "<prod.keys>" -o "<IPA>"
This launcher does not alter the working NX2Apple installation.
"""
from __future__ import annotations
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
FRONTEND = REPO / "frontend-qt"
if not (REPO / "scripts" / "build_ipa_from_nsp.py").is_file():
    raise SystemExit("nxnative upstream scripts/build_ipa_from_nsp.py is missing")
if not (FRONTEND / "nspb_qt" / "win" / "driver.py").is_file():
    raise SystemExit("Windows backend is missing")
if os.name != "nt":
    raise SystemExit("This launcher requires native Windows Python")
sys.path.insert(0, str(FRONTEND))
from nspb_qt.win.driver import main

if __name__ == "__main__":
    raise SystemExit(main())
