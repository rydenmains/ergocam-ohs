@echo off
setlocal
cd /d "%~dp0"

if not exist "venv\Scripts\python.exe" (
    echo  [!] Jalankan run.bat dulu untuk setup venv.
    pause & exit /b 1
)

echo  [1/2] Install PyInstaller...
venv\Scripts\python.exe -m pip install --quiet pyinstaller

echo  [2/2] Build ErgoCam.exe...
set EXTRA=
if "%1"=="debug" set EXTRA=--console

venv\Scripts\pyinstaller --noconfirm --clean ^
    --name ErgoCam ^
    --onedir ^
    --noconsole %EXTRA% ^
    --icon logo.ico ^
    --add-data "logo.ico;." ^
    --add-data "logo.png;." ^
    --hidden-import PySide6.QtCore ^
    --hidden-import PySide6.QtGui ^
    --hidden-import PySide6.QtWidgets ^
    --collect-all mediapipe ^
    main.py

echo.
echo  Done! Folder: dist\ErgoCam\
echo  Zip folder itu dan kirim — penerima cukup double-click ErgoCam.exe
echo.
pause
