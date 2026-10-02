@echo off
title 🛠️ ติดตั้งระบบ POS - PJ Copy Shop
color 0A
echo ==============================================================
echo 🛠️ กำลังติดตั้งระบบ POS สำหรับร้าน PJ Copy Shop
echo ==============================================================
echo.
echo [1/3] กำลังสร้าง Virtual Environment...
python -m venv venv

echo.
echo [2/3] กำลังอัปเดตระบบจัดการแพ็กเกจ (PIP)...
call venv\Scripts\activate.bat
python -m pip install --upgrade pip

echo.
echo [3/3] กำลังติดตั้ง Libraries ที่จำเป็น (กรุณารอสักครู่)...
pip install -r requirements.txt

echo.
echo ==============================================================
echo ✅ ติดตั้งระบบเสร็จสมบูรณ์!
echo สามารถดับเบิลคลิกที่ไฟล์ "2_Start_POS.bat" เพื่อเปิดใช้งานระบบได้เลย
echo ==============================================================
pause
