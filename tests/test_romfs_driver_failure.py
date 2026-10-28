"""Regression tests for Windows driver ROMFS failure handling."""

from pathlib import Path
from types import SimpleNamespace


def test_driver_returns_failure_without_completion(
    monkeypatch, capsys, tmp_path
):
    import nspb_qt.win.driver as driver
    from nspb_qt.win import romfs_integration, shim

    fake_upstream = SimpleNamespace(cli=lambda args: 0)

    monkeypatch.setattr(driver, "check_cli", lambda args: None)
    monkeypatch.setattr(driver, "repo_dir", lambda: tmp_path)
    monkeypatch.setattr(
        driver, "load_upstream", lambda repo: fake_upstream
    )
    monkeypatch.setattr(driver, "patch", lambda mod, repo: None)

    monkeypatch.setattr(
        shim,
        "build_env",
        lambda **kwargs: dict(__import__("os").environ),
    )

    def fail_integrity(*args, **kwargs):
        raise RuntimeError("Simulated ROMFS SHA256 mismatch")

    monkeypatch.setattr(
        romfs_integration,
        "finish_build",
        fail_integrity,
    )

    image = tmp_path / "RomFS.img"
    image.write_bytes(b"synthetic ROMFS fixture")

    result = driver.main([
        str(tmp_path),
        "-o",
        str(tmp_path / "synthetic.ipa"),
        "--romfs-image",
        str(image),
        "--romfs-verify-full",
    ])

    captured = capsys.readouterr()

    assert result == 1
    assert "[ROMFSARC] ERROR:" in captured.err
    assert "Simulated ROMFS SHA256 mismatch" in captured.err
    assert "BUILD COMPLETE" not in captured.out
    assert "BUILD COMPLETE" not in captured.err
