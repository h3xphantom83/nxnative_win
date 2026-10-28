"""Windows integration unit tests, runnable without an NSP or iPhone."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / 'frontend-qt/nspb_qt/win/romfs_integration.py'
PACKER = ROOT / 'dm/tools/romfs_arc.py'


def load(path, label):
    spec = importlib.util.spec_from_file_location(label, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_cli_flags():
    mod = load(MODULE, 'romfs_integration_test')
    args, skip, output, shard, image = mod.extract_flags([
        'E:/GameSource', '-k', 'keys', '--romfs-shard-mib=256',
        '--romfs-output', 'E:/Packaged', '--skip-romfs', '-o', 'E:/Game.ipa'
    ])
    assert args == ['E:/GameSource', '-k', 'keys', '-o', 'E:/Game.ipa']
    assert skip and output == Path('E:/Packaged') and shard == 256 and image is None


def test_verify_existing(tmp_path):
    mod = load(MODULE, 'romfs_integration_test2')
    packer = load(PACKER, 'romfs_arc_test')
    from test_romfs_arc import synthetic_image
    source = tmp_path / 'RomFS.img'
    output = tmp_path / 'romfs'
    synthetic_image(source)
    packer.pack(source, output)
    ok, detail = mod.verify_archive(source, output, packer)
    assert ok, detail
    (output / 'romfs.00').unlink()
    assert not mod.verify_archive(source, output, packer)[0]


def test_missing_and_ambiguous_images(tmp_path):
    mod = load(MODULE, 'romfs_integration_test3')
    import pytest
    with pytest.raises(ValueError, match='exactly one'):
        mod.locate_image([str(tmp_path)])
    for version in ('v0', 'v327680'):
        folder = tmp_path / 'ID_build' / 'extract' / version
        folder.mkdir(parents=True)
        (folder / 'RomFS.img').write_bytes(b'mock')
    with pytest.raises(ValueError, match='found 2'):
        mod.locate_image([str(tmp_path)])
