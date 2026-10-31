@echo off
chcp 65001 >nul
set "PYTHONIOENCODING=utf-8"
set "PYTHONUTF8=1"
title 🚀 PJ Copy Shop - POS System
color 0B

echo ==============================================================
echo 🚀 PJ Copy Shop - POS System
echo ==============================================================
echo.

cd /d "%~dp0"

set "RUN_PYTHON="

REM 1. ทดสอบ Virtual Environment (venv) ในโฟลเดอร์โปรแกรม
if exist "%~dp0venv\Scripts\python.exe" (
    "%~dp0venv\Scripts\python.exe" -c "import flask, waitress" >nul 2>nul
    if not errorlevel 1 (
        set "RUN_PYTHON=%~dp0venv\Scripts\python.exe"
        goto :python_found
    )
)

REM 2. ทดสอบ Python หลักของระบบใน PATH
python -c "import flask, waitress" >nul 2>nul
if not errorlevel 1 (
    set "RUN_PYTHON=python"
    goto :python_found
)

REM 3. ทดสอบ py launcher
py -3 -c "import flask, waitress" >nul 2>nul
if not errorlevel 1 (
    set "RUN_PYTHON=py -3"
    goto :python_found
)

REM 4. ทดสอบตำแหน่งติดตั้งมาตรฐานของผู้ใช้
if exist "%LOCALAPPDATA%\Programs\Python\Python314\python.exe" (
    "%LOCALAPPDATA%\Programs\Python\Python314\python.exe" -c "import flask, waitress" >nul 2>nul
    if not errorlevel 1 (
        set "RUN_PYTHON=%LOCALAPPDATA%\Programs\Python\Python314\python.exe"
        goto :python_found
    )
)

REM 5. ทดสอบ Portable Runtime
if exist "%~dp0python_runtime\python.exe" (
    "%~dp0python_runtime\python.exe" -c "import flask, waitress" >nul 2>nul
    if not errorlevel 1 (
        set "RUN_PYTHON=%~dp0python_runtime\python.exe"
        goto :python_found
    )
)

REM 6. หากยังไม่พบสภาพแวดล้อมที่พร้อม ให้เรียก SETUP.bat ช่วยติดตั้ง
echo ⚠️ ยังไม่พบสภาพแวดล้อมระบบที่พร้อมใช้งาน
echo 🛠️ กำลังเปิดระบบติดตั้งอัตโนมัติ กรุณารอสักครู่...
echo.
call "%~dp0SETUP.bat"

if exist "%~dp0venv\Scripts\python.exe" (
    set "RUN_PYTHON=%~dp0venv\Scripts\python.exe"
    goto :python_found
)

echo.
echo ==============================================================
echo ❌ ไม่พบ Python หรือติดตั้งไม่สำเร็จ
echo กรุณารันไฟล์ SETUP.bat อีกครั้งเพื่อติดตั้ง
echo ==============================================================
pause
exit /b 1

:python_found
echo [OK] สภาพแวดล้อมพร้อมใช้งาน
echo เซิร์ฟเวอร์กำลังทำงาน... กรุณาย่อหน้าต่างนี้ไว้
echo ห้ามปิดหน้าต่างนี้จนกว่าจะเลิกใช้งานระบบ
echo.

%RUN_PYTHON% "%~dp0run_server.py"

if %errorlevel% neq 0 (
    echo.
    echo ==============================================================
    echo ⚠️ ระบบหยุดทำงาน (Error Code: %errorlevel%)
    echo ==============================================================
    pause
)
