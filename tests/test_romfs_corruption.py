"""Failure-handling regression tests using disposable ROMFS archives."""

import subprocess

import pytest

from test_romfs_integrity import populated, packer, integrity
from test_romfs_driver_integrity import ROOT, romfs


def corrupt_archive(tmp_path):
    image, folder = populated(tmp_path)

    # Record hashes before corruption.
    integrity.save_manifest(folder, integrity.build_manifest(folder))

    # Change exactly one byte without changing the shard length.
    shard = folder / "romfs.00"
    with shard.open("r+b") as handle:
        original = handle.read(1)
        assert original
        handle.seek(0)
        handle.write(bytes([original[0] ^ 0x01]))

    return image, folder


def test_corruption_survives_structural_check(tmp_path):
    image, folder = corrupt_archive(tmp_path)

    valid, detail = romfs.verify_archive(image, folder, packer)

    assert valid, detail

    with pytest.raises(ValueError, match="payload differs"):
        integrity.verify_payload(image, folder, packer)


def test_full_integrity_command_rejects_corruption(tmp_path):
    image, folder = corrupt_archive(tmp_path)

    with pytest.raises(subprocess.CalledProcessError) as error:
        romfs.run_integrity(
            ROOT,
            image,
            folder,
            verify_full=True,
        )

    assert error.value.returncode != 0


def test_finish_build_propagates_corruption_failure(tmp_path, capsys):
    image, folder = corrupt_archive(tmp_path)

    with pytest.raises(subprocess.CalledProcessError):
        romfs.finish_build(
            ROOT,
            ["unused-game-directory", "-o", str(tmp_path / "game.ipa")],
            False,
            folder,
            200,
            image_override=image,
            verify_full=True,
        )

    captured = capsys.readouterr()

    # The integration must not report a successful completion.
    assert "[ROMFSARC] Complete:" not in captured.out
    assert "BUILD COMPLETE" not in captured.out
