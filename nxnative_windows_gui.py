"""Standalone Qt GUI for nxnative_win. Does not change NX2Apple or the builder."""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

try:
    from PySide6.QtCore import QProcess, QProcessEnvironment, QSettings, Qt, QTimer
    from PySide6.QtWidgets import (
        QApplication, QCheckBox, QFileDialog, QFormLayout, QGridLayout,
        QGroupBox, QHBoxLayout, QLabel, QLineEdit, QMainWindow, QMessageBox,
        QPlainTextEdit, QProgressBar, QPushButton, QSpinBox, QTabWidget,
        QVBoxLayout, QWidget,
    )
except ImportError:
    print("PySide6 is required. Install with: python -m pip install PySide6", file=sys.stderr)
    raise SystemExit(2)

from nxnative_gui_core import BuildOptions, build_arguments, validate

from nxnative_gui_paths import find_repo
from nxnative_gui_dependencies import doctor_args, parse_doctor_json, summarize

try:
    REPO = find_repo(module_file=__file__)
except RuntimeError as exc:
    print(f'[GUI] {exc}', file=sys.stderr)
    raise SystemExit(2) from exc

STAGES = re.compile(r"\[(\d+)/(\d+)\]")


def default_if_exists(path: str) -> str:
    return path if Path(path).exists() else ""


class PathSelector(QWidget):
    def __init__(self, kind: str, label: str, parent=None):
        super().__init__(parent)
        self.kind = kind
        self.label = label
        self.edit = QLineEdit()
        self.edit.setClearButtonEnabled(True)
        self.button = QPushButton('Browse…')
        self.button.setFixedWidth(90)
        self.button.clicked.connect(self.browse)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.edit, 1)
        layout.addWidget(self.button)

    def browse(self):
        current = self.edit.text().strip()
        start = current or str(Path.home())
        if self.kind == 'folder':
            selection = QFileDialog.getExistingDirectory(self, self.label, start)
        elif self.kind == 'saveipa':
            selection, _ = QFileDialog.getSaveFileName(
                self, self.label, start, 'iOS App Packages (*.ipa)')
            if selection and not selection.lower().endswith('.ipa'):
                selection += '.ipa'
        else:
            fmt = 'All files (*)'
            if self.kind == 'romfs':
                fmt = 'RomFS images (*.img);;All files (*)'
            selection, _ = QFileDialog.getOpenFileName(self, self.label, start, fmt)
        if selection:
            self.edit.setText(selection)

    def value(self):
        return self.edit.text().strip().strip('"')


