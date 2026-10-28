"""Locate an nxnative checkout for source and PyInstaller-frozen GUIs."""
from __future__ import annotations

import os
import sys
from pathlib import Path

MARKER = Path('scripts') / 'build_ipa_windows.py'


def find_repo(*, executable=None, module_file=None, cwd=None, override=None):
    """Find a checkout using an override first, then executable/module/CWD ancestors.

    No recursive directory scanning or fixed drive letters. Reject invalid overrides
    instead of silently running a build against a different checkout.
    """
    override = os.environ.get('NXNATIVE_REPO', '') if override is None else override
    if override:
        candidate = Path(override).expanduser().resolve()
        if not (candidate / MARKER).is_file():
            raise RuntimeError(f'NXNATIVE_REPO does not point to an nxnative checkout: {candidate}')
        return candidate

    executable = sys.executable if executable is None else executable
    module_file = __file__ if module_file is None else module_file
    cwd = Path.cwd() if cwd is None else cwd
    roots = (Path(executable).resolve().parent, Path(module_file).resolve().parent, Path(cwd).resolve())
    seen = set()
    for root in roots:
        for candidate in (root, *root.parents):
            if candidate in seen:
                continue
            seen.add(candidate)
            if (candidate / MARKER).is_file():
                return candidate
    raise RuntimeError(
        'Cannot find nxnative_win (scripts/build_ipa_windows.py). '
        'Place the EXE inside the repository tree or set NXNATIVE_REPO to its root.'
    )
