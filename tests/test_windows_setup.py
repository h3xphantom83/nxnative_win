"""Tests for the Windows first-run setup assistant."""

import importlib.util
import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "setup_windows.py"


def load_setup():
    spec = importlib.util.spec_from_file_location("setup_windows", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_setup_success(monkeypatch, capsys):
    setup = load_setup()

    probe = setup.tc.Probe(
        "llvm", "LLVM (clang)", "ok", "Compiler available"
    )

    monkeypatch.setattr(setup, "run_checks", lambda: [probe])

    assert setup.main() == 0
    output = capsys.readouterr().out

    assert "PASS" in output
    assert "All required Windows build dependencies" in output


def test_setup_reports_missing_dependency(monkeypatch, capsys):
    setup = load_setup()

    probe = setup.tc.Probe(
        "llvm", "LLVM (clang)", "missing",
        "clang.exe not found",
        hint="Install LLVM-MinGW"
    )

    monkeypatch.setattr(setup, "run_checks", lambda: [probe])

    assert setup.main() == 1
    output = capsys.readouterr().out

    assert "FAIL" in output
    assert "clang.exe not found" in output
    assert "Install LLVM-MinGW" in output


def test_optional_dependency_does_not_fail_setup(monkeypatch, capsys):
    setup = load_setup()

    probe = setup.tc.Probe(
        "glslangValidator", "glslangValidator",
        "missing", "not found",
        required=False
    )

    monkeypatch.setattr(setup, "run_checks", lambda: [probe])

    assert setup.main() == 0
    output = capsys.readouterr().out

    assert "OPTIONAL" in output
