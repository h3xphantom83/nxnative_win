"""Pure readiness calculations for the nxnative dependency panel."""
from __future__ import annotations


def readiness_counts(rows: list[dict] | None) -> dict[str, int | str]:
    """None means unchecked, whereas [] is an empty/invalid probe report."""
    if rows is None or not rows:
        return {'status': 'Not checked', 'passed': 0, 'required': 0,
                'issues': 0, 'optional_missing': 0}
    required = [row for row in rows if row.get('required', True)]
    passed = sum(row.get('state') == 'ok' for row in required)
    issues = len(required) - passed
    optional_missing = sum(row.get('state') != 'ok' for row in rows
                           if not row.get('required', True))
    status = ('Required dependencies missing' if issues else
              'Ready to build (dependency checks passed)')
    return {'status': status, 'passed': passed, 'required': len(required),
            'issues': issues, 'optional_missing': optional_missing}
