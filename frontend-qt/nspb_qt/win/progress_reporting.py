"""Windows-only progress adaptation for nxnative's Xcode-oriented IpaWatch."""
from __future__ import annotations

import re
from pathlib import Path

_COMPILE = re.compile(r"(?:^|\]\s*)compile:\s*(\d+)\s+of\s+(\d+)\s+files\b")


def compilation_summary(compiled: int, total: int) -> str:
    if not (0 <= compiled <= total):
        raise ValueError('invalid compilation counts')
    return f'{total - compiled:,} objects reused, {compiled:,} compiled'


def on_windows_line(watch, line: str, original_line, progress):
    """Handle Windows compiler messages while preserving the original IPA watcher.

    All lines except the final IPA-pack transition are passed unchanged to the
    upstream watcher. If no Windows compiler count was seen, use upstream logic.
    """
    match = _COMPILE.search(line)
    if match:
        compiled, total = map(int, match.groups())
        if 0 <= compiled <= total:
            watch._windows_compilation_counts = (compiled, total)
    # The upstream watcher ends app build on this exact step; override only its
    # Xcode CompileC-based summary if we have Windows Clang's real counts.
    stripped = re.sub(r'^\[[\d:]+\] ', '', line)
    if stripped.startswith('pack IPA') and hasattr(watch, '_windows_compilation_counts'):
        compiled, total = watch._windows_compilation_counts
        with watch.lock:
            progress.end(compilation_summary(compiled, total))
            watch.state, watch.total, watch.most = 'list', None, 0
            progress.stage('IPA pack', poll=watch.poll, step='listing the files')
        return None
    return original_line(watch, line)


def completed_output(ipa: str | None, romfs: Path | None, *, skipped: bool) -> str:
    lines = ['BUILD COMPLETE']
    if ipa:
        lines.append(f'IPA:   {Path(ipa).resolve()}')
    lines.append('ROMFS: skipped (--skip-romfs)' if skipped else f'ROMFS: {romfs}')
    return '\n'.join(lines)
