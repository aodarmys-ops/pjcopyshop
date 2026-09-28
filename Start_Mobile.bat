@echo off
title 📱 ระบบเชื่อมต่อมือถือ (Ngrok)
color 0A
echo ==============================================================
echo 📱 กำลังเปิดช่องทางเชื่อมต่อมือถือเข้ากับคอมพิวเตอร์ (Ngrok)
echo ==============================================================
echo.
echo วิธีเข้าใช้งานจากมือถือ:
echo ให้เปิดเบราว์เซอร์ (Chrome/Safari) แล้วเข้าลิงก์ด้านล่างนี้
echo.
echo 👉 https://bunkhouse-footman-evasion.ngrok-free.dev
echo.
echo.
echo *** คำเตือน: ห้ามปิดหน้าต่างสีดำนี้เด็ดขาด จนกว่าจะเลิกใช้งานมือถือ ***
echo ==============================================================
echo.
"C:\Users\NB34\AppData\Local\Microsoft\WinGet\Links\ngrok.exe" http --url=bunkhouse-footman-evasion.ngrok-free.dev 5000
pause
