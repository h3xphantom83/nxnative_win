"""Validate the structure and metadata of an nxnative iOS IPA."""

import argparse
import plistlib
import struct
import sys
import zipfile
from pathlib import Path


REQUIRED_RESOURCES = (
    "dm/launcher.json",
    "dm/shader_map.tsv",
    "dm/pso_manifest.tsv",
)


def validate_ipa(path, expected_id=None, expected_version=None):
    errors = []

    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        name_set = set(names)

        if len(names) != len(name_set):
            errors.append("Duplicate ZIP entry names")

        apps = {
            name.split("/")[1]
            for name in names
            if name.startswith("Payload/")
            and len(name.split("/")) >= 3
            and name.split("/")[1].endswith(".app")
        }

        if len(apps) != 1:
            raise ValueError(
                f"Expected exactly one application bundle; found {len(apps)}"
            )

        app = next(iter(apps))
        prefix = f"Payload/{app}/"

        plist_path = prefix + "Info.plist"

        if plist_path not in name_set:
            raise ValueError("Info.plist is missing")

        info = plistlib.loads(archive.read(plist_path))

        bundle_id = info.get("CFBundleIdentifier")
        version = info.get("CFBundleShortVersionString")
        executable = info.get("CFBundleExecutable")

        if not isinstance(bundle_id, str) or not bundle_id:
            errors.append("Invalid bundle identifier")

        if not isinstance(version, str) or not version:
            errors.append("Invalid application version")

        if not isinstance(executable, str) or not executable:
            errors.append("Missing CFBundleExecutable")
        else:
            executable_path = prefix + executable

            if executable_path not in name_set:
                errors.append("Executable missing from IPA")
            else:
                try:
                    with archive.open(executable_path) as stream:
                        header = stream.read(12)
                except zipfile.BadZipFile as exc:
                    raise ValueError(
                        f"ZIP CRC failure: {executable_path}: {exc}"
                    ) from exc

                if len(header) < 12:
                    errors.append("Truncated Mach-O header")
                else:
                    magic, cpu, subtype = struct.unpack("<III", header)

                    if magic != 0xFEEDFACF:
                        errors.append("Executable is not 64-bit Mach-O")

                    if cpu != 0x0100000C:
                        errors.append(
                            f"Expected ARM64 Mach-O, found CPU 0x{cpu:08x}"
                        )

        for resource in REQUIRED_RESOURCES:
            if prefix + resource not in name_set:
                errors.append(f"Missing required resource: {resource}")

        if expected_id and bundle_id != expected_id:
            errors.append(
                f"Bundle ID mismatch: {bundle_id} != {expected_id}"
            )

        if expected_version and version != expected_version:
            errors.append(
                f"Version mismatch: {version} != {expected_version}"
            )

        # Check CRCs and decompression for all archived files.
        corrupt = archive.testzip()
        if corrupt:
            errors.append(f"ZIP CRC failure: {corrupt}")

    if errors:
        raise ValueError("; ".join(errors))

    return {
        "app": app,
        "bundle_id": bundle_id,
        "version": version,
        "executable": executable,
        "entries": len(names),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ipa", type=Path)
    parser.add_argument("--bundle-id")
    parser.add_argument("--version")
    args = parser.parse_args(argv)

    try:
        result = validate_ipa(
            args.ipa,
            expected_id=args.bundle_id,
            expected_version=args.version,
        )
    except (OSError, ValueError, zipfile.BadZipFile, plistlib.InvalidFileException) as exc:
        print(f"[IPA] FAIL: {exc}", file=sys.stderr)
        return 1

    print(f"[IPA] PASS: {result['app']}")
    print(f"[IPA] Bundle: {result['bundle_id']}")
    print(f"[IPA] Version: {result['version']}")
    print(f"[IPA] Executable: {result['executable']} (ARM64 Mach-O)")
    print(f"[IPA] ZIP entries verified: {result['entries']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
