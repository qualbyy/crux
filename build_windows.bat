@echo off
REM ========================================================
REM  Sonde — Native Windows Release Build Script
REM ========================================================

echo ===^> [Sonde] Checking Windows build environment...

where cargo >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Cargo / Rust is not found in PATH!
    echo Please install Rust from https://rustup.rs/
    pause
    exit /b 1
)

cd /d "%~dp0src-tauri"

echo ===^> [Sonde 2.0] Building release binary for Windows (x86_64)...
cargo build --release

if %ERRORLEVEL% equ 0 (
    echo.
    echo ========================================================
    echo  [SUCCESS] Sonde Windows binary built successfully!
    echo  Binary: src-tauri\target\release\sonde-rs.exe
    echo ========================================================
) else (
    echo.
    echo [ERROR] Cargo build failed with exit code %ERRORLEVEL%
    pause
    exit /b %ERRORLEVEL%
)
