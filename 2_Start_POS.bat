@echo off
title 🚀 PJ Copy Shop - POS System
color 0B
echo ==============================================================
echo 🚀 กำลังเปิดระบบ POS...
echo ==============================================================
echo.
echo เซิร์ฟเวอร์กำลังทำงาน... ห้ามปิดหน้าต่างนี้จนกว่าจะเลิกใช้งาน!
echo (ระบบจะเปิดบราวเซอร์หน้าแรกให้โดยอัตโนมัติ)
echo.
call venv\Scripts\activate.bat
python run_server.py
pause
