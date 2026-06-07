"""
ErgoCam v3.0 — core/detector.py
Detektor postur & jarak berbasis MediaPipe FaceLandmarker (Tasks API).
Kompatibel dengan mediapipe >= 0.10.30 (mp.solutions dihapus).

Model di-download otomatis saat pertama kali Detector() dibuat.
"""

from __future__ import annotations

import math
import os
import urllib.request
from dataclasses import dataclass
from typing import Optional

import mediapipe as mp
import numpy as np

import config

# ── Landmark indices (MediaPipe FaceMesh canonical 468-pt) ───
_IDX_CHIN  = 152
_IDX_BROW  = 10
_IDX_L_OUT = 263
_IDX_R_OUT = 33

# ── Model ─────────────────────────────────────────────────────
_MODEL_URL  = (
    "https://storage.googleapis.com/mediapipe-models/"
    "face_landmarker/face_landmarker/float16/latest/face_landmarker.task"
)
_MODEL_PATH = os.path.join(config.BASE_DIR, "face_landmarker.task")


def _ensure_model():
    if not os.path.exists(_MODEL_PATH):
        print("[ErgoCam] Downloading face_landmarker.task (~3.7 MB)...")
        urllib.request.urlretrieve(_MODEL_URL, _MODEL_PATH)
        print("[ErgoCam] Model downloaded.")


@dataclass
class DetectionResult:
    proximity_status:  str   = "idle"
    slouch_status:     str   = "idle"
    eye_distance_px:   float = 0.0
    foreshorten_ratio: float = 0.0
    face_detected:     bool  = False


class Detector:
    """FaceLandmarker wrapper. Thread-safe untuk QThread."""

    def __init__(self):
        _ensure_model()

        from mediapipe.tasks import python as mp_tasks
        from mediapipe.tasks.python import vision as mp_vision

        base_opts = mp_tasks.BaseOptions(model_asset_path=_MODEL_PATH)
        opts = mp_vision.FaceLandmarkerOptions(
            base_options=base_opts,
            output_face_blendshapes=False,
            output_facial_transformation_matrixes=False,
            num_faces=1,
            min_face_detection_confidence=0.5,
            min_face_presence_confidence=0.5,
            min_tracking_confidence=0.5,
            running_mode=mp_vision.RunningMode.IMAGE,
        )
        self._landmarker = mp_vision.FaceLandmarker.create_from_options(opts)
        self.baseline_ratio: Optional[float] = None

    # ── Public ────────────────────────────────────────────────

    def process(self, frame_rgb: np.ndarray, bg_mode: bool = False) -> DetectionResult:
        res = DetectionResult()
        mp_image = self._to_mp_image(frame_rgb)
        detection = self._landmarker.detect(mp_image)

        if not detection.face_landmarks:
            return res

        lm = detection.face_landmarks[0]
        h, w = frame_rgb.shape[:2]
        res.face_detected = True

        # Proximity
        lx, ly = lm[_IDX_L_OUT].x * w, lm[_IDX_L_OUT].y * h
        rx, ry = lm[_IDX_R_OUT].x * w, lm[_IDX_R_OUT].y * h
        eye_dist = math.hypot(lx - rx, ly - ry)
        res.eye_distance_px = eye_dist
        res.proximity_status = self._prox_tier(eye_dist)

        # Slouch (face foreshortening ratio)
        chin_y = lm[_IDX_CHIN].y * h
        brow_y = lm[_IDX_BROW].y * h
        ratio  = abs(chin_y - brow_y) / max(eye_dist, 1.0)
        res.foreshorten_ratio = ratio
        res.slouch_status = self._slouch_tier(ratio, bg_mode)

        return res

    def calibrate(self, frame_rgb: np.ndarray) -> bool:
        mp_image = self._to_mp_image(frame_rgb)
        detection = self._landmarker.detect(mp_image)
        if not detection.face_landmarks:
            return False
        lm = detection.face_landmarks[0]
        h, w = frame_rgb.shape[:2]
        chin_y = lm[_IDX_CHIN].y * h
        brow_y = lm[_IDX_BROW].y * h
        lx, ly = lm[_IDX_L_OUT].x * w, lm[_IDX_L_OUT].y * h
        rx, ry = lm[_IDX_R_OUT].x * w, lm[_IDX_R_OUT].y * h
        eye_dist = math.hypot(lx - rx, ly - ry)
        self.baseline_ratio = abs(chin_y - brow_y) / max(eye_dist, 1.0)
        return True

    def close(self):
        self._landmarker.close()

    # ── Private ───────────────────────────────────────────────

    @staticmethod
    def _to_mp_image(frame_rgb: np.ndarray):
        return mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)

    @staticmethod
    def _prox_tier(eye_dist: float) -> str:
        if eye_dist > config.PROX_SAFE:    return "ok"
        if eye_dist > config.PROX_CAUTION: return "caution"
        if eye_dist > config.PROX_WARN:    return "warn"
        return "alert"

    def _slouch_tier(self, ratio: float, bg_mode: bool) -> str:
        if self.baseline_ratio is None:
            return "ok" if ratio > 0.7 else "alert"
        drop_thresh = config.SLOUCH_DROP_BG if bg_mode else config.SLOUCH_DROP_CAM
        drop = (self.baseline_ratio - ratio) / max(self.baseline_ratio, 1e-6)
        if drop < drop_thresh * 0.5:   return "ok"
        if drop < drop_thresh:         return "caution"
        if drop < drop_thresh * 1.5:   return "warn"
        return "alert"
