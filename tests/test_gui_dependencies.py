"""Dependency dashboard parsing without requiring PySide6 or Windows tools."""
import json
from nxnative_gui_dependencies import doctor_args, parse_doctor_json, summarize


def test_shallow_command():
    assert doctor_args() == ['-m', 'nspb_qt.win.doctor', '--json', '--no-probe']


def test_deep_command():
    assert doctor_args(True) == ['-m', 'nspb_qt.win.doctor', '--json']


def test_ready_report():
    rows = parse_doctor_json(json.dumps([
        {'name': 'clang', 'state': 'ok', 'required': True, 'path': 'C:/clang.exe'},
        {'name': 'metal-tt', 'state': 'missing', 'required': False},
    ]))
    assert summarize(rows) == 'All 1 required dependencies ready'
    assert rows[0]['path'] == 'C:/clang.exe'


def test_bad_report_and_required_failures():
    import pytest
    rows = parse_doctor_json(json.dumps([
        {'name': 'SDK', 'state': 'wrong', 'required': True, 'hint': 'Install SDK'},
        {'name': 'zstd', 'state': 'ok', 'required': True},
    ]))
    assert '1 required dependency issue(s)' in summarize(rows)
    with pytest.raises(ValueError):
        parse_doctor_json('not JSON')
    with pytest.raises(ValueError):
        parse_doctor_json('{}')
