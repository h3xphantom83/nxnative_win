from pathlib import Path
from nxnative_gui_core import BuildOptions, build_arguments


def test_gui_no_old_romfs_ui_fields():
    source = Path(__file__).resolve().parents[1].joinpath('nxnative_windows_gui.py').read_text(encoding='utf-8')
    assert "self.image = PathSelector('romfs'" not in source
    assert "self.romfs_out = PathSelector" not in source
    assert "romfs_image=self.image.value()" not in source
    assert "romfs_output=self.romfs_out.value()" not in source


def test_default_gui_has_no_manual_romfs_override():
    opts = BuildOptions(game_folder=r'E:\Nintendo Switch\MK8', keys_file=r'E:\keys', ipa_file=r'E:\out\MK8.ipa')
    args = build_arguments(opts, Path(r'E:\nxnative_win'))
    assert '--romfs-image' not in args
    assert '--romfs-output' not in args
    assert '-o' in args


def test_windows_backend_keeps_automatic_romfs_destination():
    text = (Path(__file__).resolve().parents[1] / 'frontend-qt/nspb_qt/win/romfs_integration.py').read_text(encoding='utf-8')
    assert "output = Path(ipa).resolve().parent / 'romfs'" in text
