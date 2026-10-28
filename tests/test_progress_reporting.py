"""Focused tests for Windows progress messages; no native toolchain required."""
import importlib.util
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / 'frontend-qt' / 'nspb_qt' / 'win' / 'progress_reporting.py'
spec = importlib.util.spec_from_file_location('windows_progress_reporting', SOURCE)
reporter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reporter)


class Lock:
    def __enter__(self): return self
    def __exit__(self, *args): pass


class Watch:
    def __init__(self):
        self.lock = Lock()
        self.state = 'gen'
        self.total = self.most = 99
    def poll(self): return None


class Progress:
    def __init__(self): self.calls = []
    def end(self, text): self.calls.append(('end', text))
    def stage(self, label, **kwargs): self.calls.append(('stage', label))


def test_cached_compilation():
    w, p, original = Watch(), Progress(), []
    delegate = lambda _, line: original.append(line)
    reporter.on_windows_line(w, '[12:00:00] compile: 0 of 181 files (clang, arm64-apple-ios26.0), 181 up to date', delegate, p)
    reporter.on_windows_line(w, '[12:00:01] pack IPA -> output', delegate, p)
    assert p.calls == [('end', '181 objects reused, 0 compiled'), ('stage', 'IPA pack')]
    assert w.state == 'list'
    assert len(original) == 1


def test_fresh_compilation():
    w, p = Watch(), Progress()
    reporter.on_windows_line(w, 'compile: 181 of 181 files', lambda *_: None, p)
    reporter.on_windows_line(w, 'pack IPA', lambda *_: None, p)
    assert p.calls[0] == ('end', '0 objects reused, 181 compiled')


def test_no_counts_uses_upstream():
    w, p, calls = Watch(), Progress(), []
    reporter.on_windows_line(w, 'pack IPA', lambda _, line: calls.append(line), p)
    assert calls == ['pack IPA'] and not p.calls


def test_bad_counts_do_not_replace_summary():
    w, p, calls = Watch(), Progress(), []
    delegate = lambda _, line: calls.append(line)
    reporter.on_windows_line(w, 'compile: 182 of 181 files', delegate, p)
    reporter.on_windows_line(w, 'pack IPA', delegate, p)
    assert not p.calls


def test_completion_summary():
    text = reporter.completed_output('Example.ipa', Path('romfs').resolve(), skipped=False)
    assert 'BUILD COMPLETE' in text and 'ROMFS:' in text and 'Example.ipa' in text
    assert 'skipped' in reporter.completed_output('Example.ipa', None, skipped=True)
