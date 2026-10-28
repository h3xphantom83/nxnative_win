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


def test_remediation_for_missing_llvm():
    setup = load_setup()

    probe = setup.tc.Probe(
        "llvm", "LLVM (clang)", "missing", "clang.exe not found"
    )

    advice = setup.remediation(probe)

    assert "check_windows_setup.py --fix" in advice


def test_remediation_for_missing_metal():
    setup = load_setup()

    probe = setup.tc.Probe(
        "metal", "Metal Developer Tools", "missing", "metal.exe not found"
    )

    advice = setup.remediation(probe)

    assert "developer.apple.com" in advice


def test_remediation_for_invalid_sdk_override(monkeypatch):
    setup = load_setup()

    monkeypatch.setenv("NSPB_IOS_SDK", "C:\\Nonexistent\\iPhoneOS.sdk")

    probe = setup.tc.Probe(
        "ios_sdk", "iPhoneOS SDK", "missing", "configured path invalid"
    )

    advice = setup.remediation(probe)

    assert "Correct the configured SDK path" in advice
    assert "Remove-Item Env:NSPB_IOS_SDK" in advice
    assert "--import-sdk" not in advice


def test_setup_prints_remediation_command(monkeypatch, capsys):
    """The setup report must show actionable instructions for failures."""
    setup = load_setup()

    probe = setup.tc.Probe(
        "llvm", "LLVM (clang)", "missing",
        "clang.exe not found",
        hint="Install LLVM-MinGW"
    )

    monkeypatch.setattr(setup, "run_checks", lambda: [probe])

    result = setup.main()
    output = capsys.readouterr().out

    assert result == 1
    assert "RECOMMENDED ACTIONS" in output
    assert "check_windows_setup.py --fix" in output
    assert "LLVM (clang)" in output
