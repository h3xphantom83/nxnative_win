#!/usr/bin/env python3
"""Non-destructive structural validation of the Windows backend."""
import ast
import os
import sys
from pathlib import Path

repo = Path(__file__).resolve().parents[1]
win = repo / "frontend-qt" / "nspb_qt" / "win"
required = [repo / "scripts" / "build_ipa_from_nsp.py", win / "driver.py",
            win / "toolchain.py", win / "shim.py", win / "build_app.py",
            win / "ios" / "Launcher.m", win / "ios" / "compat_rt.c"]
failed = False
for p in required:
    ok = p.is_file()
    print(f"{'OK' if ok else 'MISSING'}: {p.relative_to(repo)}")
    failed |= not ok
for p in win.glob('*.py'):
    try:
        ast.parse(p.read_text(encoding='utf-8'), filename=str(p))
    except (SyntaxError, UnicodeError) as exc:
        print(f"INVALID: {p.name}: {exc}")
        failed = True
print('Platform:', os.name, '| Python:', sys.version.split()[0])
raise SystemExit(1 if failed else 0)
