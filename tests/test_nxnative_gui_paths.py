"""Pure Python repository discovery tests; no Qt dependency."""
from pathlib import Path
import pytest
from nxnative_gui_paths import find_repo


def checkout(root):
    marker = root / 'scripts' / 'build_ipa_windows.py'
    marker.parent.mkdir(parents=True)
    marker.write_text('# fixture', encoding='utf-8')
    return root


def test_frozen_exe_nested_under_checkout(tmp_path):
    root = checkout(tmp_path / 'repo')
    exe = root / 'dist' / 'nxnative-gui' / 'nxnative-gui.exe'
    assert find_repo(executable=exe, module_file=tmp_path / 'elsewhere/gui.py', cwd=tmp_path, override='') == root


def test_explicit_override_for_external_release(tmp_path):
    root = checkout(tmp_path / 'repo')
    external = tmp_path / 'download' / 'nxnative-gui.exe'
    assert find_repo(executable=external, module_file=external, cwd=tmp_path, override=str(root)) == root


def test_invalid_override_fails_closed(tmp_path):
    root = checkout(tmp_path / 'repo')
    with pytest.raises(RuntimeError, match='NXNATIVE_REPO'):
        find_repo(executable=root / 'nxnative-gui.exe', module_file=root / 'gui.py', cwd=root, override=str(tmp_path / 'wrong'))


def test_missing_checkout_fails(tmp_path):
    with pytest.raises(RuntimeError, match='Cannot find'):
        find_repo(executable=tmp_path / 'gui.exe', module_file=tmp_path / 'gui.py', cwd=tmp_path, override='')
