"""Regression tests for Qt-independent build-result decisions."""
from nxnative_gui_result import classify_result


def test_success(tmp_path):
    ipa = tmp_path / 'game.ipa'
    ipa.write_bytes(b'PK')
    assert classify_result(0, False, False, str(ipa))[0] == 'success'


def test_nonzero_is_failure(tmp_path):
    ipa = tmp_path / 'game.ipa'
    ipa.write_bytes(b'PK')
    assert classify_result(2, False, False, str(ipa))[0] == 'error'


def test_crash_is_failure(tmp_path):
    ipa = tmp_path / 'game.ipa'
    ipa.write_bytes(b'PK')
    assert classify_result(0, True, False, str(ipa))[0] == 'error'


def test_stopped_is_cancelled(tmp_path):
    ipa = tmp_path / 'game.ipa'
    ipa.write_bytes(b'PK')
    assert classify_result(1, True, True, str(ipa))[0] == 'cancelled'


def test_success_requires_ipa(tmp_path):
    assert classify_result(0, False, False, str(tmp_path / 'missing.ipa'))[0] == 'error'
