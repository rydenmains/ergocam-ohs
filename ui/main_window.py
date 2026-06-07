"""
ErgoCam v3.0 - ui/main_window.py
MainWindow PySide6 dengan Apple light design system.

Optimasi UI:
  • dirty-check _set_label → skip setStyleSheet/setText kalau nilai sama
  • self-correcting SESI timer (200ms tick, bukan 1000ms)
  • fixed-width stat value labels → no layout reflow saat teks berganti
"""

from __future__ import annotations

import os
import sys
import time
from typing import Dict, Optional, Tuple

import cv2
import numpy as np
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QFont, QImage, QPixmap
from PySide6.QtWidgets import (
    QApplication, QFrame, QHBoxLayout, QLabel, QMainWindow,
    QPushButton, QSizePolicy, QStackedWidget, QVBoxLayout, QWidget,
)

import config
from core.camera_worker import CameraWorker
from core.detector import DetectionResult
from core.session import Session


# ── Font helper ───────────────────────────────────────────────

def pick_font() -> str:
    """SF Pro → Inter → Segoe UI → system default.
    Harus dipanggil setelah QApplication sudah dibuat.
    """
    try:
        available = [f.lower() for f in QFont.families(QFont.Latin)]
    except Exception:
        return "Segoe UI"
    for name in ("SF Pro Display", "Inter", "Segoe UI", "Helvetica Neue"):
        if name.lower() in available:
            return name
    return "Segoe UI"


# ── QSS ───────────────────────────────────────────────────────

def _build_qss() -> str:
    c = config
    return f"""
/* Base */
QWidget {{
    background: {c.FOG};
    color: {c.INK};
    font-family: "{pick_font() or 'Segoe UI'}";
    font-size: 13px;
}}

/* Card */
QFrame#card {{
    background: {c.SNOW};
    border: 1px solid {c.SILVER};
    border-radius: 12px;
}}

/* Primary button */
QPushButton#primary {{
    background: {c.AZURE};
    color: #ffffff;
    border: none;
    border-radius: 8px;
    padding: 8px 20px;
    font-size: 13px;
    font-weight: 600;
    letter-spacing: -0.2px;
}}
QPushButton#primary:hover  {{ background: {c.AZURE_HV}; }}
QPushButton#primary:pressed {{ background: #005bbf; }}

/* Ghost button */
QPushButton#ghost {{
    background: transparent;
    color: {c.AZURE};
    border: 1.5px solid {c.AZURE};
    border-radius: 8px;
    padding: 7px 18px;
    font-size: 13px;
    font-weight: 500;
}}
QPushButton#ghost:hover  {{ background: rgba(0,113,227,0.06); }}
QPushButton#ghost:pressed {{ background: rgba(0,113,227,0.12); }}

/* Mode card (selector) */
QPushButton#mode_card {{
    background: {c.SNOW};
    color: {c.INK};
    border: 1.5px solid {c.SILVER};
    border-radius: 12px;
    padding: 16px 12px;
    font-size: 14px;
    font-weight: 500;
    text-align: left;
}}
QPushButton#mode_card:hover   {{ background: {c.CARD_HI}; border-color: {c.AZURE}; }}
QPushButton#mode_card:checked {{ background: rgba(0,113,227,0.07); border-color: {c.AZURE}; color: {c.AZURE}; }}

/* Stat label (value) */
QLabel#stat_val {{
    color: {c.INK};
    font-size: 15px;
    font-weight: 700;
}}
QLabel#stat_key {{
    color: #3a3a3c;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.8px;
    text-transform: uppercase;
}}

/* Toast */
QFrame#toast {{
    background: rgba(29,29,31,0.92);
    border-radius: 10px;
    padding: 8px 16px;
}}
QLabel#toast_lbl {{
    color: #ffffff;
    font-size: 13px;
}}

/* Break overlay */
QWidget#break_overlay {{
    background: rgba(29,29,31,0.96);
}}
"""


