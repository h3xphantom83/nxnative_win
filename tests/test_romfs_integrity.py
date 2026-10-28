"""Behavioral checks of ROMFSARC source comparison and SHA256 sidecar."""
import importlib.util
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]

def load(file, name):
    spec = importlib.util.spec_from_file_location(name, file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

integrity = load(ROOT / 'dm/tools/romfs_integrity.py', 'romfs_integrity_test')
packer = load(ROOT / 'dm/tools/romfs_arc.py', 'romfs_arc_integrity_test')
from test_romfs_arc import synthetic_image


def populated(tmp_path):
    image = tmp_path / 'RomFS.img'
    output = tmp_path / 'romfs'
    synthetic_image(image)
    packer.pack(image, output)
    return image, output


def test_verified_payload_and_manifest(tmp_path):
    image, folder = populated(tmp_path)
    assert integrity.verify_payload(image, folder, packer) == (2, 1)
    integrity.save_manifest(folder, integrity.build_manifest(folder))
    assert integrity.check_manifest(folder) == 2


def test_detect_same_size_corruption(tmp_path):
    image, folder = populated(tmp_path)
    integrity.save_manifest(folder, integrity.build_manifest(folder))
    shard = folder / 'romfs.00'
    data = bytearray(shard.read_bytes())
    data[0] ^= 0x01
    shard.write_bytes(data)
    with pytest.raises(ValueError, match='payload differs'):
        integrity.verify_payload(image, folder, packer)
    with pytest.raises(ValueError, match='SHA256 manifest mismatch'):
        integrity.check_manifest(folder)


def test_no_manifest_overwrite(tmp_path):
    image, folder = populated(tmp_path)
    integrity.save_manifest(folder, integrity.build_manifest(folder))
    with pytest.raises(FileExistsError):
        integrity.save_manifest(folder, integrity.build_manifest(folder))
