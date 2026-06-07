# ErgoCam v3.0

**Real-time ergonomic posture and screen proximity monitor via webcam.**

Built for the K3 (Occupational Health & Safety) course. No extra hardware needed — just your existing webcam.

![Platform](https://img.shields.io/badge/platform-Windows%2010%2F11-0071e3?style=flat-square)
![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-1a7a37?style=flat-square)
![License](https://img.shields.io/badge/license-MIT-b0b0b7?style=flat-square)

---

## What It Does

ErgoCam watches your face through the webcam and tells you two things in real-time:

| Metric | How It Works |
|---|---|
| **Screen Proximity** | Measures pixel distance between outer eye corners (landmark 33 & 263). Wider = farther away. |
| **Posture (Slouch)** | Face foreshortening ratio: chin-to-brow height divided by eye width. Distance-invariant. |

Both metrics update at up to 30 FPS and are logged per session to CSV + XLSX.

---

## Screenshots

| Home | Live Session |
|---|---|
| ![Home](docs/home.png) | ![Live](docs/live.png) |

---

## Quick Start

> **Requires Python 3.10, 3.11, or 3.12.** Python 3.13 is not yet supported by mediapipe.
> During Python install, check **"Add Python to PATH"**.

```
1. Download the ZIP from Releases
2. Extract to any folder
3. Double-click run.bat
4. Wait 2-5 minutes on first run (auto-installs dependencies)
5. Done
```

After the first run, subsequent launches open instantly with no CMD window.

---

## Usage

### Calibration
Sit upright, press **C** (or click **Kalibrasi (C)**). This sets your upright posture as the baseline. Recalibrate whenever you change sitting position or move the camera.

### Status Tiers

**Proximity (Screen Distance)**

| Status | Condition | Color |
|---|---|---|
| Aman (Safe) | eye distance > 90px | Green |
| Agak Dekat (Caution) | 70–90px | Orange |
| Dekat (Warning) | 55–70px | Orange |
| Berbahaya (Danger) | <= 55px | Red |

**Posture**

| Status | Drop from Baseline | Color |
|---|---|---|
| Tegak (Upright) | < 5% | Green |
| Agak Bungkuk (Slight) | 5–10% | Orange |
| Bungkuk (Slouch) | 10–15% | Orange |
| Buruk (Severe) | >= 15% | Red |

### Forced Break
After 2 continuous hours, a fullscreen break overlay appears with a 5-minute countdown. Timer resets after the break.

### Reports
Session logs save automatically to `reports/` on stop or window close.

```
reports/
  ergocam_20260612_143022.csv
  ergocam_20260612_143022.xlsx
```

XLSX includes color-coded rows and a Summary sheet.

---

## Modes

| Mode | Camera Feed | Slouch Threshold | Best For |
|---|---|---|---|
| **Mode Kamera** | Shown | 10% drop | Active monitoring |
| **Mode Background** | Hidden | 12% drop | Focused work |

---

## Troubleshooting

**App closes immediately on run.bat**
Run `run.bat debug` — the window stays open and shows the error. Check `install.log` in the same folder.

**"Kalibrasi gagal" toast**
Face not detected. Ensure your face is visible in frame and lighting is adequate.

**Status always shows —**
Camera not found or in use by another app. Close other camera apps and restart ErgoCam.

**FPS below 5**
Close other heavy applications. ErgoCam targets 30 FPS but CPU load can limit this.

---

## Build Standalone .exe

```bat
build-exe.bat
```

Output: `dist\ErgoCam\` — zip that folder for distribution without requiring Python.

---

## Tech Stack

| Package | Purpose |
|---|---|
| PySide6-Essentials | Qt6 UI, threading, signals |
| mediapipe >= 0.10.30 | FaceLandmarker Tasks API |
| opencv-python | Webcam capture, frame processing |
| numpy | Frame array manipulation |
| openpyxl | XLSX report export (optional) |

> **Note:** mediapipe 0.10.30+ removed `mp.solutions` — this project uses the Tasks API (`mediapipe.tasks.python.vision.FaceLandmarker`).

---

## Project Structure

```
ergocam/
├── main.py                 Entry point
├── config.py               Constants, Apple light color palette
├── requirements.txt
├── run.bat                 Auto-setup launcher
├── build-exe.bat           PyInstaller build script
├── core/
│   ├── detector.py         MediaPipe pipeline, proximity & slouch logic
│   ├── camera_worker.py    QThread, EMA FPS, frame capture
│   └── session.py          Session timer, event logging, CSV/XLSX export
└── ui/
    └── main_window.py      PySide6 UI, QSS design system, all screens
```

---

## License

MIT — free to use, modify, and distribute.

---

*ErgoCam v3.0 — Raffa Hayden — K3 Project 2026*
