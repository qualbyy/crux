@echo off
setlocal enabledelayedexpansion

echo ========================================================
echo       Crux Browser - Windows x86_64 Builder
echo ========================================================
echo.

if not exist ".venv" (
    echo [1/4] Creating Python virtual environment...
    python -m venv .venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment. Ensure Python 3.10+ is installed and in PATH.
        exit /b 1
    )
)

echo [2/4] Activating virtual environment and installing dependencies...
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller

echo.
echo [3/4] Building Crux standalone executable with PyInstaller...
pyinstaller crux.spec --noconfirm --clean

if not exist "dist\crux\crux.exe" (
    echo.
    echo [ERROR] Build failed! crux.exe was not generated.
    exit /b 1
)

echo.
echo [4/4] Packaging portable ZIP distribution...
powershell -Command "Compress-Archive -Path dist\crux\* -DestinationPath dist\crux-windows-x86_64.zip -Force"
powershell -Command "(Get-FileHash -Algorithm SHA256 dist\crux-windows-x86_64.zip).Hash | Out-File -FilePath dist\crux-windows-x86_64.zip.sha256 -Encoding ascii"

echo.
echo ========================================================
echo Build Succeeded!
echo Output: dist\crux\crux.exe
echo Archive: dist\crux-windows-x86_64.zip
echo ========================================================
pause
