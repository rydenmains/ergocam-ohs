"""
ErgoCam v3.0 — core/camera_worker.py
QThread kamera: baca frame → deteksi → emit sinyal ke UI.

EMA FPS: menghindari label fps jitter akibat per-frame instantaneous.
Windowed frame count: 1-detik sliding window untuk display FPS.
"""

from __future__ import annotations

import sys
import time
from collections import deque

import cv2
import numpy as np
from PySide6.QtCore import QThread, Signal

import config
from core.detector import Detector, DetectionResult


class CameraWorker(QThread):
    # sinyal ke MainWindow
    frame_ready    = Signal(np.ndarray)          # frame BGR untuk ditampilkan
    result_ready   = Signal(DetectionResult)      # hasil deteksi
    fps_updated    = Signal(float)                # EMA fps
    face_lost      = Signal()                     # wajah tidak terdeteksi
    calibrated     = Signal(bool)                 # hasil kalibrasi (True/False)

    def __init__(self, camera_index: int = 0, bg_mode: bool = False, parent=None):
        super().__init__(parent)
        self.camera_index = camera_index
        self.bg_mode      = bg_mode
        self._stop_flag   = False
        self._cal_flag    = False                 # request kalibrasi
        self._detector    = Detector()

        # EMA fps
        self._ema_fps     = 0.0
        self._ema_alpha   = 0.15                  # smoothing factor
        # Windowed frame count (1 detik)
        self._frame_times: deque = deque()

    # ── Public ────────────────────────────────────────────────

    def request_calibrate(self):
        """Dipanggil dari thread lain — set flag, diproses di loop."""
        self._cal_flag = True

    def stop(self):
        self._stop_flag = True
        self.wait()

    # ── QThread.run ───────────────────────────────────────────

    def run(self):
        backend = cv2.CAP_DSHOW if sys.platform == "win32" else 0
        cap = cv2.VideoCapture(self.camera_index, backend)
        if not cap.isOpened():
            return

        cap.set(cv2.CAP_PROP_FRAME_WIDTH,  1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        cap.set(cv2.CAP_PROP_FPS, config.FPS_TARGET)

        target_interval = 1.0 / config.FPS_TARGET
        last_emit_fps   = time.monotonic()

        while not self._stop_flag:
            t0    = time.monotonic()
            ok, frame = cap.read()
            if not ok:
                time.sleep(0.05)
                continue

            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # ── Kalibrasi on-demand ──────────────────────────
            if self._cal_flag:
                self._cal_flag = False
                success = self._detector.calibrate(frame_rgb)
                self.calibrated.emit(success)

            # ── Deteksi ──────────────────────────────────────
            result = self._detector.process(frame_rgb, bg_mode=self.bg_mode)

            # ── Emit frame + result ──────────────────────────
            if not self.bg_mode:
                self.frame_ready.emit(frame)          # kirim BGR asli ke UI
            self.result_ready.emit(result)
            if not result.face_detected:
                self.face_lost.emit()

            # ── FPS windowed ─────────────────────────────────
            now = time.monotonic()
            self._frame_times.append(now)
            # Buang frame > 1 detik lalu
            while self._frame_times and (now - self._frame_times[0]) > 1.0:
                self._frame_times.popleft()
            # Emit tiap 0.5 detik
            if now - last_emit_fps >= 0.5:
                fps_raw  = len(self._frame_times)
                self._ema_fps = (self._ema_alpha * fps_raw
                                 + (1 - self._ema_alpha) * self._ema_fps)
                self.fps_updated.emit(round(self._ema_fps, 1))
                last_emit_fps = now

            # ── Throttle ke FPS target ───────────────────────
            elapsed = time.monotonic() - t0
            sleep   = target_interval - elapsed
            if sleep > 0:
                time.sleep(sleep)

        cap.release()
        self._detector.close()
