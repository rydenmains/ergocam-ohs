"""
ErgoCam v3.0 — main.py
Entry point. QApplication + anti-GC window reference.
"""

import os
import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import QApplication

import config
from ui.main_window import MainWindow, pick_font


def main():
    # Windows taskbar grouping
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(config.APP_ID)
        except Exception:
            pass

    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)

    app = QApplication(sys.argv)
    app.setApplicationName(config.APP_NAME)

    font_name = pick_font()
    if font_name:
        base = QFont(font_name)
        base.setStyleStrategy(QFont.PreferAntialias)
        app.setFont(base)

    if os.path.exists(config.LOGO_ICO):
        app.setWindowIcon(QIcon(config.LOGO_ICO))

    window = MainWindow()   # anti-GC: referensi di scope main()
    if os.path.exists(config.LOGO_ICO):
        window.setWindowIcon(QIcon(config.LOGO_ICO))
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
