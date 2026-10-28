"""Discover a usable external Python interpreter for nxnative builds."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


def _run(args):
    try:
        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=5,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        pass
    return ""


def python_is_usable(path):
    """Accept a real Python 3.12+ interpreter, not a GUI executable."""
    if not path:
        return False
    exe = Path(path)
    if not exe.is_file():
        return False
    return _run([
        str(exe), "-c",
        "import sys; sys.exit(0 if sys.version_info >= (3, 12) else 1)"
    ]) == "" and _python_version_ok(exe)


def _python_version_ok(exe):
    result = _run([
        str(exe), "-c",
        "import sys; print(int(sys.version_info >= (3, 12)))"
    ])
    return result == "1"


def detect_python(repo):
    """Find an external build interpreter without hardcoded machine paths."""
    repo = Path(repo)

    candidates = [
        repo / ".venv" / "Scripts" / "python.exe",
        repo / "venv" / "Scripts" / "python.exe",
    ]

    if not getattr(sys, "frozen", False):
        candidates.append(Path(sys.executable))

    launcher = shutil.which("py")
    if launcher:
        for version in ("3.14", "3.13", "3.12"):
            resolved = _run([
                launcher, "-" + version, "-c",
                "import sys; print(sys.executable)"
            ])
            if resolved:
                candidates.append(Path(resolved.splitlines()[-1]))

    for name in ("python", "python3"):
        resolved = shutil.which(name)
        if resolved:
            candidates.append(Path(resolved))

    seen = set()
    for candidate in candidates:
        candidate = Path(candidate)
        key = str(candidate).lower()
        if key in seen:
            continue
        seen.add(key)
        if python_is_usable(str(candidate)):
            return str(candidate.resolve())

    return ""