class Window(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('nxnative for Windows — IPA Builder')
        self.resize(1040, 760)
        self.settings = QSettings('nxnative_win', 'WindowsIPA_GUI')
        self.process = QProcess(self)
        self.process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self.process.readyReadStandardOutput.connect(self.read_log)
        self.process.finished.connect(self.finished)
        self.process.errorOccurred.connect(self.process_error)
        self.doctor_process = QProcess(self)
        self.doctor_process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self.doctor_process.finished.connect(self.doctor_finished)
        self.doctor_process.errorOccurred.connect(self.doctor_error)
        self.doctor_pending = False
        self.doctor_buffer = bytearray()
        self.stop_requested = False
        self.current_log = ''
        self.make_ui()
        self.restore()
        self.update_controls(False)

    def make_ui(self):
        root = QWidget()
        self.setCentralWidget(root)
        vertical = QVBoxLayout(root)
        vertical.setSpacing(12)
        title = QLabel('nxnative_win  /  Windows IPA Builder')
        title.setStyleSheet('font-size: 21px; font-weight: 700; padding: 3px 0;')
        vertical.addWidget(title)
        subtitle = QLabel('Native ARM64 iOS builds · ROMFSARC packaging · optional integrity checks')
        subtitle.setStyleSheet('color: #888;')
        vertical.addWidget(subtitle)
        outer_layout = vertical
        self.main_tabs = QTabWidget()
        outer_layout.addWidget(self.main_tabs, 1)
        build_tab = QWidget()
        vertical = QVBoxLayout(build_tab)
        vertical.setSpacing(12)
        self.main_tabs.addTab(build_tab, 'Build IPA')

        group = QGroupBox('Build inputs')
        form = QFormLayout(group)
        self.game = PathSelector('folder', 'Select NSP source folder')
        self.keys = PathSelector('file', 'Select prod.keys file')
        self.ipa = PathSelector('saveipa', 'Save IPA as')
        self.image = PathSelector('romfs', 'Select extracted RomFS.img (optional)')
        self.romfs_out = PathSelector('folder', 'Select ROMFS output directory (optional)')
        self.python = PathSelector('file', 'Select Python executable')
        form.addRow('Game / NSP folder', self.game)
        form.addRow('Keys file', self.keys)
        form.addRow('Output IPA', self.ipa)
        form.addRow('RomFS.img (optional)', self.image)
        form.addRow('ROMFS output (optional)', self.romfs_out)
        form.addRow('Python interpreter', self.python)
        vertical.addWidget(group)

        options_group = QGroupBox('Build and verification options')
        opt = QGridLayout(options_group)
        self.allow_metal = QCheckBox('Allow other Metal Developer Tools versions')
        self.allow_metal.setChecked(True)
        self.validate_ipa = QCheckBox('Validate IPA after packaging')
        self.validate_ipa.setChecked(True)
        self.full = QCheckBox('Full ROMFS source + SHA-256 verification')
        self.manifest = QCheckBox('Write SHA-256 manifest if missing')
        self.skip = QCheckBox('Skip ROMFS packaging / verification')
        self.shard = QSpinBox()
        self.shard.setRange(1, 4096)
        self.shard.setValue(200)
        self.shard.setSuffix(' MiB')
        opt.addWidget(self.allow_metal, 0, 0)
        opt.addWidget(self.validate_ipa, 0, 1)
        opt.addWidget(self.full, 1, 0)
        opt.addWidget(self.manifest, 1, 1)
        opt.addWidget(self.skip, 2, 0)
        shardrow = QHBoxLayout()
        shardrow.addWidget(QLabel('ROMFS shard target:'))
        shardrow.addWidget(self.shard)
        shardrow.addStretch()
        opt.addLayout(shardrow, 2, 1)
        self.skip.toggled.connect(self.toggle_romfs_controls)
        vertical.addWidget(options_group)

        action = QHBoxLayout()
        self.start = QPushButton('Build IPA')
        self.start.setMinimumHeight(40)
        self.start.setStyleSheet('font-weight: 700;')
        self.start.clicked.connect(self.run_build)
        self.stop = QPushButton('Stop build')
        self.stop.setMinimumHeight(40)
        self.stop.clicked.connect(self.stop_build)
        self.clear = QPushButton('Clear log')
        self.clear.clicked.connect(lambda: self.log.clear())
        self.open_output = QPushButton('Open output folder')
        self.open_output.clicked.connect(self.open_folder)
        action.addWidget(self.start)
        action.addWidget(self.stop)
        action.addStretch()
        action.addWidget(self.open_output)
        action.addWidget(self.clear)
        vertical.addLayout(action)
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        vertical.addWidget(self.progress)
        self.status = QLabel('Ready')
        vertical.addWidget(self.status)
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(5000)
        self.log.setStyleSheet('font-family: Consolas, "Courier New", monospace; font-size: 11px;')
        vertical.addWidget(self.log, 1)
        self.make_dependencies_tab()
        self.statusBar().showMessage(f'Repository: {REPO}')

    def make_dependencies_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(QLabel(
            'Dependency diagnostics use the existing Windows toolchain doctor. '
            'Checks are read-only and run outside the GUI process.'
        ))
        controls = QHBoxLayout()
        self.doctor_deep = QCheckBox('Deep checks: compile, link and Metal')
        self.doctor_deep.setChecked(False)
        controls.addWidget(self.doctor_deep)
        self.doctor_refresh = QPushButton('Refresh dependencies')
        self.doctor_refresh.clicked.connect(self.refresh_dependencies)
        controls.addWidget(self.doctor_refresh)
        controls.addStretch()
        layout.addLayout(controls)
        self.doctor_summary = QLabel('Not checked')
        layout.addWidget(self.doctor_summary)
        self.doctor_details = QPlainTextEdit()
        self.doctor_details.setReadOnly(True)
        self.doctor_details.setPlaceholderText('Click Refresh dependencies to inspect the build environment.')
        layout.addWidget(self.doctor_details, 1)
        self.main_tabs.addTab(page, 'Dependencies')

    def refresh_dependencies(self):
        if self.doctor_process.state() != QProcess.ProcessState.NotRunning:
            return
        py = Path(self.python.value().strip())
        if not py.is_file():
            self.doctor_summary.setText('Select an existing Python executable in Build IPA first.')
            return
        self.doctor_buffer = bytearray()
        self.doctor_pending = True
        self.doctor_refresh.setEnabled(False)
        self.doctor_summary.setText('Checking dependencies…')
        self.doctor_details.setPlainText('Running Windows toolchain diagnostics…')
        env = QProcessEnvironment.systemEnvironment()
        env.insert('PYTHONIOENCODING', 'utf-8')
        env.insert('PYTHONUTF8', '1')
        frontend = str(REPO / 'frontend-qt')
        previous = env.value('PYTHONPATH', '')
        env.insert('PYTHONPATH', frontend + (os.pathsep + previous if previous else ''))
        self.doctor_process.setProcessEnvironment(env)
        self.doctor_process.setWorkingDirectory(str(REPO))
        self.doctor_process.setProgram(str(py))
        self.doctor_process.setArguments(doctor_args(self.doctor_deep.isChecked()))
        self.doctor_process.start()

    def doctor_error(self, error):
        if error == QProcess.ProcessError.FailedToStart:
            self.doctor_pending = False
            self.doctor_refresh.setEnabled(True)
            self.doctor_summary.setText('Unable to start dependency checker')
            self.doctor_details.setPlainText(self.doctor_process.errorString())

    def doctor_finished(self, code, status):
        self.doctor_buffer.extend(bytes(self.doctor_process.readAllStandardOutput()))
        self.doctor_pending = False
        self.doctor_refresh.setEnabled(True)
        output = self.doctor_buffer.decode('utf-8', errors='replace')
        try:
            rows = parse_doctor_json(output)
        except ValueError as exc:
            self.doctor_summary.setText('Dependency report could not be read')
            self.doctor_details.setPlainText(f'{exc}\n\n{output[:6000]}')
            return
        self.doctor_summary.setText(summarize(rows))
        lines = []
        for row in rows:
            state = row['state'].upper()
            optional = '' if row['required'] else ' (optional)'
            lines.append(f"[{state}] {row['name']}{optional}")
            for key in ('version', 'path', 'detail'):
                value = row[key]
                if value:
                    lines.append(f'  {key}: {value}')
            if row['state'] != 'ok' and row['hint']:
                lines.append(f"  Suggestion: {row['hint']}")
            lines.append('')
        self.doctor_details.setPlainText('\n'.join(lines))
        if code not in (0, 1):
            self.doctor_summary.setText(self.doctor_summary.text() + f' (doctor exit code {code})')

    def toggle_romfs_controls(self, skipped):
        self.full.setEnabled(not skipped)
        self.manifest.setEnabled(not skipped)
        self.shard.setEnabled(not skipped)
        self.romfs_out.setEnabled(not skipped)
        self.image.setEnabled(not skipped)

    def restore(self):
        defaults = {
            'game': r'E:\NXBuild\Luigi3_ColdBuild_Test\GameSource',
            'keys': r'E:\Nintendo Switch\prod.keys',
            'ipa': r'E:\NXBuild\Luigi3_ColdBuild_Test\Luigi3_Complete.ipa',
            'image': r'E:\NXBuild\Luigi3_ColdBuild_Test\GameSource\0100DCA0064A6000_build\extract\v327680\RomFS.img',
            'romfs_out': '',
            'python': r'E:\nxnative_clean_test\.venv\Scripts\python.exe',
        }
        for name, default in defaults.items():
            value = self.settings.value(name, None)
            if value is None:
                value = default if name == 'ipa' else default_if_exists(default)
            getattr(self, name).edit.setText(str(value))
        for field, widget in [('allow_metal',self.allow_metal),('validate_ipa',self.validate_ipa),
                              ('full',self.full),('manifest',self.manifest),('skip',self.skip)]:
            saved = self.settings.value(field, None)
            if saved is not None:
                widget.setChecked(str(saved).lower() in ('true', '1'))
        self.shard.setValue(int(self.settings.value('shard', 200)))
        self.toggle_romfs_controls(self.skip.isChecked())

    def save_settings(self):
        for name in ['game', 'keys', 'ipa', 'image', 'romfs_out', 'python']:
            self.settings.setValue(name, getattr(self, name).value())
        for name in ['allow_metal', 'validate_ipa', 'full', 'manifest', 'skip']:
            self.settings.setValue(name, getattr(self, name).isChecked())
        self.settings.setValue('shard', self.shard.value())

    def options(self):
        return BuildOptions(
            game_folder=self.game.value(), keys_file=self.keys.value(),
            ipa_file=self.ipa.value(), romfs_image=self.image.value(),
            romfs_output=self.romfs_out.value(), shard_mib=self.shard.value(),
            skip_romfs=self.skip.isChecked(), verify_romfs_full=self.full.isChecked(),
            write_romfs_manifest=self.manifest.isChecked(),
            validate_ipa=self.validate_ipa.isChecked(), allow_other_metal=self.allow_metal.isChecked(),
        )

    def update_controls(self, running):
        self.start.setEnabled(not running)
        self.stop.setEnabled(running)
        for widget in [self.game, self.keys, self.ipa, self.image, self.romfs_out, self.python,
                       self.allow_metal, self.validate_ipa, self.full, self.manifest, self.skip, self.shard]:
            widget.setEnabled(not running)
        if not running:
            self.toggle_romfs_controls(self.skip.isChecked())

    def run_build(self):
        opts = self.options()
        py = Path(self.python.value())
        errors = validate(opts, REPO, py)
        if errors:
            QMessageBox.warning(self, 'Check build settings', '\n'.join(errors))
            return
        self.save_settings()
        self.stop_requested = False
        self.progress.setValue(0)
        self.log.clear()
        argv = build_arguments(opts, REPO)
        # For safety, do not print the keys-file argument or its path in logs.
        self.append_log(f'[GUI] Starting Windows build with Python: {py}')
        self.append_log(f'[GUI] IPA destination: {opts.ipa_file}')
        self.append_log('[GUI] Extra checks: IPA={} ROMFS-full={} manifest={}'.format(
            opts.validate_ipa, opts.verify_romfs_full, opts.write_romfs_manifest))
        self.update_controls(True)
        self.status.setText('Building…')
        self.process.setWorkingDirectory(str(REPO))

        # Force UTF-8 for the child Python build process.
        # Prevents UnicodeEncodeError on Windows cp1252 consoles.
        env = QProcessEnvironment.systemEnvironment()
        env.insert('PYTHONIOENCODING', 'utf-8')
        env.insert('PYTHONUTF8', '1')
        self.process.setProcessEnvironment(env)

        self.process.setProgram(str(py))
        self.process.setArguments(argv)
        self.process.start()
        if not self.process.waitForStarted(4000):
            self.append_log('[GUI] Failed to launch Python: ' + self.process.errorString())
            self.status.setText('Failed to start')
            self.update_controls(False)

    def append_log(self, line):
        self.log.appendPlainText(line.rstrip('\r\n'))
        match = STAGES.search(line)
        if match:
            current, total = map(int, match.groups())
            if total > 0:
                self.progress.setValue(min(95, round(current / total * 95)))
        if 'BUILD COMPLETE' in line:
            self.progress.setValue(100)

    def read_log(self):
        raw = bytes(self.process.readAllStandardOutput())
        if not raw:
            return
        self.current_log += raw.decode('utf-8', errors='replace').replace('\r\n', '\n')
        while '\n' in self.current_log:
            line, self.current_log = self.current_log.split('\n', 1)
            self.append_log(line)

    def finished(self, code, status):
        self.read_log()
        if self.current_log:
            self.append_log(self.current_log)
            self.current_log = ''
        if self.stop_requested:
            self.status.setText('Build stopped')
            self.append_log('[GUI] Build stopped by user')
        elif code == 0 and status == QProcess.ExitStatus.NormalExit:
            self.progress.setValue(100)
            self.status.setText('Build completed successfully')
            self.append_log('[GUI] Python exited successfully (exit code 0)')
        else:
            self.status.setText(f'Build failed (exit code {code})')
            self.append_log(f'[GUI] Build failed: exit code {code}; status {status}')
        self.update_controls(False)

    def process_error(self, error):
        if error != QProcess.ProcessError.FailedToStart:
            self.append_log('[GUI] Process error: ' + self.process.errorString())

    def stop_build(self):
        if self.process.state() == QProcess.ProcessState.NotRunning:
            return
        if QMessageBox.question(self, 'Stop the build?',
                                'Stop the running build process? Partial output may remain on disk.') != QMessageBox.StandardButton.Yes:
            return
        self.stop_requested = True
        self.status.setText('Stopping build…')
        self.process.terminate()
        QTimer.singleShot(2500, self.kill_if_running)

    def kill_if_running(self):
        if self.stop_requested and self.process.state() != QProcess.ProcessState.NotRunning:
            self.process.kill()

    def open_folder(self):
        folder = Path(self.ipa.value()).parent
        if not folder.exists():
            QMessageBox.information(self, 'Output folder', 'The output directory does not exist yet.')
            return
        if os.name == 'nt':
            os.startfile(str(folder))
        else:
            QMessageBox.information(self, 'Output folder', str(folder))

    def closeEvent(self, event):
        if self.process.state() != QProcess.ProcessState.NotRunning:
            QMessageBox.warning(self, 'Build active', 'Stop the build before closing this window.')
            event.ignore()
            return
        self.save_settings()
        event.accept()


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    window = Window()
    window.show()
    return app.exec()


if __name__ == '__main__':
    raise SystemExit(main())