# ─────────────────────────────────────────────────────────────
# BreakOverlay
# ─────────────────────────────────────────────────────────────

class BreakOverlay(QWidget):
    dismissed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("break_overlay")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, False)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(16)

        title = QLabel("Waktunya Istirahat")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(f"color:#ffffff; font-size:28px; font-weight:700; letter-spacing:-0.5px;")

        self._countdown = QLabel("05:00")
        self._countdown.setAlignment(Qt.AlignCenter)
        self._countdown.setStyleSheet(f"color:{config.AZURE}; font-size:56px; font-weight:300; letter-spacing:-2px;")

        sub = QLabel("Jauh dari layar - regangkan leher & punggung Anda.")
        sub.setAlignment(Qt.AlignCenter)
        sub.setStyleSheet(f"color:#aeaeb2; font-size:14px;")

        self._btn = QPushButton("Lanjutkan")
        self._btn.setObjectName("primary")
        self._btn.setFixedWidth(160)
        self._btn.clicked.connect(self.dismissed)

        for w in (title, self._countdown, sub, self._btn):
            layout.addWidget(w)

        self._remaining = config.BREAK_DURATION_SEC
        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._tick)

    def start_break(self):
        self._remaining = config.BREAK_DURATION_SEC
        self._update_label()
        self._timer.start()
        self.show()
        self.raise_()

    def _tick(self):
        self._remaining -= 1
        if self._remaining <= 0:
            self._timer.stop()
            self.dismissed.emit()
        else:
            self._update_label()

    def _update_label(self):
        m, s = divmod(self._remaining, 60)
        self._countdown.setText(f"{m:02d}:{s:02d}")

    def stop(self):
        self._timer.stop()
        self.hide()


# ─────────────────────────────────────────────────────────────
# MainWindow
# ─────────────────────────────────────────────────────────────

