import importlib.util
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "frontend-qt/nspb_qt/win/romfs_integration.py"

spec = importlib.util.spec_from_file_location("romfs_integrated_test", MODULE)
romfs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(romfs)


def test_integrity_flags_are_removed():
    args, full, write = romfs.extract_integrity_flags([
        "game", "--romfs-verify-full",
        "--romfs-write-manifest", "-o", "game.ipa",
    ])
    assert args == ["game", "-o", "game.ipa"]
    assert full is True
    assert write is True


def test_integrity_flags_default_off():
    args, full, write = romfs.extract_integrity_flags(["game", "-o", "x"])
    assert args == ["game", "-o", "x"]
    assert full is False
    assert write is False


def test_integrity_existing_manifest(tmp_path):
    repo = tmp_path / "repo"
    folder = tmp_path / "romfs"
    tool = repo / "dm/tools/romfs_integrity.py"
    tool.parent.mkdir(parents=True)
    tool.write_text("# test")
    folder.mkdir()
    (folder / "romfs.sha256.json").write_text("{}")

    with patch.object(romfs.subprocess, "run") as run:
        romfs.run_integrity(
            repo, tmp_path / "RomFS.img", folder,
            verify_full=True,
        )

    cmd = run.call_args.args[0]
    assert "--check-manifest" in cmd
    run.assert_called_once()


def test_integrity_creates_missing_manifest(tmp_path):
    repo = tmp_path / "repo"
    folder = tmp_path / "romfs"
    tool = repo / "dm/tools/romfs_integrity.py"
    tool.parent.mkdir(parents=True)
    tool.write_text("# test")
    folder.mkdir()

    with patch.object(romfs.subprocess, "run") as run:
        romfs.run_integrity(
            repo, tmp_path / "RomFS.img", folder,
            write_manifest=True,
        )

    cmd = run.call_args.args[0]
    assert "--write-manifest" in cmd
    run.assert_called_once()
