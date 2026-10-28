"""Small synthetic DMROMFS1 -> ROMFSARC compatibility checks."""
import importlib.util
import struct
from pathlib import Path

MOD = Path(__file__).resolve().parents[1] / 'dm' / 'tools' / 'romfs_arc.py'
spec = importlib.util.spec_from_file_location('romfs_arc_generator', MOD)
packer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(packer)


def synthetic_image(path):
    head = struct.Struct('<8sQQQ')
    entry = struct.Struct('<QQIHBB')
    names = b'a.txtbx.dat'
    content = b'helloworld!'
    records = [(1, 2, 0, 0, 0, 0), (head.size, 5, 0, 5, 1, 0),
               (3, 1, 5, 1, 0, 0), (head.size + 5, 6, 6, 5, 1, 0)]
    index = b''.join(entry.pack(*record) for record in records) + names
    path.write_bytes(head.pack(b'DMROMFS1', head.size + len(content), len(index), len(records)) + content + index)


def test_packer_and_reader_tables(tmp_path):
    image = tmp_path / 'RomFS.img'
    target = tmp_path / 'romfs'
    synthetic_image(image)
    assert packer.pack(image, target) == (2, 2, 1)
    index = (target / 'romfs.idx').read_bytes()
    assert index[:8] == b'ROMFSARC'
    magic, version, shards, size, files, dirs, pool_size, reserved, tree_hash = struct.unpack_from('<8sIIQQQQQQ', index)
    assert (version, shards, size, files, dirs) == (1, 1, len(index), 2, 2)
    pool = index[64:64+pool_size]
    file_base = 64 + pool_size
    expected = {'a.txt': b'hello', 'b/x.dat': b'world!'}
    for i in range(files):
        name_off, shard, offset, length, mode, _ = struct.unpack_from('<IIQQII', index, file_base+i*32)
        name = pool[name_off:pool.index(b'\0', name_off)].decode()
        data = (target / f'romfs.{shard:02d}').read_bytes()[offset:offset+length]
        assert data == expected[name]
    dir_base = file_base + files*32
    children_base = dir_base + dirs*16
    root_name, root_first, root_count, _ = struct.unpack_from('<IIII', index, dir_base)
    sub_name, sub_first, sub_count, _ = struct.unpack_from('<IIII', index, dir_base+16)
    assert (root_name, root_count, sub_count) == (0, 2, 1)
    assert root_first == 0 and sub_first == 2
    tags = struct.unpack_from('<III', index, children_base)
    assert tags == (0, packer.CHILD_DIR | 1, 1)
    assert (target / 'romfs.00').read_bytes() == b'helloworld!'


def test_never_overwrites(tmp_path):
    image = tmp_path / 'RomFS.img'
    synthetic_image(image)
    target = tmp_path / 'romfs'
    target.mkdir()
    try:
        packer.pack(image, target)
    except FileExistsError:
        pass
    else:
        assert False, 'existing directory was not protected'
