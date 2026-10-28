"""Argument construction and validation for the standalone nxnative Windows GUI.

No Qt dependency: this module can be tested without a desktop environment.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class BuildOptions:
    game_folder: str
    keys_file: str
    ipa_file: str
    romfs_image: str = ""
    romfs_output: str = ""
    shard_mib: int = 200
    skip_romfs: bool = False
    verify_romfs_full: bool = False
    write_romfs_manifest: bool = False
    validate_ipa: bool = True
    allow_other_metal: bool = True


def validate(options: BuildOptions, repo: Path, python: Path) -> list[str]:
    errors: list[str] = []
    if not (repo / "scripts" / "build_ipa_windows.py").is_file():
        errors.append(f"Builder missing: {repo / 'scripts' / 'build_ipa_windows.py'}")
    if not python.is_file():
        errors.append(f"Python executable not found: {python}")
    if not Path(options.game_folder).is_dir():
        errors.append("Select a valid game/NSP source folder.")
    if not Path(options.keys_file).is_file():
        errors.append("Select an existing prod.keys file.")
    if not options.ipa_file or Path(options.ipa_file).suffix.lower() != ".ipa":
        errors.append("Select an output filename ending in .ipa.")
    if options.romfs_image and not Path(options.romfs_image).is_file():
        errors.append("Specified RomFS.img does not exist.")
    if not 1 <= options.shard_mib <= 4096:
        errors.append("ROMFS shard size must be between 1 and 4096 MiB.")
    if options.skip_romfs and (options.verify_romfs_full or options.write_romfs_manifest):
        errors.append("ROMFS verification and manifest generation require ROMFS generation/reuse.")
    if options.romfs_output and Path(options.romfs_output).is_file():
        errors.append("ROMFS output must be a directory, not a file.")
    return errors


def build_arguments(options: BuildOptions, repo: Path) -> list[str]:
    """Exact argv for scripts/build_ipa_windows.py, without the Python executable."""
    args = [
        "-u", str(repo / "scripts" / "build_ipa_windows.py"),
        options.game_folder,
        "-k", options.keys_file,
        "--progress", "lines",
        "-o", options.ipa_file,
    ]
    if options.romfs_image:
        args += ["--romfs-image", options.romfs_image]
    if options.romfs_output:
        args += ["--romfs-output", options.romfs_output]
    if options.shard_mib != 200:
        args += ["--romfs-shard-mib", str(options.shard_mib)]
    if options.skip_romfs:
        args.append("--skip-romfs")
    if options.verify_romfs_full:
        args.append("--romfs-verify-full")
    if options.write_romfs_manifest:
        args.append("--romfs-write-manifest")
    if options.validate_ipa:
        args.append("--validate-ipa")
    if options.allow_other_metal:
        args.append("--allow-other-metal")
    return args
