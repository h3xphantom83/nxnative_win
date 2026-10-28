"""Windows-only ROMFSARC integration for the successful nxnative IPA build."""
from __future__ import annotations

import importlib.util
import struct
from pathlib import Path

HEADER = struct.Struct('<8sIIQQQQQQ')
FILEREC = struct.Struct('<IIQQII')
DIRREC = struct.Struct('<IIII')


def extract_flags(argv):
    """Remove our three Windows-only flags before upstream parses its arguments."""
    args = []
    skip, output, shard_mib, image = False, None, 200, None
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == '--skip-romfs':
            skip = True
        elif arg in ('--romfs-output', '--romfs-shard-mib', '--romfs-image') or any(
            arg.startswith(name + '=') for name in ('--romfs-output', '--romfs-shard-mib', '--romfs-image')
        ):
            name, eq, val = arg.partition('=')
            if not eq:
                i += 1
                if i >= len(argv):
                    raise ValueError(f'{name} needs a value')
                val = argv[i]
            if name == '--romfs-output':
                output = Path(val)
            elif name == '--romfs-image':
                image = Path(val)
            else:
                shard_mib = int(val)
                if not 1 <= shard_mib <= 4096:
                    raise ValueError('--romfs-shard-mib must be 1..4096')
        else:
            args.append(arg)
        i += 1
    return args, skip, output, shard_mib, image


def get_option(args, name):
    for i, arg in enumerate(args):
        if arg == name:
            return args[i + 1] if i + 1 < len(args) else None
        if arg.startswith(name + '='):
            return arg.split('=', 1)[1]
    return None


def locate_image(args):
    """Use upstream's <NSP folder>/<title_id>_build/extract/v*/RomFS.img layout.

    Refuse ambiguity rather than silently packaging a different title/version.
    """
    positional = args[0] if args and not args[0].startswith('-') else None
    if not positional:
        raise ValueError('Cannot determine NSP folder from build arguments')
    nsp_dir = Path(positional).resolve()
    choices = sorted(nsp_dir.glob('*_build/extract/v*/RomFS.img'))
    if len(choices) != 1:
        raise ValueError(
            f'Expected exactly one extracted RomFS image under {nsp_dir}; found {len(choices)}. '
            'Use --skip-romfs for now, or remove irrelevant build caches; '
            'automatic selection must not guess a game/update version.'
        )
    return choices[0]


def read_packer(repo):
    path = repo / 'dm' / 'tools' / 'romfs_arc.py'
    if not path.is_file():
        raise FileNotFoundError(f'ROMFSARC packer is missing: {path}')
    spec = importlib.util.spec_from_file_location('nxnative_romfs_arc_packer', path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def verify_archive(image, folder, packer):
    """Verify index, files, shard extents, and source tree identity (not byte hashes)."""
    idx = folder / 'romfs.idx'
    if not idx.is_file():
        return False, 'romfs.idx missing'
    try:
        b = idx.read_bytes()
        if len(b) < HEADER.size:
            return False, 'index truncated'
        magic, version, shards, length, nfiles, ndirs, pool_size, _, tree_hash = HEADER.unpack_from(b)
        if magic != b'ROMFSARC' or version != 1 or not 1 <= shards <= 256 or length != len(b):
            return False, 'invalid header'
        files, dirs = packer.inventory(image)
        if (nfiles, ndirs, tree_hash) != (len(files), len(dirs), packer._tree_hash(files)):
            return False, 'source tree identity mismatch'
        file_base = HEADER.size + pool_size
        dir_base = file_base + nfiles * FILEREC.size
        children_base = dir_base + ndirs * DIRREC.size
        if children_base > len(b):
            return False, 'index tables exceed file length'
        pool = b[HEADER.size:file_base]
        if len(pool) != pool_size:
            return False, 'name pool truncated'
        sizes = []
        for i in range(shards):
            path = folder / f'romfs.{i:02d}'
            if not path.is_file():
                return False, f'missing {path.name}'
            sizes.append(path.stat().st_size)
        for i, (expected_path, _, expected_size) in enumerate(files):
            name_off, shard, offset, size, _, _ = FILEREC.unpack_from(b, file_base + i * FILEREC.size)
            if name_off >= len(pool) or b'\0' not in pool[name_off:]:
                return False, f'invalid filename at {i}'
            path = pool[name_off:pool.index(b'\0', name_off)].decode('utf-8')
            if (path, size) != (expected_path, expected_size):
                return False, f'file table mismatch at {i}'
            if shard >= shards or offset > sizes[shard] or size > sizes[shard] - offset:
                return False, f'invalid shard extent at {i}'
        for i, expected_path in enumerate(dirs):
            name_off, first_child, count, _ = DIRREC.unpack_from(b, dir_base + i * DIRREC.size)
            if name_off >= len(pool) or b'\0' not in pool[name_off:]:
                return False, f'invalid directory name at {i}'
            actual = pool[name_off:pool.index(b'\0', name_off)].decode('utf-8')
            if actual != expected_path or children_base + 4 * (first_child + count) > len(b):
                return False, f'directory entry mismatch at {i}'
        return True, f'{nfiles} files, {ndirs} directories, {shards} shards'
    except (OSError, ValueError, UnicodeError, struct.error) as error:
        return False, str(error)


def finish_build(repo, args, skip, output, shard_mib, image_override=None):
    if skip:
        print('[ROMFSARC] Skipped (--skip-romfs)')
        return 0
    image = image_override.resolve() if image_override is not None else locate_image(args)
    if not image.is_file():
        raise FileNotFoundError(f'RomFS image not found: {image}')
    ipa = get_option(args, '-o')
    if output is None:
        if not ipa:
            raise ValueError('Cannot determine ROMFS output: pass -o or --romfs-output')
        output = Path(ipa).resolve().parent / 'romfs'
    packer = read_packer(repo)
    if output.exists():
        valid, detail = verify_archive(image, output, packer)
        if not valid:
            raise RuntimeError(f'Existing ROMFS output is not reusable: {output}: {detail}. '
                               'Do not overwrite it; specify a new --romfs-output directory.')
        print(f'[ROMFSARC] Reusing verified {output} ({detail})')
        return 0
    print(f'[ROMFSARC] Packing {image} -> {output}', flush=True)
    packer.pack(image, output, shard_mib)
    valid, detail = verify_archive(image, output, packer)
    if not valid:
        raise RuntimeError(f'Generated ROMFS archive failed verification: {detail}')
    print(f'[ROMFSARC] Complete: {output} ({detail})', flush=True)
    return 0