class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("ErgoCam")
        self.setMinimumSize(900, 620)
        self.resize(1040, 680)
        self.setStyleSheet(_build_qss())

        self._worker: Optional[CameraWorker] = None
        self._session: Optional[Session] = None
        self._bg_mode = False

        # Dirty-check cache: label_id → (text, color)
        self._label_cache: Dict[str, Tuple[str, str]] = {}

        # SESI timer - self-correcting 200ms tick
        self._sesi_timer = QTimer(self)
        self._sesi_timer.setInterval(200)
        self._sesi_timer.timeout.connect(self._tick_sesi)

        # Break timer
        self._break_timer = QTimer(self)
        self._break_timer.setInterval(5000)   # cek tiap 5 detik
        self._break_timer.timeout.connect(self._check_break)

        # Toast auto-dismiss
        self._toast_timer = QTimer(self)
        self._toast_timer.setSingleShot(True)
        self._toast_timer.timeout.connect(self._hide_toast)

        self._build_ui()

    # ── Build UI ─────────────────────────────────────────────

    def _build_ui(self):
        root = QWidget()
        self.setCentralWidget(root)
        root_h = QHBoxLayout(root)
        root_h.setContentsMargins(0, 0, 0, 0)
        root_h.setSpacing(0)

        # Sidebar
        sidebar = self._make_sidebar()
        root_h.addWidget(sidebar)

        # Main area (stacked: home / live)
        self._stack = QStackedWidget()
        root_h.addWidget(self._stack, 1)

        self._page_home = self._make_home_page()
        self._page_live = self._make_live_page()
        self._stack.addWidget(self._page_home)
        self._stack.addWidget(self._page_live)

        # Break overlay - full-size child of centralWidget
        self._break_overlay = BreakOverlay(root)
        self._break_overlay.hide()
        self._break_overlay.dismissed.connect(self._end_break)

    def _make_sidebar(self) -> QFrame:
        sb = QFrame()
        sb.setObjectName("card")
        sb.setFixedWidth(200)
        sb.setStyleSheet(f"""
            QFrame#card {{
                background: {config.SNOW};
                border: none;
                border-right: 1px solid {config.SILVER};
                border-radius: 0;
            }}
        """)
        vl = QVBoxLayout(sb)
        vl.setContentsMargins(16, 24, 16, 24)
        vl.setSpacing(4)

        # Logo / title
        title = QLabel("ErgoCam")
        title.setStyleSheet(f"color:{config.INK}; font-size:22px; font-weight:700; letter-spacing:-0.8px; background:transparent; border:none;")
        sub   = QLabel(f"v{config.APP_VER}")
        sub.setStyleSheet(f"color:{config.GRAPHITE}; font-size:11px; background:transparent; border:none;")
        vl.addWidget(title)
        vl.addWidget(sub)
        vl.addSpacing(24)

        # Nav buttons
        self._nav_home = self._nav_btn("Beranda", checked=True)
        self._nav_live = self._nav_btn("Sesi Aktif", checked=False)
        self._nav_home.clicked.connect(lambda: self._goto(0))
        self._nav_live.clicked.connect(lambda: self._goto(1))
        vl.addWidget(self._nav_home)
        vl.addWidget(self._nav_live)

        vl.addStretch()

        # FPS indicator
        self._fps_lbl = QLabel("FPS -")
        self._fps_lbl.setStyleSheet(f"color:{config.GRAPHITE}; font-size:11px; background:transparent;")
        self._fps_lbl.setObjectName("stat_key")
        vl.addWidget(self._fps_lbl)

        return sb

    def _nav_btn(self, text: str, checked: bool = False) -> QPushButton:
        btn = QPushButton(text)
        btn.setCheckable(True)
        btn.setChecked(checked)
        btn.setObjectName("mode_card")
        btn.setFixedHeight(40)
        btn.setStyleSheet(f"""
            QPushButton {{
                text-align: left;
                padding: 8px 14px;
                font-size: 13px;
                font-weight: 500;
                color: {config.INK};
                background: transparent;
                border: none;
                border-radius: 8px;
            }}
            QPushButton:checked {{
                background: rgba(0,113,227,0.10);
                color: {config.AZURE};
                font-weight: 700;
            }}
            QPushButton:hover:!checked {{
                background: {config.CARD_HI};
                color: {config.INK};
            }}
        """)
        return btn

    # ── Home page ─────────────────────────────────────────────

    def _make_home_page(self) -> QWidget:
        page = QWidget()
        vl = QVBoxLayout(page)
        vl.setContentsMargins(40, 40, 40, 40)
        vl.setSpacing(24)

        # Header
        hdr = QLabel("Pilih Mode")
        hdr.setStyleSheet(f"color:{config.INK}; font-size:28px; font-weight:700; letter-spacing:-0.8px;")
        vl.addWidget(hdr)

        desc = QLabel("Pantau postur dan jarak layar secara real-time via webcam.")
        desc.setStyleSheet(f"color:{config.GRAPHITE}; font-size:14px;")
        vl.addWidget(desc)
        vl.addSpacing(8)

        # Mode cards
        row = QHBoxLayout()
        row.setSpacing(16)

        cam_card  = self._mode_card(
            "Mode Kamera",
            "Tampilkan feed kamera live dengan overlay deteksi.",
            primary=True,
        )
        bg_card = self._mode_card(
            "Mode Background",
            "Jalankan di latar belakang - notifikasi sistem saja.",
            primary=False,
        )

        cam_card.mousePressEvent  = lambda e: self._start_session(bg=False)
        bg_card.mousePressEvent   = lambda e: self._start_session(bg=True)

        row.addWidget(cam_card)
        row.addWidget(bg_card)
        vl.addLayout(row)

        vl.addStretch()
        return page

    def _mode_card(self, title: str, desc: str, primary: bool) -> QFrame:
        bg_color    = config.AZURE if primary else config.SNOW
        title_color = "#ffffff"    if primary else config.INK
        desc_color  = "rgba(255,255,255,0.95)" if primary else config.GRAPHITE
        border      = "none"       if primary else f"2px solid {config.SILVER}"

        card = QFrame()
        card.setFixedSize(280, 120)
        card.setCursor(Qt.PointingHandCursor)
        card.setStyleSheet(f"""
            QFrame {{
                background: {bg_color};
                border: {border};
                border-radius: 14px;
            }}
            QFrame:hover {{
                background: {'#0062c7' if primary else '#ececf0'};
                border: {'none' if primary else f'2px solid {config.AZURE}'};
            }}
        """)

        vl = QVBoxLayout(card)
        vl.setContentsMargins(20, 18, 20, 18)
        vl.setSpacing(6)

        t = QLabel(title)
        t.setStyleSheet(f"font-size:15px; font-weight:700; color:{title_color}; background:transparent; border:none;")

        d = QLabel(desc)
        d.setWordWrap(True)
        d.setStyleSheet(f"font-size:12px; color:{desc_color}; background:transparent; border:none;")

        vl.addWidget(t)
        vl.addWidget(d)

        return card

    # ── Live page ─────────────────────────────────────────────

    def _make_live_page(self) -> QWidget:
        page = QWidget()
        vl = QVBoxLayout(page)
        vl.setContentsMargins(24, 24, 24, 24)
        vl.setSpacing(16)

        # Feed
        self._feed_lbl = QLabel()
        self._feed_lbl.setAlignment(Qt.AlignCenter)
        self._feed_lbl.setMinimumSize(640, 360)
        self._feed_lbl.setStyleSheet(f"""
            background: {config.BLACK};
            border-radius: 14px;
            border: 1px solid {config.SILVER};
        """)
        self._feed_lbl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        vl.addWidget(self._feed_lbl)

        # Stats bar
        stats_frame = QFrame()
        stats_frame.setStyleSheet("background: transparent; border: none;")
        stats_h = QHBoxLayout(stats_frame)
        stats_h.setContentsMargins(20, 12, 20, 12)
        stats_h.setSpacing(0)

        self._prox_val, prox_block   = self._stat_block("JARAK",  "-", 124)
        self._slouch_val, sl_block   = self._stat_block("POSTUR", "-", 140)
        self._sesi_val, sesi_block   = self._stat_block("SESI",   "00:00:00", 80)

        for block in (prox_block, sl_block, sesi_block):
            stats_h.addWidget(block, 1)

        vl.addWidget(stats_frame)

        # Control bar
        ctrl = QHBoxLayout()
        ctrl.setSpacing(10)

        self._cal_btn  = QPushButton("Kalibrasi (C)")
        self._cal_btn.setObjectName("ghost")
        self._cal_btn.clicked.connect(self._do_calibrate)

        self._stop_btn = QPushButton("Hentikan Sesi")
        self._stop_btn.setObjectName("primary")
        self._stop_btn.clicked.connect(self._stop_session)

        ctrl.addStretch()
        ctrl.addWidget(self._cal_btn)
        ctrl.addWidget(self._stop_btn)
        vl.addLayout(ctrl)

        # Calibration hint overlay (floating di atas feed)
        self._cal_hint = QFrame(page)
        self._cal_hint.setAttribute(Qt.WA_StyledBackground, True)
        self._cal_hint.setStyleSheet("""
            QFrame {
                background-color: rgba(29,29,31,0.82);
                border-radius: 12px;
            }
        """)
        cal_vl = QVBoxLayout(self._cal_hint)
        cal_vl.setContentsMargins(20, 16, 20, 16)
        cal_vl.setSpacing(6)
        self._cal_hint_title = QLabel("Pastikan bahu terlihat di kamera")
        self._cal_hint_title.setAlignment(Qt.AlignCenter)
        self._cal_hint_title.setStyleSheet("color:#ffffff; font-size:14px; font-weight:600; background:transparent;")
        self._cal_hint_sub = QLabel("Kalibrasi otomatis dalam 3 detik...")
        self._cal_hint_sub.setAlignment(Qt.AlignCenter)
        self._cal_hint_sub.setStyleSheet(f"color:{config.AZURE}; font-size:22px; font-weight:300; background:transparent;")
        cal_vl.addWidget(self._cal_hint_title)
        cal_vl.addWidget(self._cal_hint_sub)
        self._cal_hint.adjustSize()
        self._cal_hint.hide()

        # Toast (floating, parented to page)
        self._toast = QFrame(page)
        self._toast.setAttribute(Qt.WA_StyledBackground, True)
        self._toast.setFixedWidth(300)
        self._toast.hide()
        self._toast.setStyleSheet("""
            QFrame {
                background-color: #1d1d1f;
                border-radius: 10px;
            }
        """)
        toast_h = QHBoxLayout(self._toast)
        toast_h.setContentsMargins(16, 12, 16, 12)
        self._toast_lbl = QLabel()
        self._toast_lbl.setWordWrap(True)
        self._toast_lbl.setStyleSheet("color: #ffffff; font-size: 13px; font-weight: 500; background: transparent;")
        toast_h.addWidget(self._toast_lbl)

        return page

    def _stat_block(self, key: str, val: str, val_width: int):
        frame = QWidget()
        frame.setStyleSheet("background: transparent;")
        vl = QVBoxLayout(frame)
        vl.setContentsMargins(12, 0, 12, 0)
        vl.setSpacing(2)
        vl.setAlignment(Qt.AlignCenter)

        key_lbl = QLabel(key)
        key_lbl.setObjectName("stat_key")
        key_lbl.setAlignment(Qt.AlignCenter)
        key_lbl.setStyleSheet(f"color:#3a3a3c; font-size:11px; font-weight:600; letter-spacing:0.8px; background:transparent;")

        val_lbl = QLabel(val)
        val_lbl.setObjectName("stat_val")
        val_lbl.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        val_lbl.setFixedWidth(val_width)
        val_lbl.setStyleSheet(f"color:{config.INK}; font-size:15px; font-weight:700; background:transparent;")

        vl.addWidget(key_lbl)
        vl.addWidget(val_lbl)
        return val_lbl, frame

    # ── Session control ───────────────────────────────────────

    def _start_session(self, bg: bool):
        self._bg_mode = bg
        self._session = Session()

        self._worker = CameraWorker(bg_mode=bg)
        self._worker.frame_ready.connect(self._on_frame)
        self._worker.result_ready.connect(self._on_result)
        self._worker.fps_updated.connect(self._on_fps)
        self._worker.calibrated.connect(self._on_calibrated)
        self._worker.countdown_tick.connect(self._on_countdown)
        self._worker.start()
        self._show_calibration_hint(3)

        self._label_cache.clear()
        self._sesi_timer.start()
        self._break_timer.start()
        self._goto(1)

        if bg:
            self._feed_lbl.setText("Mode Background Aktif\nApp berjalan di latar belakang.")
            self._feed_lbl.setStyleSheet(self._feed_lbl.styleSheet() +
                                         f"color:{config.GRAPHITE}; font-size:16px;")

    def _stop_session(self):
        self._sesi_timer.stop()
        self._break_timer.stop()
        if self._worker:
            self._worker.stop()
            self._worker = None
        if self._session:
            self._session.write_report()
            self._session = None
        self._break_overlay.stop()
        self._label_cache.clear()
        self._goto(0)

    # ── Calibrate ─────────────────────────────────────────────

    def _do_calibrate(self):
        if self._worker:
            self._worker.request_calibrate()

    def _on_calibrated(self, success: bool):
        if success:
            self._cal_hint.hide()
            self._show_toast("Kalibrasi berhasil - baseline postur diperbarui.")
        else:
            self._show_toast("Kalibrasi gagal - wajah tidak terdeteksi, coba lagi.")

    def _on_countdown(self, remaining: int):
        if remaining == 0:
            self._cal_hint.hide()
            return
        self._show_calibration_hint(remaining)

    def _show_calibration_hint(self, remaining: int):
        if remaining > 0:
            self._cal_hint_sub.setText(f"Kalibrasi otomatis dalam {remaining} detik...")
        self._cal_hint.adjustSize()
        page = self._page_live
        x = (page.width() - self._cal_hint.width()) // 2
        self._cal_hint.move(x, 16)
        self._cal_hint.show()
        self._cal_hint.raise_()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_C:
            self._do_calibrate()
        super().keyPressEvent(event)

    # ── Slots ─────────────────────────────────────────────────

    def _on_frame(self, frame: np.ndarray):
        h, w, ch = frame.shape
        img = QImage(frame.data, w, h, ch * w, QImage.Format_BGR888)
        pix = QPixmap.fromImage(img)
        self._feed_lbl.setPixmap(
            pix.scaled(self._feed_lbl.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        )

    def _on_result(self, result: DetectionResult):
        if self._session:
            self._session.log_event(result.proximity_status, result.slouch_status)

        prox_text  = config.STATUS_TEXT["proximity"].get(result.proximity_status, "-")
        sl_text    = config.STATUS_TEXT["slouch"].get(result.slouch_status, "-")
        prox_color = config.status_color(result.proximity_status)
        sl_color   = config.status_color(result.slouch_status)

        self._set_label(self._prox_val,   "prox",   prox_text, prox_color)
        self._set_label(self._slouch_val, "slouch", sl_text,   sl_color)

    def _on_fps(self, fps: float):
        self._fps_lbl.setText(f"FPS {fps:.0f}")

    def _tick_sesi(self):
        if self._session:
            txt = self._session.elapsed_hms()
            self._set_label(self._sesi_val, "sesi", txt, config.INK)

    def _check_break(self):
        if self._session and self._session.elapsed_sec >= config.BREAK_INTERVAL_SEC:
            self._session.reset()   # reset timer setelah break
            self._break_overlay.setGeometry(self.centralWidget().rect())
            self._break_overlay.start_break()

    def _end_break(self):
        self._break_overlay.stop()
        if self._session:
            self._session.reset()

    # ── Dirty-check label setter ──────────────────────────────

    def _set_label(self, lbl: QLabel, key: str, text: str, color: str):
        cached = self._label_cache.get(key)
        if cached == (text, color):
            return
        self._label_cache[key] = (text, color)
        lbl.setText(text)
        lbl.setStyleSheet(f"color:{color}; font-size:15px; font-weight:700; background:transparent;")

    # ── Toast ─────────────────────────────────────────────────

    def _show_toast(self, msg: str, duration_ms: int = 3000):
        self._toast_lbl.setText(msg)
        self._toast.adjustSize()
        page = self._page_live
        x = (page.width() - self._toast.width()) // 2
        y = page.height() - self._toast.height() - 24
        self._toast.move(x, y)
        self._toast.show()
        self._toast.raise_()
        self._toast_timer.start(duration_ms)

    def _hide_toast(self):
        self._toast.hide()

    # ── Nav ───────────────────────────────────────────────────

    def _goto(self, idx: int):
        self._stack.setCurrentIndex(idx)
        self._nav_home.setChecked(idx == 0)
        self._nav_live.setChecked(idx == 1)

    # ── Close ─────────────────────────────────────────────────

    def closeEvent(self, e):
        self._sesi_timer.stop()
        self._break_timer.stop()
        if self._worker:
            self._worker.stop()
        if self._session:
            try:
                self._session.write_report()
            except Exception as ex:
                print(f"[ErgoCam] Report error: {ex}")
        self._break_overlay.stop()
        e.accept()

    # ── Resize (overlay stays full) ───────────────────────────

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._break_overlay.setGeometry(self.centralWidget().rect())
