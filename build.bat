@echo off
rem ============================================================
rem  Build PrincessMakerTool.exe with PyInstaller (Windows)
rem  Put this file, requirements.txt and PrincessMakerTool.py in
rem  the same folder, then double-click build.bat.
rem  Result: dist\PrincessMakerTool.exe
rem ============================================================
chcp 65001 >nul
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python was not found in PATH. Install Python 3.10+ first.
    pause
    exit /b 1
)

rem --- clean virtual env keeps the exe small and avoids the old "Crypto" (pycrypto) package ---
if not exist .venv_build (
    python -m venv .venv_build
)
call .venv_build\Scripts\activate.bat

python -m pip install --upgrade pip
pip install -r requirements.txt pyinstaller
if errorlevel 1 (
    echo [ERROR] pip install failed.
    pause
    exit /b 1
)

pyinstaller --noconfirm --clean --onefile --windowed ^
    --name PrincessMakerTool ^
    --collect-all customtkinter ^
    --collect-all UnityPy ^
    --hidden-import Crypto.Cipher.AES ^
    --hidden-import Crypto.Util.Counter ^
    --hidden-import Crypto.Random ^
    PrincessMakerTool.py
if errorlevel 1 (
    echo [ERROR] PyInstaller failed.
    pause
    exit /b 1
)

echo.
echo Done: %~dp0dist\PrincessMakerTool.exe
echo (tables\, patches\, TableData.db and pm_tool_settings.json will be created next to the exe)
pause
