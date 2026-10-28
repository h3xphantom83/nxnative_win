#!/usr/bin/env python3
"""Pack a DMROMFS1 image into ROMFSARC v1 shards for the nxnative iOS runtime.

Run: py -3.12 dm/tools/romfs_arc.py <RomFS.img> <new-output-dir> [--shard-mib 200]
The output directory must not exist; failures remove only their temporary output.
"""
from __future__ import annotations

import argparse
import shutil
import struct
from pathlib import Path

IMAGE_HEADER = struct.Struct('<8sQQQ')
IMAGE_ENTRY = struct.Struct('<QQIHBB')
ARC_HEADER = struct.Struct('<8sIIQQQQQQ')
ARC_FILE = struct.Struct('<IIQQII')
ARC_DIR = struct.Struct('<IIII')
ARC_CHILD = struct.Struct('<I')
CHILD_DIR = 0x80000000
CHUNK = 4 * 1024 * 1024


def inventory(src: Path):
    """Return sorted (relative path, byte offset, length) files and directory names."""
    length = src.stat().st_size
    with src.open('rb') as handle:
        raw = handle.read(IMAGE_HEADER.size)
        if len(raw) != IMAGE_HEADER.size:
            raise ValueError('Truncated DMROMFS1 header')
        magic, index_off, index_len, count = IMAGE_HEADER.unpack(raw)
        if (magic != b'DMROMFS1' or count < 1 or count > 0xFFFFFFFF
                or index_off < IMAGE_HEADER.size or index_off > length
                or index_len != length - index_off
                or count > index_len // IMAGE_ENTRY.size):
            raise ValueError('Invalid DMROMFS1 header')
        handle.seek(index_off)
        index = handle.read(index_len)
    entries = [IMAGE_ENTRY.unpack_from(index, k * IMAGE_ENTRY.size) for k in range(count)]
    pool = index[count * IMAGE_ENTRY.size:]
    def name(k):
        _, _, pos, size, _, reserved = entries[k]
        if reserved or pos + size > len(pool):
            raise ValueError(f'Invalid name record {k}')
        raw_name = pool[pos:pos + size]
        if k and (not raw_name or b'/' in raw_name or b'\0' in raw_name or raw_name in (b'.', b'..')):
            raise ValueError(f'Invalid name at entry {k}')
        return raw_name.decode('utf-8')

    if entries[0][4] != 0 or name(0):
        raise ValueError('Invalid root directory')
    files, directories = [], ['']
    visited = set()
    def descend(k, prefix):
        if k in visited:
            raise ValueError('Duplicate or cyclic image entry')
        visited.add(k)
        a, b, _, _, is_file, _ = entries[k]
        if is_file:
            if a < IMAGE_HEADER.size or a + b > index_off:
                raise ValueError(f'File range outside image: {prefix}')
            files.append((prefix, a, b))
            return
        if a > count or b > count - a:
            raise ValueError(f'Invalid directory range: {prefix}')
        previous = None
        for j in range(a, a + b):
            leaf = name(j)
            if previous is not None and leaf <= previous:
                raise ValueError(f'Unsorted directory entries: {prefix}')
            previous = leaf
            rel = f'{prefix}/{leaf}' if prefix else leaf
            if entries[j][4] == 0:
                directories.append(rel)
            elif entries[j][4] != 1:
                raise ValueError(f'Invalid entry type: {rel}')
            descend(j, rel)
    descend(0, '')
    if len(visited) != count:
        raise ValueError('Unreachable image entries')
    files.sort(key=lambda e: e[0].encode('utf-8'))
    directories.sort(key=lambda s: s.encode('utf-8'))
    return files, directories


def _tree_hash(files):
    # Stable FNV-1a identity; the current C reader exposes but does not validate this field.
    value = 0xCBF29CE484222325
    for path, _, size in files:
        for byte in path.encode('utf-8') + b'\0' + struct.pack('<Q', size):
            value = ((value ^ byte) * 0x100000001B3) & 0xFFFFFFFFFFFFFFFF
    return value


def pack(src: Path, destination: Path, shard_mib: int = 200):
    if not 1 <= shard_mib <= 4096:
        raise ValueError('shard_mib must be between 1 and 4096')
    if not src.is_file():
        raise FileNotFoundError(src)
    if destination.exists():
        raise FileExistsError(f'Output already exists (never overwriting): {destination}')
    files, directories = inventory(src)
    limit = shard_mib * 1024 * 1024
    # Build every index table before writing the gigabytes of payload.
    all_names = sorted({*(path for path, _, _ in files), *directories}, key=lambda x: x.encode('utf-8'))
    pool = bytearray()
    offsets = {}
    for path in all_names:
        offsets[path] = len(pool)
        pool.extend(path.encode('utf-8') + b'\0')
    if len(pool) >= 2**32 or len(files) >= CHILD_DIR or len(directories) >= CHILD_DIR:
        raise ValueError('Index exceeds ROMFSARC v1 limits')
    file_index = {path: i for i, (path, _, _) in enumerate(files)}
    dir_index = {path: i for i, path in enumerate(directories)}
    children_of = {path: [] for path in directories}
    for path, _, _ in files:
        parent = path.rpartition('/')[0]
        children_of[parent].append((path.rpartition('/')[2].encode('utf-8'), file_index[path]))
    for path in directories:
        if not path:
            continue
        parent = path.rpartition('/')[0]
        children_of[parent].append((path.rpartition('/')[2].encode('utf-8'), CHILD_DIR | dir_index[path]))
    child_tags = []
    dir_records = []
    for path in directories:
        kids = sorted(children_of[path])
        dir_records.append(ARC_DIR.pack(offsets[path], len(child_tags), len(kids), 0))
        child_tags.extend(tag for _, tag in kids)

    destination.parent.mkdir(parents=True, exist_ok=True)
    temp = destination.with_name(destination.name + '.partial')
    if temp.exists():
        raise FileExistsError(f'Partial output exists; inspect before retrying: {temp}')
    temp.mkdir()
    try:
        records = []
        shard_no, shard_bytes = 0, 0
        shard = (temp / f'romfs.{shard_no:02d}').open('wb')
        try:
            with src.open('rb') as image:
                for path, image_off, file_size in files:
                    if shard_bytes and shard_bytes + file_size > limit:
                        shard.close()
                        shard_no += 1
                        if shard_no >= 256:
                            raise ValueError('More than 256 shards: increase --shard-mib')
                        shard_bytes = 0
                        shard = (temp / f'romfs.{shard_no:02d}').open('wb')
                    records.append(ARC_FILE.pack(offsets[path], shard_no, shard_bytes, file_size, 0o444, 0))
                    image.seek(image_off)
                    remaining = file_size
                    while remaining:
                        data = image.read(min(CHUNK, remaining))
                        if not data:
                            raise IOError(f'Unexpected end of image while reading {path}')
                        shard.write(data)
                        remaining -= len(data)
                    shard_bytes += file_size
        finally:
            shard.close()
        index_size = (ARC_HEADER.size + len(pool) + len(records) * ARC_FILE.size
                      + len(dir_records) * ARC_DIR.size + len(child_tags) * ARC_CHILD.size)
        with (temp / 'romfs.idx').open('wb') as out:
            out.write(ARC_HEADER.pack(b'ROMFSARC', 1, shard_no + 1, index_size,
                                      len(files), len(directories), len(pool), 0,
                                      _tree_hash(files)))
            out.write(pool)
            for rec in records:
                out.write(rec)
            for rec in dir_records:
                out.write(rec)
            for tag in child_tags:
                out.write(ARC_CHILD.pack(tag))
        if (temp / 'romfs.idx').stat().st_size != index_size:
            raise IOError('ROMFSARC index size verification failed')
        temp.rename(destination)
    except BaseException:
        shutil.rmtree(temp)
        raise
    return len(files), len(directories), shard_no + 1


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('image', type=Path, help='DMROMFS1 RomFS.img')
    ap.add_argument('output', type=Path, help='new directory for romfs.idx and romfs.NN')
    ap.add_argument('--shard-mib', type=int, default=200)
    args = ap.parse_args(argv)
    files, dirs, shards = pack(args.image, args.output, args.shard_mib)
    print(f'ROMFSARC complete: {files} files, {dirs} directories, {shards} shards')
    print(f'Output: {args.output}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
