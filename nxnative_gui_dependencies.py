"""Pure helpers for the Windows GUI dependency dashboard."""
from __future__ import annotations
import json


def doctor_args(deep: bool = False) -> list[str]:
    args = ['-m', 'nspb_qt.win.doctor', '--json']
    if not deep:
        args.append('--no-probe')
    return args


def parse_doctor_json(output: str) -> list[dict]:
    try:
        data = json.loads(output)
    except (ValueError, TypeError) as exc:
        raise ValueError('Doctor returned invalid JSON') from exc
    if not isinstance(data, list):
        raise ValueError('Doctor report must contain a JSON list')
    result = []
    for item in data:
        if not isinstance(item, dict) or item.get('state') not in {'ok', 'missing', 'wrong'}:
            raise ValueError('Unexpected dependency probe entry')
        result.append({
            'id': str(item.get('id', '')),
            'name': str(item.get('name', 'Unknown')),
            'state': item['state'],
            'required': item.get('required', True) is not False,
            'version': str(item.get('version') or ''),
            'path': str(item.get('path') or ''),
            'detail': str(item.get('detail') or ''),
            'hint': str(item.get('hint') or ''),
        })
    return result


def summarize(rows: list[dict]) -> str:
    required = [r for r in rows if r['required']]
    failures = [r for r in required if r['state'] != 'ok']
    if failures:
        return f"{len(failures)} required dependency issue(s); {len(required) - len(failures)}/{len(required)} ready"
    return f'All {len(required)} required dependencies ready'
