@echo off
chcp 65001 >nul
title 📱 ระบบเชื่อมต่อมือถือ (Ngrok) - PJ Copy Shop
color 0A

echo ==============================================================
echo 📱 PJ Copy Shop - ระบบเชื่อมต่อมือถือจากภายนอก
echo ==============================================================
echo.

cd /d "%~dp0"

set "NGROK_BIN="

if exist "%~dp0ngrok.exe" (
    set "NGROK_BIN=%~dp0ngrok.exe"
    goto :ngrok_found
)

where ngrok >nul 2>nul
if %errorlevel% equ 0 (
    set "NGROK_BIN=ngrok"
    goto :ngrok_found
)

if exist "%LOCALAPPDATA%\Microsoft\WinGet\Links\ngrok.exe" (
    set "NGROK_BIN=%LOCALAPPDATA%\Microsoft\WinGet\Links\ngrok.exe"
    goto :ngrok_found
)

if exist "%USERPROFILE%\AppData\Local\ngrok\ngrok.exe" (
    set "NGROK_BIN=%USERPROFILE%\AppData\Local\ngrok\ngrok.exe"
    goto :ngrok_found
)

:ngrok_missing
echo ⚠️ ยังไม่ได้ติดตั้ง ngrok บนเครื่องนี้
echo.
echo [วิธีที่ 1] หากมือถือและคอมพิวเตอร์ต่อ Wi-Fi เดียวกัน:
echo   เปิดเว็บเบราว์เซอร์ในมือถือ แล้วใส่ IP คอมพิวเตอร์ เช่น http://192.168.1.xxx:5000 ได้ทันที
echo.
echo [วิธีที่ 2] หากต้องการใช้งานผ่านอินเทอร์เน็ตนอกร้าน:
echo   สามารถติดตั้ง ngrok โดยพิมพ์คำสั่ง: winget install ngrok
echo   หรือดาวน์โหลดจาก https://ngrok.com/download
echo.
echo ==============================================================
pause
exit /b 1

:ngrok_found
echo วิธีเข้าใช้งานจากมือถือ:
echo 1. หากมีโดเมนส่วนตัว ให้เปิดเบราว์เซอร์แล้วเข้า URL ที่ตั้งไว้
echo 2. หากใช้งานฟรี ให้ดู URL (https://xxxx.ngrok-free.app) ที่แสดงบนหน้าต่างนี้
echo.
echo *** คำเตือน: ห้ามปิดหน้าต่างนี้ จนกว่าจะเลิกใช้งานมือถือ ***
echo ==============================================================
echo.

"%NGROK_BIN%" http --url=bunkhouse-footman-evasion.ngrok-free.dev 5000
if %errorlevel% neq 0 (
    echo.
    echo กำลังลองเชื่อมต่อแบบ Dynamic URL ปกติ...
    "%NGROK_BIN%" http 5000
)

pause
