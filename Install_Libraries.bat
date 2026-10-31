@echo off
chcp 65001 >nul
set "PYTHONIOENCODING=utf-8"
set "PYTHONUTF8=1"
title 📦 ติดตั้งและซ่อมแซมไลบรารี - PJ Copy Shop POS
color 0E

echo ==============================================================
echo 📦 ระบบติดตั้งและอัปเดตไลบรารี (Python Libraries Installer)
echo    PJ Copy Shop - POS System
echo ==============================================================
echo.

cd /d "%~dp0"

set "TARGET_PYTHON="

if exist "%~dp0venv\Scripts\python.exe" set "TARGET_PYTHON=%~dp0venv\Scripts\python.exe" & set "PY_NAME=Virtual Environment [venv]" & goto :found_python

where python >nul 2>nul
if %errorlevel% equ 0 set "TARGET_PYTHON=python" & set "PY_NAME=Python ในระบบ [PATH]" & goto :found_python

where py >nul 2>nul
if %errorlevel% equ 0 set "TARGET_PYTHON=py -3" & set "PY_NAME=Python Launcher [py]" & goto :found_python

if exist "%LOCALAPPDATA%\Programs\Python\Python314\python.exe" set "TARGET_PYTHON=%LOCALAPPDATA%\Programs\Python\Python314\python.exe" & set "PY_NAME=Python 3.14 ใน AppData" & goto :found_python

if exist "%~dp0python_runtime\python.exe" set "TARGET_PYTHON=%~dp0python_runtime\python.exe" & set "PY_NAME=Portable Python Runtime" & goto :found_python

echo ❌ ไม่พบ Python บนเครื่องนี้
echo กรุณารันไฟล์ SETUP.bat ก่อน เพื่อติดตั้ง Python อัตโนมัติ
echo.
pause
exit /b 1

:found_python
echo [1/3] ตรวจพบสภาพแวดล้อม: %PY_NAME%
echo       คำสั่งที่ใช้: %TARGET_PYTHON%
echo.

echo [2/3] กำลังติดตั้งไลบรารีจาก requirements.txt กรุณารอสักครู่...
echo --------------------------------------------------------------
%TARGET_PYTHON% -m pip install --upgrade pip --quiet 2>nul
%TARGET_PYTHON% -m pip install --prefer-binary -r "%~dp0requirements.txt"

where python >nul 2>nul
if %errorlevel% equ 0 (
    python -m pip install --prefer-binary -r "%~dp0requirements.txt" --quiet 2>nul
)

echo --------------------------------------------------------------
echo.

echo [3/3] ตรวจสอบความพร้อมของแต่ละโมดูล...
echo.

%TARGET_PYTHON% "%~dp0check_libraries.py"

if %errorlevel% equ 0 (
    echo.
    echo 👉 สามารถเปิดระบบขายหน้าร้านได้ที่ไฟล์: 2_Start_POS.bat
    echo.
) else (
    echo.
    echo 💡 แนะนำ: กรุณาตรวจสอบการเชื่อมต่ออินเทอร์เน็ต แล้วรันไฟล์นี้ใหม่อีกครั้ง
    echo.
)

pause
