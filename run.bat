@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

:: Jalankan dengan "run.bat debug" untuk lihat error di terminal
set DEBUG=0
if /i "%1"=="debug" set DEBUG=1

:: ── Already installed → langsung jalankan ───────────────────
if exist "venv\Scripts\pythonw.exe" goto :run

:: ── First-time setup ─────────────────────────────────────────
echo.
echo  ErgoCam v3.0 - Setup Pertama Kali
echo  -----------------------------------------------
echo.

:: Cari Python
set PY=
for %%c in (python py python3) do (
    if "!PY!"=="" (
        %%c --version >nul 2>&1 && set PY=%%c
    )
)

if "!PY!"=="" (
    echo  [!] Python tidak ditemukan.
    echo  Download: https://www.python.org/downloads/
    echo  Centang "Add Python to PATH" saat install.
    echo.
    pause & exit /b 1
)

echo  Python ditemukan: !PY!
echo.

echo  [1/2] Membuat virtual environment...
!PY! -m venv venv
if !errorlevel! neq 0 (
    echo  [!] Gagal buat venv.
    pause & exit /b 1
)

echo  [2/2] Menginstall dependensi (2-5 menit pertama kali)...
venv\Scripts\python.exe -m pip install --upgrade pip >> install.log 2>&1
venv\Scripts\python.exe -m pip install ^
    "PySide6-Essentials" ^
    "opencv-python" ^
    "mediapipe>=0.10.30" ^
    "numpy" ^
    "openpyxl" >> install.log 2>&1

if !errorlevel! neq 0 (
    echo  [!] Install gagal. Buka install.log untuk detail.
    pause & exit /b 1
)

echo.
echo  Setup selesai!
echo.

:: ── Jalankan ────────────────────────────────────────────────
:run
if "%DEBUG%"=="1" (
    echo  [DEBUG MODE] Error akan tampil di sini.
    venv\Scripts\python.exe main.py
    pause
) else (
    start "" "venv\Scripts\pythonw.exe" main.py
)
exit
