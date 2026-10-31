@echo off
title Setup POS - PJ Copy Shop
cd /d "%~dp0"

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup.ps1"

if %errorlevel% neq 0 (
    echo.
    echo ==============================================================
    echo [ERROR] Installation failed. Please check the messages above.
    echo ==============================================================
    pause
)
