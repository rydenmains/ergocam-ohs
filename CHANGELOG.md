# Changelog - ErgoCam

All notable changes to ErgoCam are documented here.

---

## [3.0] - 2026-06-08

### Architecture
- Full rewrite from single-file CustomTkinter to 5-file modular PySide6 architecture
- Migrated from `mp.solutions.face_mesh` (removed in mediapipe 0.10.30+) to MediaPipe Tasks API (`FaceLandmarker`)
- `face_landmarker.task` model auto-downloads on first run (~3.7 MB)
- `CameraWorker` moved to dedicated `QThread` with Qt signals - no more polling from main thread
- Split into `core/detector.py`, `core/camera_worker.py`, `core/session.py`, `ui/main_window.py`, `config.py`

### Detection
- **Slouch algorithm replaced**: nose-to-eye-midpoint ratio (only captured head tilt) replaced with face foreshortening ratio (`chin-to-brow height / eye width`) - now distance-invariant and correctly detects forward head posture
- Slouch threshold: 10% drop from baseline (camera mode), 12% (background mode)
- Proximity tiers recalibrated: Safe >90px, Caution 70–90px, Warning 55–70px, Danger <=55px

### UI
- Migrated from CustomTkinter to PySide6 with Apple light design system
- `_set_label()` dirty-check cache - skips `setText`/`setStyleSheet` when value unchanged, eliminates redundant repaints at 30fps
- Self-correcting SESI timer: 200ms tick instead of 1000ms, prevents drift
- EMA-smoothed FPS display (alpha=0.15) with 1-second windowed frame count
- Fixed-width stat value labels - no layout reflow when status text changes length
- `QFont.families()` moved post-`QApplication` init (was crashing on launch)
- `import sys` moved to top-level in `camera_worker.py` (was inline `__import__`)
- `BreakOverlay` and toast `QFrame` given `WA_StyledBackground=True` - fixes rgba background not rendering in PySide6
- `QFrame`-based mode cards replace `QPushButton` overlay pattern - eliminates text color inheritance bug
- Nav button explicit color at all states - prevents QSS global override leak

### Colors (WCAG AA compliance)
- `GREEN` `#34c759` → `#1a7a37` (ratio 2.8:1 → 5.3:1)
- `CAUTION` `#ff9500` → `#b85c00` (ratio 2.4:1 → 5.1:1)
- `RED` `#ff3b30` → `#c0392b` (ratio 3.9:1 → 5.1:1)
- `GRAPHITE` `#6e6e73` → `#3a3a3c` (ratio ~3.5:1 → 8.1:1)
- `SILVER` border `#d2d2d7` → `#b0b0b7` - visible on `FOG` background
- Mode card ghost description text: `rgba(255,255,255,0.80)` → `0.95`

### Packaging
- Switched from `PySide6` to `PySide6-Essentials` - eliminates ~600 MB unused Qt modules
- `run.bat`: auto-setup venv, install deps, launch without CMD window; `run.bat debug` for error visibility
- `build-exe.bat`: PyInstaller onedir build with `--collect-all mediapipe`
- `install.log` written on first-time setup for troubleshooting

### Reports
- CSV always written; XLSX written if openpyxl available (graceful fallback)
- XLSX: color-coded cells per status tier + Summary sheet

---

## [2.0] - 2026-05-30

### Detection
- Per-mode detection tuning: camera mode stricter, background mode uses slower/smoother thresholds
- `refine_landmarks=False`, inference downscaled to 640×360, frame-skip render for performance

### UI
- Converted from light to Apple-style dark mode
- Fixed critical shutdown bug: `write_report` importing `openpyxl` was blocking `root.destroy()`
- `bind_all` for keyboard shortcuts - transparent overlays were stealing focus
- WCAG contrast fix: `GRAPHITE` `#8e8e93` → `#aeaeb2` (6.3:1)
- Replaced emoji status indicators with CTk badge widgets
- Mode card hover feedback added
- Logo icon loading + `AppUserModelID` for Windows taskbar grouping
- Stats card repositioned to `relx=0.5, rely=1.0, anchor="s"` - fixed corner-to-center glitch from overlay approach

### Reports
- Replaced `.txt` logs with `.csv` (always) and `.xlsx` (best-effort)

---

## [1.0] - 2026-05-29

- Initial release: single-file Python + CustomTkinter + MediaPipe FaceMesh
- Proximity detection via eye-corner pixel distance
- Slouch detection via head-tilt ratio (nose-to-eye-midpoint)
- 2-hour forced break with 5-minute countdown overlay
- Calibration via keyboard shortcut C
- Session timer with HH:MM:SS display
- Background mode (detection without camera feed)
- `.txt` session log export
