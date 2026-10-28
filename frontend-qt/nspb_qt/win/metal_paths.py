"""Run Windows Metal tools with space-free temporary shader paths.

Windows metal.exe may split quoted paths containing spaces internally. This
adapter is selected only for Metal commands with whitespace-containing paths.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def staging_root() -> Path:
    explicit = os.environ.get('NSPB_METAL_STAGING')
    if explicit:
        root = Path(explicit).resolve()
    else:
        root = Path(tempfile.gettempdir()).resolve()
        if any(ch.isspace() for ch in str(root)):
            drive = os.environ.get('SystemDrive') or root.anchor
            root = Path(drive) / 'NXMetalTemp'
    if any(ch.isspace() for ch in str(root)):
        raise RuntimeError(
            f'Metal staging directory contains whitespace: {root}; '
            'set NSPB_METAL_STAGING to a writable directory without spaces'
        )
    try:
        root.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise RuntimeError(
            f'Cannot create Metal staging directory {root}: {exc}. '
            'Set NSPB_METAL_STAGING to a writable directory without spaces'
        ) from exc
    return root


def run(exe: str, arguments: list[str]) -> int:
    # Current nxnative Metal calls are: metal [flags] source.metal -o output.air
    # and metallib source.air -o output.metallib[.tmp].
    if '-o' not in arguments:
        raise ValueError('Metal adapter expected an -o output argument')
    output_idx = arguments.index('-o') + 1
    if output_idx >= len(arguments):
        raise ValueError('Metal adapter found -o without an output path')
    output_path = Path(arguments[output_idx])
    if not output_path.parent.exists():
        raise FileNotFoundError(f'Metal output directory does not exist: {output_path.parent}')

    with tempfile.TemporaryDirectory(prefix='nxmtl_', dir=staging_root()) as work:
        work_path = Path(work)
        fixed = list(arguments)
        source_count = 0
        for idx, arg in enumerate(arguments):
            if idx == output_idx or idx > 0 and arguments[idx - 1] in ('-o', '-target', '--target'):
                continue
            if arg.startswith('-'):
                continue
            path = Path(arg)
            if path.suffix.lower() not in ('.metal', '.air') or not path.is_file():
                continue
            staged_source = work_path / f'input_{source_count}{path.suffix}'
            shutil.copy2(path, staged_source)
            fixed[idx] = str(staged_source)
            source_count += 1
        if not source_count:
            raise FileNotFoundError('Metal adapter could not identify an existing .metal or .air input')
        # Preserve the original output suffix; output may be .air, .metallib or .tmp.
        staged_output = work_path / ('output' + output_path.suffix)
        fixed[output_idx] = str(staged_output)
        result = subprocess.run([exe, *fixed], check=False)
        if result.returncode != 0:
            return result.returncode
        if not staged_output.is_file():
            raise FileNotFoundError(f'Metal tool returned success but did not create {staged_output}')
        shutil.copy2(staged_output, output_path)
        return 0


if __name__ == '__main__':
    if len(sys.argv) < 3:
        raise SystemExit('Usage: metal_paths.py <metal-or-metallib.exe> <arguments...>')
    try:
        raise SystemExit(run(sys.argv[1], sys.argv[2:]))
    except (OSError, ValueError, RuntimeError) as exc:
        print(f'nxnative Metal staging: {exc}', file=sys.stderr)
        raise SystemExit(1)
