"""Optional IPA validation for Windows builds."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def extract_flag(argv):
    """Remove --validate-ipa before upstream parses build arguments."""
    args = []
    enabled = False

    for arg in argv:
        if arg == '--validate-ipa':
            enabled = True
        elif arg.startswith('--validate-ipa='):
            raise ValueError('--validate-ipa does not accept a value')
        else:
            args.append(arg)

    return args, enabled


def validate(repo, args):
    """Validate the completed IPA; propagate validation failures."""
    from .romfs_integration import get_option

    output = get_option(args, '-o')
    if not output:
        raise ValueError('--validate-ipa requires an output IPA (-o)')

    ipa = Path(output).resolve()
    if not ipa.is_file():
        raise FileNotFoundError(f'IPA not found: {ipa}')

    validator = repo / 'scripts' / 'validate_ipa.py'
    if not validator.is_file():
        raise FileNotFoundError(f'IPA validator not found: {validator}')

    print(f'[IPA] Validating {ipa}', flush=True)

    subprocess.run(
        [sys.executable, '-u', str(validator), str(ipa)],
        check=True,
    )

    print('[IPA] Validation successful', flush=True)
