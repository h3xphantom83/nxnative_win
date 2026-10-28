#!/usr/bin/env python3
"""Verify ROMFSARC payload against DMROMFS1 and optionally create/check SHA256 manifest.

Usage: python romfs_integrity.py SOURCE.img ARCHIVE_DIR [--write-manifest]
       python romfs_integrity.py SOURCE.img ARCHIVE_DIR --check-manifest
The manifest is an optional sidecar; iOS only needs romfs.idx and numbered shards.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import struct

HDR = struct.Struct('<8sIIQQQQQQ')
FILE = struct.Struct('<IIQQII')
CHUNK = 4 * 1024 * 1024
MANIFEST = 'romfs.sha256.json'


def packer_module(repo: Path):
    path = repo / 'dm' / 'tools' / 'romfs_arc.py'
    spec = importlib.util.spec_from_file_location('romfs_arc_for_integrity', path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def hash_file(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(CHUNK), b''):
            h.update(block)
    return h.hexdigest()


def verify_payload(image: Path, folder: Path, packer) -> tuple[int, int]:
    """Compare every archived byte to the original source; reject malformed index/extent."""
    files, dirs = packer.inventory(image)
    data = (folder / 'romfs.idx').read_bytes()
    if len(data) < HDR.size:
        raise ValueError('Index too short')
    magic, ver, shards, length, nfiles, ndirs, pool_size, _, tree_hash = HDR.unpack_from(data)
    if (magic != b'ROMFSARC' or ver != 1 or not 1 <= shards <= 256
            or length != len(data) or nfiles != len(files) or ndirs != len(dirs)
            or tree_hash != packer._tree_hash(files)):
        raise ValueError('ROMFSARC header or source tree mismatch')
    start = HDR.size + pool_size
    end = start + nfiles * FILE.size
    if start > len(data) or end + ndirs * 16 > len(data):
        raise ValueError('Truncated index tables')
    pool = data[HDR.size:start]
    paths = [folder / f'romfs.{i:02d}' for i in range(shards)]
    sizes = [p.stat().st_size for p in paths]
    handles = {}
    try:
        with image.open('rb') as original:
            for i, (expected_name, img_off, expected_size) in enumerate(files):
                name_off, shard, offset, size, _, _ = FILE.unpack_from(data, start + i * FILE.size)
                if name_off >= len(pool) or b'\0' not in pool[name_off:]:
                    raise ValueError(f'Invalid path offset in file record {i}')
                name = pool[name_off:pool.index(b'\0', name_off)].decode('utf-8')
                if name != expected_name or size != expected_size:
                    raise ValueError(f'File mismatch: {expected_name}')
                if shard >= shards or offset > sizes[shard] or size > sizes[shard] - offset:
                    raise ValueError(f'Invalid shard extent: {expected_name}')
                if shard not in handles:
                    handles[shard] = paths[shard].open('rb')
                archived = handles[shard]
                original.seek(img_off)
                archived.seek(offset)
                remaining = size
                while remaining:
                    n = min(CHUNK, remaining)
                    a = original.read(n)
                    b = archived.read(n)
                    if len(a) != n or a != b:
                        raise ValueError(f'ROMFS payload differs: {expected_name} (shard {shard})')
                    remaining -= n
    finally:
        for handle in handles.values():
            handle.close()
    return len(files), shards


def build_manifest(folder):
    idx = folder / 'romfs.idx'
    blob = idx.read_bytes()
    if len(blob) < HDR.size:
        raise ValueError('ROMFSARC index truncated')
    magic, ver, shards, *unused = HDR.unpack_from(blob)
    if magic != b'ROMFSARC' or ver != 1 or not 1 <= shards <= 256:
        raise ValueError('Invalid ROMFSARC index')
    paths = [idx] + [folder / f'romfs.{i:02d}' for i in range(shards)]
    return {'format': 'ROMFSARC-SHA256', 'version': 1,
            'files': {p.name: {'bytes': p.stat().st_size, 'sha256': hash_file(p)} for p in paths}}


def save_manifest(folder, manifest):
    path = folder / MANIFEST
    if path.exists():
        raise FileExistsError(f'Manifest already exists: {path}')
    tmp = folder / (MANIFEST + '.partial')
    with tmp.open('x', encoding='utf-8', newline='\n') as f:
        json.dump(manifest, f, indent=2, sort_keys=True)
        f.write('\n')
    os.replace(tmp, path)


def check_manifest(folder):
    path = folder / MANIFEST
    doc = json.loads(path.read_text(encoding='utf-8'))
    if doc.get('format') != 'ROMFSARC-SHA256' or doc.get('version') != 1:
        raise ValueError('Unsupported manifest format')
    expected = doc.get('files')
    if not isinstance(expected, dict):
        raise ValueError('Invalid manifest file list')
    actual = build_manifest(folder)
    if expected != actual['files']:
        raise ValueError('ROMFSARC SHA256 manifest mismatch: archive content changed')
    return len(expected)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('image', type=Path)
    ap.add_argument('folder', type=Path)
    options = ap.add_mutually_exclusive_group()
    options.add_argument('--write-manifest', action='store_true', help='After source verification, hash shards and write optional SHA256 sidecar')
    options.add_argument('--check-manifest', action='store_true', help='Check existing SHA256 sidecar (also compare to source)')
    args = ap.parse_args(argv)
    repo = Path(__file__).resolve().parents[2]
    packer = packer_module(repo)
    files, shards = verify_payload(args.image, args.folder, packer)
    print(f'[ROMFSARC] Source byte comparison PASS: {files} files, {shards} shards', flush=True)
    if args.write_manifest:
        save_manifest(args.folder, build_manifest(args.folder))
        print(f'[ROMFSARC] SHA256 manifest written: {args.folder / MANIFEST}', flush=True)
    if args.check_manifest:
        count = check_manifest(args.folder)
        print(f'[ROMFSARC] SHA256 manifest PASS: {count} archive files', flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
