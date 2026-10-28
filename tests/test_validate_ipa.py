"""Behavioral tests for the Windows IPA validation utility."""

import importlib.util
import plistlib
import struct
import zipfile
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "scripts" / "validate_ipa.py"

spec = importlib.util.spec_from_file_location("validate_ipa_test", SOURCE)
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)

BUNDLE = "org.nxnative.testgame"
VERSION = "1.0"
PREFIX = "Payload/DmIOS.app/"


def make_ipa(
    tmp_path,
    *,
    executable=True,
    cpu=0x0100000C,
    bundle_id=BUNDLE,
    resources=True,
):
    path = tmp_path / "test.ipa"

    info = {
        "CFBundleIdentifier": bundle_id,
        "CFBundleShortVersionString": VERSION,
        "CFBundleExecutable": "DmIOS",
    }

    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_STORED) as z:
        z.writestr(PREFIX + "Info.plist", plistlib.dumps(info))

        if executable:
            header = struct.pack("<III", 0xFEEDFACF, cpu, 0)
            z.writestr(PREFIX + "DmIOS", header + b"TEST_EXECUTABLE")

        if resources:
            for name in validator.REQUIRED_RESOURCES:
                z.writestr(PREFIX + name, b"fixture data")

    return path


def test_valid_arm64_ipa(tmp_path):
    ipa = make_ipa(tmp_path)

    result = validator.validate_ipa(
        ipa, expected_id=BUNDLE, expected_version=VERSION
    )

    assert result["app"] == "DmIOS.app"
    assert result["bundle_id"] == BUNDLE
    assert result["version"] == VERSION


def test_missing_executable(tmp_path):
    ipa = make_ipa(tmp_path, executable=False)

    with pytest.raises(ValueError, match="Executable missing"):
        validator.validate_ipa(ipa)


def test_wrong_bundle_identifier(tmp_path):
    ipa = make_ipa(tmp_path)

    with pytest.raises(ValueError, match="Bundle ID mismatch"):
        validator.validate_ipa(ipa, expected_id="org.nxnative.wrong")


def test_wrong_cpu_architecture(tmp_path):
    ipa = make_ipa(tmp_path, cpu=0x01000007)

    with pytest.raises(ValueError, match="Expected ARM64"):
        validator.validate_ipa(ipa)


def test_missing_required_resources(tmp_path):
    ipa = make_ipa(tmp_path, resources=False)

    with pytest.raises(ValueError, match="Missing required resource"):
        validator.validate_ipa(ipa)


def test_corrupted_zip_payload(tmp_path):
    ipa = make_ipa(tmp_path)

    # Change one byte inside a stored ZIP member without updating its CRC.
    blob = ipa.read_bytes()
    marker = b"TEST_EXECUTABLE"

    assert blob.count(marker) == 1

    position = blob.index(marker)
    corrupted = (
        blob[:position]
        + bytes([blob[position] ^ 1])
        + blob[position + 1:]
    )

    ipa.write_bytes(corrupted)

    with pytest.raises(ValueError, match="ZIP CRC failure"):
        validator.validate_ipa(ipa)
