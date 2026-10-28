"""Windows toolchain discovery and diagnostic regression tests."""

import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "frontend-qt"))

from nspb_qt.win import toolchain as tc


def test_missing_llvm_is_reported(monkeypatch):
    monkeypatch.setattr(tc, "llvm_dir", lambda: None)
    monkeypatch.setattr(tc, "llvm_tool", lambda name: None)

    probes = tc.check_all(deep=False)
    llvm = next(p for p in probes if p.id == "llvm")

    assert llvm.state == "missing"
    assert "clang.exe" in llvm.detail


def test_missing_macho_linker_is_reported(monkeypatch):
    monkeypatch.setattr(tc, "ld64_lld", lambda: None)
    monkeypatch.setattr(
        tc, "ensure_ld64_lld",
        lambda: (None, "Mach-O linker unavailable")
    )

    probes = tc.check_all(deep=False)
    linker = next(p for p in probes if p.id == "lld")

    assert linker.state in ("missing", "wrong")


def test_missing_metal_is_reported(monkeypatch):
    monkeypatch.setattr(tc, "metal_dir", lambda: None)
    monkeypatch.setattr(tc, "metal_tool", lambda *args, **kwargs: None)

    probes = tc.check_all(deep=False)
    metal = next(p for p in probes if p.id == "metal")

    assert metal.state == "missing"
    assert metal.required


def test_cached_sdk_discovery_without_override(monkeypatch, tmp_path):
    cached = tmp_path / "iPhoneOS26.0.sdk"
    cached.mkdir()

    monkeypatch.delenv("NSPB_IOS_SDK", raising=False)
    monkeypatch.setattr(tc, "load_config", lambda: {})
    monkeypatch.setattr(tc, "sdk_cache_dir", lambda: tmp_path)

    with patch.object(
        tc, "is_sdk_dir",
        side_effect=lambda p: Path(p) == cached
    ):
        assert tc.ios_sdk() == cached


def test_explicit_sdk_wins_over_cached_sdk(monkeypatch, tmp_path):
    explicit = tmp_path / "iPhoneOS27.0.sdk"
    cached = tmp_path / "iPhoneOS26.0.sdk"
    explicit.mkdir()
    cached.mkdir()

    monkeypatch.setenv("NSPB_IOS_SDK", str(explicit))
    monkeypatch.setattr(tc, "sdk_cache_dir", lambda: tmp_path)

    with patch.object(
        tc, "is_sdk_dir",
        side_effect=lambda p: Path(p) in (explicit, cached)
    ):
        assert tc.ios_sdk() == explicit


def test_setup_checker_rejects_python_313():
    """Simulate Python 3.13 without modifying installed interpreters."""
    import subprocess

    script = ROOT / "scripts" / "check_windows_setup.py"
    source = script.read_text(encoding="utf-8-sig")

    guard = source.split("ROOT = Path(__file__)")[0]

    # Keep future imports at the beginning of the executed source.
    simulation = """
class Version:
    major = 3
    minor = 13

    def __getitem__(self, key):
        return (3, 13)[key]

sys.version_info = Version()
"""

    anchor = "if sys.version_info[:2] != (3, 12):"

    assert guard.count(anchor) == 1

    code = guard.replace(anchor, simulation + "\n" + anchor)

    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 2, result.stderr
    assert "requires Python 3.12.x" in result.stderr
    assert "Detected Python 3.13" in result.stderr


def test_doctor_does_not_recommend_download_for_invalid_sdk(monkeypatch, tmp_path, capsys):
    """An invalid explicit SDK path should prompt correction, not downloading."""
    from nspb_qt.win import doctor

    invalid = tmp_path / "missing.sdk"

    monkeypatch.setenv("NSPB_IOS_SDK", str(invalid))
    monkeypatch.setattr(tc, "sdk_cache_dir", lambda: tmp_path)
    monkeypatch.setattr(
        doctor.shim,
        "build_env",
        lambda: {},
    )

    code = doctor.main(["--no-probe"])
    output = capsys.readouterr().out

    assert code == 1
    assert str(invalid) in output
    assert "Correct NSPB_IOS_SDK" in output
    assert "get an iPhoneOS SDK:" not in output
