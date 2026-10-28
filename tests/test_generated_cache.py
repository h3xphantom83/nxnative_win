import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "frontend-qt/nspb_qt/win/build_app.py"


def test_profile_timestamp_preservation_present():
    source = MODULE.read_text(encoding="utf-8")
    assert "previous_profile" in source
    assert "profile_header.read_bytes() == old_bytes" in source
    assert "os.utime(profile_header" in source


def test_embed_timestamp_preservation_present():
    source = MODULE.read_text(encoding="utf-8")
    assert "previous_embed" in source
    assert "es.read_bytes() == old_bytes" in source
    assert "os.utime(es" in source
