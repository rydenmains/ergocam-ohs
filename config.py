"""
ErgoCam v3.0 — config.py
Konstanta global, palet warna Apple light, teks status.
"""

import os

# ── Path ─────────────────────────────────────────────────────
BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
LOGO_ICO  = os.path.join(BASE_DIR, "logo.ico")
LOGO_PNG  = os.path.join(BASE_DIR, "logo.png")
REPORT_DIR = os.path.join(BASE_DIR, "reports")

# ── App metadata ─────────────────────────────────────────────
APP_NAME = "ErgoCam"
APP_VER  = "3.0"
APP_ID   = "com.ergocam.app"          # Windows taskbar grouping

# ── Deteksi ──────────────────────────────────────────────────
FPS_TARGET          = 30
BREAK_INTERVAL_SEC  = 2 * 60 * 60    # 2 jam → paksa istirahat
BREAK_DURATION_SEC  = 5 * 60         # 5 menit istirahat

# Proximity: jarak mata (px) per tier
PROX_SAFE    = 90    # > nilai ini = Aman
PROX_CAUTION = 70    # 70-90 = Agak dekat
PROX_WARN    = 55    # 55-70 = Dekat
# < 55 = Berbahaya

# Slouch: face foreshortening ratio (chin-to-brow ÷ eye-width)
# Jatuh > DROP_CAM (10%) dari baseline → bungkuk (camera mode)
# Jatuh > DROP_BG  (12%) dari baseline → bungkuk (background mode)
SLOUCH_DROP_CAM = 0.10
SLOUCH_DROP_BG  = 0.12

# ── Palet — Apple light ───────────────────────────────────────
INK       = "#1d1d1f"   # teks utama
GRAPHITE  = "#3a3a3c"   # teks sekunder (kontras ~8:1 on white)
FOG       = "#f5f5f7"   # latar dasar
SNOW      = "#ffffff"   # permukaan kartu
CARD_HI   = "#e8e8ed"   # hover netral
SILVER    = "#b0b0b7"   # hairline / border — visible on FOG background
SILVER_HV = "#b0b0b7"
AZURE     = "#0071e3"   # aksi (Action Blue)
AZURE_HV  = "#0077ed"
CAUTION   = "#b85c00"   # oranye peringatan — darkened untuk WCAG AA on white (~5.1:1)
GREEN     = "#1a7a37"   # aman / tegak — darkened untuk WCAG AA on white (~5.3:1)
RED       = "#c0392b"   # bahaya — darkened untuk WCAG AA on white (~5.1:1)
RED_HV    = "#d93025"
BLACK     = "#000000"   # latar feed kamera

# ── Teks status ───────────────────────────────────────────────
STATUS_TEXT = {
    "proximity": {
        "idle":    "-",
        "ok":      "Aman",
        "caution": "Agak dekat",
        "warn":    "Dekat",
        "alert":   "Berbahaya",
    },
    "slouch": {
        "idle":    "-",
        "ok":      "Tegak",
        "caution": "Agak bungkuk",
        "warn":    "Bungkuk",
        "alert":   "Buruk",
    },
}


def status_color(status: str) -> str:
    """Warna dot/indikator untuk status string."""
    return {
        "ok":      GREEN,
        "caution": CAUTION,
        "warn":    CAUTION,
        "alert":   RED,
    }.get(status, GRAPHITE)
