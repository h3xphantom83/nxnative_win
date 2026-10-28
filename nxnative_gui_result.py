"""Build-result classification and a compact graphical Qt dialog."""
from pathlib import Path


def classify_result(exit_code: int, crashed: bool, stopped: bool, ipa: str) -> tuple[str, str, str]:
    """Return (kind, title, description) without relying on GUI internals."""
    if stopped:
        return ('cancelled', 'Build stopped', 'The build was stopped before completion.')
    if crashed or exit_code != 0:
        return ('error', 'Build failed', f'The build ended with exit code {exit_code}. Review the build log for details.')
    if not ipa or not Path(ipa).is_file():
        return ('error', 'IPA not found', 'The build reported success, but the output IPA could not be found. Check the build log and destination.')
    return ('success', 'IPA built successfully!', 'Your iOS package is ready.')


def show_result_dialog(parent, kind: str, title: str, description: str, ipa: str = '') -> None:
    """Graphical status popup using built-in Qt icon artwork (no external assets)."""
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import (
        QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
        QStyle, QFrame, QApplication,
    )

    dialog = QDialog(parent)
    dialog.setWindowTitle('nxnative — Build result')
    dialog.setModal(True)
    dialog.setMinimumWidth(390)
    dialog.setMaximumWidth(530)
    dialog.setObjectName('buildResultDialog')

    outer = QVBoxLayout(dialog)
    outer.setContentsMargins(28, 24, 28, 20)
    outer.setSpacing(12)

    symbol = QLabel()
    symbol.setAlignment(Qt.AlignmentFlag.AlignCenter)
    style = QApplication.style()
    icon_type = {
        'success': QStyle.StandardPixmap.SP_DialogApplyButton,
        'error': QStyle.StandardPixmap.SP_MessageBoxCritical,
        'cancelled': QStyle.StandardPixmap.SP_MessageBoxWarning,
    }.get(kind, QStyle.StandardPixmap.SP_MessageBoxInformation)
    symbol.setPixmap(style.standardIcon(icon_type).pixmap(76, 76))
    outer.addWidget(symbol)

    header = QLabel(title)
    header.setAlignment(Qt.AlignmentFlag.AlignCenter)
    header.setWordWrap(True)
    header.setStyleSheet('font-size: 20px; font-weight: 700;')
    outer.addWidget(header)

    detail = QLabel(description)
    detail.setAlignment(Qt.AlignmentFlag.AlignCenter)
    detail.setWordWrap(True)
    outer.addWidget(detail)

    if ipa and kind == 'success':
        path_label = QLabel(ipa)
        path_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        path_label.setWordWrap(True)
        path_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        path_label.setStyleSheet('color: #777; font-size: 11px;')
        outer.addWidget(path_label)

    divider = QFrame()
    divider.setFrameShape(QFrame.Shape.HLine)
    outer.addWidget(divider)
    actions = QHBoxLayout()
    actions.addStretch()
    if kind == 'success' and ipa:
        folder_btn = QPushButton('Open output folder')
        folder_btn.clicked.connect(lambda: _open_folder(ipa))
        actions.addWidget(folder_btn)
    close_btn = QPushButton('OK')
    close_btn.setDefault(True)
    close_btn.clicked.connect(dialog.accept)
    actions.addWidget(close_btn)
    outer.addLayout(actions)
    dialog.exec()


def _open_folder(ipa: str) -> None:
    from PySide6.QtCore import QUrl
    from PySide6.QtGui import QDesktopServices
    QDesktopServices.openUrl(QUrl.fromLocalFile(str(Path(ipa).resolve().parent)))
