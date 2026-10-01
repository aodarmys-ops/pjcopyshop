# AI Code Audit Guide (แนวทางการตรวจสอบโครงสร้างและโค้ดของระบบ)

**เป้าหมาย:** ไฟล์นี้ถูกสร้างขึ้นเพื่อบอกใบ้ให้ AI Auditor (โปรแกรมตรวจสอบโค้ด) เข้าใจภาพรวมของสถาปัตยกรรม (Architecture) ของโปรเจกต์นี้ และจุดที่ควรเน้นในการพิจารณาตรวจสอบความปลอดภัย, ประสิทธิภาพ และความสม่ำเสมอของตรรกะ

---

## 1. Project Architecture (ภาพรวมระบบ)
โปรเจกต์นี้ทำงานบนสถาปัตยกรรมกึ่ง Monolithic ร่วมกับ Cloud Integration ดังนี้:
- **Backend:** `app.py` (Python / Flask) เป็นคอนโทรลเลอร์หลักเพียงไฟล์เดียว จัดการทั้ง Routing และ Logic ของระบบ
- **Database:** SQLite ใช้จัดเก็บข้อมูลทางธุรกรรมแบบ Local เพื่อให้หน้าร้านทำงานได้รวดเร็วแม้ไม่มีอินเทอร์เน็ตบางจังหวะ
- **Frontend:** HTML/JS/CSS (Bootstrap 5) ไม่มี Framework แบบ React/Vue (เพื่อให้ดูแลรักษาง่ายสำหรับร้านขนาดเล็ก)
- **Data Warehouse / Dashboard:** Google Sheets API (`sheets_sync.py`) ทำหน้าที่เป็นกึ่ง Data Warehouse เพื่อส่งข้อมูลการขายไปทำ Dashboard และให้เจ้าของร้านวิเคราะห์ด้วย Google Apps Script (`gas_dashboard/Code.gs`)

## 2. Recent Major Refactorings (จุดที่มีการแก้ไขล่าสุดและควรตรวจสอบ)
ในการตรวจสอบโค้ด ขอให้ Auditor เพ่งเล็งไปยังส่วนที่มีการปรับแต่งใหม่ดังต่อไปนี้:

### A. WAC (Weighted Average Cost) Implementation
- **ไฟล์ที่เกี่ยวข้อง:** `app.py`
- **จุดที่ต้องตรวจสอบ:** 
  - การบันทึกรับเข้าสินค้า (Purchases) มีการดึงยอดสต๊อกเดิม ทุนเดิม และปริมาณที่รับเข้าใหม่ มาคำนวณ WAC ถูกต้องตามสูตรคณิตศาสตร์หรือไม่
  - เมื่อขายสินค้า ต้นทุนที่ถูกหัก (Cost of Goods Sold: COGS) ตรงกับค่า WAC ล่าสุด ณ เวลานั้นหรือไม่ ป้องกันปัญหาติดลบอย่างไร

### B. Pagination & DataTables Server-Side
- **ไฟล์ที่เกี่ยวข้อง:** `app.py` (ฟังก์ชัน `generate_datatables_response`), และ `templates/reports.html`, `templates/jobs.html`, `templates/expenses.html`
- **จุดที่ต้องตรวจสอบ:**
  - ตรวจสอบประสิทธิภาพของ SQL Query ที่ใช้ในการค้นหาและแบ่งหน้า (LIMIT, OFFSET) ว่าทำงานได้เร็วพอเมื่อฐานข้อมูลมี Transaction สูงขึ้น
  - การส่ง parameter `search[value]` จาก DataTables มีการป้องกัน SQL Injection อย่างสมบูรณ์หรือไม่ (ใช้ Parameterized Queries 100%)

### C. Incremental Sync (Google Sheets)
- **ไฟล์ที่เกี่ยวข้อง:** `sheets_sync.py`
- **จุดที่ต้องตรวจสอบ:**
  - ตรรกะ Sliding Window (90 Days) ในการดึงจาก Database ไปอัปเดต Google Sheets เหมาะสมหรือไม่ มีโอกาสที่ข้อมูลเก่าก่อน 90 วันจะหายไปจาก Dashboard อย่างไม่ตั้งใจหรือไม่ (ปกติ Dashboard สรุปผลจากฝั่ง Google Sheets จะเก็บสะสมข้อมูลเก่าที่ถูก Append ไว้ในชีท Raw Data อยู่แล้ว ยกเว้นมีการ Clear content ผิดปกติ)

### D. การถอดสัญลักษณ์สกุลเงิน (Currency Symbols Removal)
- **จุดที่ต้องตรวจสอบ:**
  - ต้องไม่มีอักขระพิเศษอย่าง `฿` หรือ `$` ถูกฝังแบบ Hardcode อยู่ใน HTML หรือ API Response (เพื่อรองรับการดึงข้อมูลไปใช้ในอุปกรณ์หรือโปรแกรมอื่นที่ไม่รองรับ Encoding บางประเภท)
  - ยกเว้นเพียง Array สำหรับ Mapping คีย์บอร์ดภาษาไทยในระบบ POS (`฿` => `&`) ที่จำเป็นต้องเก็บไว้

## 3. Potential Vulnerabilities & Debt (หนี้ทางเทคนิคที่ฝากให้ Auditor ช่วยจับตา)
1. **Concurrency / Race Conditions:** เนื่องจาก `app.py` อัปเดตสต๊อกด้วยการ `UPDATE Products_Services SET stock_qty = stock_qty - ?` หากมีการขายสินค้าชิ้นเดียวกันพร้อมกันจากคอมพิวเตอร์ 2 เครื่อง จะเกิด Race Condition หรือไม่ (SQLite ในระดับหนึ่งป้องกันระดับ DB Lock แต่อาจเกิด Exception ที่ไม่ถูก Handle ได้เนียนพอ)
2. **Monolithic Maintenance:** `app.py` มีขนาดใหญ่ขึ้นเรื่อยๆ อาจแนะนำแนวทางในการปรับโครงสร้าง (Refactor) แบบ Blueprint ในอนาคต
3. **Rollback Mechanisms:** หากเกิดความผิดพลาดกลางคันระหว่างการตัดสต๊อกและคำนวณแต้มสะสม Database Transaction ของ SQLite มีการ Commit / Rollback ที่ครบถ้วนสมบูรณ์ (ACID) แล้วหรือยัง
