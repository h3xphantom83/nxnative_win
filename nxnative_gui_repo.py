"""Select the correct nxnative checkout for the Windows GUI."""

from __future__ import annotations

import os
import sys
from pathlib import Path


REQUIRED = (
    "scripts/build_ipa_windows.py",
    "scripts/validate_ipa.py",
    "frontend-qt/nspb_qt/win/driver.py",
)


def is_valid_repo(path: Path) -> bool:
    return path.is_dir() and all(
        (path / item).is_file() for item in REQUIRED
    )


def resolve_gui_repository(module_file: str) -> Path:
    """Explicit override, then GUI checkout, then packaged EXE locations."""

    override = os.environ.get("NXNATIVE_REPO", "").strip()
    if override:
        candidate = Path(override).expanduser().resolve()
        if not is_valid_repo(candidate):
            raise RuntimeError(
                f"NXNATIVE_REPO is not a complete nxnative checkout: {candidate}"
            )
        return candidate

    source = Path(module_file).resolve()
    candidates = [source.parent, *source.parents]

    if getattr(sys, "frozen", False):
        exe = Path(sys.executable).resolve()
        candidates.extend([exe.parent, *exe.parents])

    seen = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        if is_valid_repo(candidate):
            return candidate

    raise RuntimeError(
        "Cannot locate a complete nxnative checkout. "
        "Set NXNATIVE_REPO to your nxnative_win repository directory."
    )
