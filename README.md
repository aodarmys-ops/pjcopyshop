# PJ Copy Shop - POS System

ระบบ POS สำหรับร้านถ่ายเอกสาร (Copy Shop) พร้อมด้วยระบบคลังสินค้า, บัญชีรายรับ-รายจ่าย, การจองคิวงาน, ระบบลูกค้าสมาชิก, โปรโมชั่น, จัดการสูตรการผลิต (BOM), และส่งรายงานขึ้น Google Sheets อัตโนมัติ

## ฟีเจอร์หลัก
- **ขายหน้าร้าน (POS)**: รองรับบาร์โค้ด, พิมพ์ใบเสร็จ, สแกน QR (เตรียมไว้), แยกชำระเงิน (Split)
- **คลังสินค้าและ BOM**: ตัดสต๊อกตามสูตรการผลิต, แจ้งเตือนของใกล้หมด
- **คิวงานสั่งทำ (Job Orders)**: ติดตามสถานะงานพิมพ์ขนาดใหญ่
- **ลูกค้าและลูกหนี้**: สะสมแต้ม, ค้างชำระ (Unpaid/Credit)
- **บัญชี (P&L, Cashflow)**: บันทึกค่าใช้จ่าย, ปิดยอดสิ้นวัน
- **Google Sheets Sync**: ซิงค์ข้อมูลขึ้น Google Sheets เพื่อดู Dashboard

## การติดตั้งและการรันระบบ
1. ติดตั้ง Python Library: `pip install -r requirements.txt`
2. ใส่ไฟล์ `service_account.json` สำหรับ Google Sheets API
3. รันระบบ: `python app.py`

## โค้ดสำหรับ Google Apps Script (Dashboard)
โค้ดสำหรับนำไปวางใน Google Apps Script (เพื่อให้แสดง Dashboard วิเคราะห์ยอดขายและวางแผนสั่งของ) อยู่ในโฟลเดอร์ `gas_dashboard`:
1. `gas_dashboard/Code.gs` -> วางใน `Code.gs` ของ Apps Script
2. `gas_dashboard/Index.html` -> สร้างไฟล์ `Index.html` และวางโค้ดใน Apps Script

(อย่าลืมตั้งค่า `XFrameOptionsMode.ALLOWALL` เพื่อให้ฝังใน Google Site ได้)
