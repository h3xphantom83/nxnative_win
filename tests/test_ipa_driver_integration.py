"""Tests for optional Windows IPA validation integration."""

import subprocess
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from nspb_qt.win import ipa_validation


def test_validate_ipa_flag_removed():
    args, enabled = ipa_validation.extract_flag([
        "game", "--validate-ipa", "-o", "game.ipa"
    ])
    assert enabled is True
    assert args == ["game", "-o", "game.ipa"]


def test_validate_ipa_default_disabled():
    args, enabled = ipa_validation.extract_flag([
        "game", "-o", "game.ipa"
    ])
    assert enabled is False
    assert args == ["game", "-o", "game.ipa"]


def test_ipa_validator_invoked(tmp_path):
    repo = tmp_path / "repo"
    script = repo / "scripts" / "validate_ipa.py"
    script.parent.mkdir(parents=True)
    script.write_text("# synthetic validator", encoding="utf-8")

    ipa = tmp_path / "test.ipa"
    ipa.write_bytes(b"synthetic")

    with patch.object(ipa_validation.subprocess, "run") as run:
        ipa_validation.validate(repo, ["game", "-o", str(ipa)])

    run.assert_called_once()
    assert str(script) in run.call_args.args[0]
    assert str(ipa) in run.call_args.args[0]
    assert run.call_args.kwargs["check"] is True


def test_driver_suppresses_completion_on_ipa_failure(
    monkeypatch, capsys, tmp_path
):
    import nspb_qt.win.driver as driver
    from nspb_qt.win import romfs_integration, shim

    upstream = SimpleNamespace(cli=lambda args: 0)

    monkeypatch.setattr(driver, "check_cli", lambda args: None)
    monkeypatch.setattr(driver, "repo_dir", lambda: tmp_path)
    monkeypatch.setattr(driver, "load_upstream", lambda repo: upstream)
    monkeypatch.setattr(driver, "patch", lambda mod, repo: None)

    monkeypatch.setattr(
        shim, "build_env",
        lambda **kwargs: dict(__import__("os").environ),
    )

    def validation_failure(repo, args):
        raise ValueError("Simulated invalid IPA")

    monkeypatch.setattr(
        ipa_validation, "validate", validation_failure
    )

    def must_not_run(*args, **kwargs):
        raise AssertionError(
            "ROMFS processing must not run after invalid IPA"
        )

    monkeypatch.setattr(
        romfs_integration, "finish_build", must_not_run
    )

    result = driver.main([
        str(tmp_path),
        "-o", str(tmp_path / "invalid.ipa"),
        "--validate-ipa",
    ])

    output = capsys.readouterr()

    assert result == 1
    assert "Simulated invalid IPA" in output.err
    assert "BUILD COMPLETE" not in output.out
    assert "BUILD COMPLETE" not in output.err
