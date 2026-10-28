"""Regression tests for Windows iPhoneOS SDK discovery."""

import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "frontend-qt"))

from nspb_qt.win import toolchain as tc


def test_invalid_explicit_sdk_does_not_fall_back(monkeypatch, tmp_path):
    invalid = tmp_path / "missing.sdk"
    cached = tmp_path / "iPhoneOS26.0.sdk"
    cached.mkdir()

    monkeypatch.setenv("NSPB_IOS_SDK", str(invalid))
    monkeypatch.setattr(tc, "sdk_cache_dir", lambda: tmp_path)

    with patch.object(
        tc, "is_sdk_dir",
        side_effect=lambda p: Path(p) == cached
    ):
        assert tc.ios_sdk() is None


def test_valid_explicit_sdk_takes_priority(monkeypatch, tmp_path):
    selected = tmp_path / "selected.sdk"
    cached = tmp_path / "iPhoneOS26.0.sdk"
    selected.mkdir()
    cached.mkdir()

    monkeypatch.setenv("NSPB_IOS_SDK", str(selected))
    monkeypatch.setattr(tc, "sdk_cache_dir", lambda: tmp_path)

    with patch.object(
        tc, "is_sdk_dir",
        side_effect=lambda p: Path(p) in (selected, cached)
    ):
        assert tc.ios_sdk() == selected


def test_invalid_sdk_diagnostic_identifies_configured_path(monkeypatch, tmp_path):
    invalid = tmp_path / "missing.sdk"

    monkeypatch.setenv("NSPB_IOS_SDK", str(invalid))
    monkeypatch.setattr(tc, "sdk_cache_dir", lambda: tmp_path)

    probes = tc.check_all(deep=False)
    sdk = next(p for p in probes if p.id == "ios_sdk")

    assert sdk.state == "missing"
    assert str(invalid) in sdk.detail
    assert "NSPB_IOS_SDK" in sdk.hint
    assert sdk.path == str(invalid)
