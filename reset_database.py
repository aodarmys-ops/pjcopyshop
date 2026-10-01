import sqlite3

def reset_database():
    # เตือนความจำก่อนลบจริง
    confirm = input("⚠️ คำเตือน: ข้อมูลทั้งหมดจะถูกลบถาวร พิมพ์ 'Y' เพื่อยืนยันการล้างฐานข้อมูล: ")
    if confirm.upper() != 'Y':
        print("ยกเลิกการทำงาน...")
        return

    conn = sqlite3.connect('xerox.db')
    c = conn.cursor()
    
    try:
        # 1. ปิดการตรวจสอบ Foreign Key ชั่วคราวเพื่อไม่ให้ติด Error ตอนลบข้อมูลข้ามตาราง
        c.execute('PRAGMA foreign_keys = OFF;')
        
        # 2. ดึงรายชื่อตารางทั้งหมด (ยกเว้นตารางระบบของ SQLite)
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
        tables = c.fetchall()
        
        # 3. สั่งลบข้อมูล (DELETE) ทุกตาราง
        for table in tables:
            table_name = table[0]
            print(f"กำลังลบข้อมูลในตาราง: {table_name}...")
            c.execute(f"DELETE FROM {table_name};")
            
        # 4. ลบประวัติการนับ Auto Increment เพื่อให้ ID กลับไปเริ่มที่ 1 ใหม่
        print("กำลังรีเซ็ตตัวเลขรันอัตโนมัติ (Auto Increment)...")
        c.execute("DELETE FROM sqlite_sequence;")
        
        # 5. เปิด Foreign Key กลับมาเหมือนเดิม
        c.execute('PRAGMA foreign_keys = ON;')
        conn.commit()
        
        # 6. คืนพื้นที่ว่างให้ไฟล์ .db (Vacuum)
        conn.execute("VACUUM;")
        
        print("\n✅ ล้างฐานข้อมูลเสร็จสมบูรณ์! ระบบกลับไปเป็นฐานข้อมูลเปล่าแล้ว")
        print("💡 หมายเหตุ: รหัสผ่านแอดมินจะกลับไปเป็นค่าเริ่มต้น (PIN: 1234) เมื่อคุณรัน app.py ครั้งถัดไป")
        
    except Exception as e:
        print(f"❌ เกิดข้อผิดพลาด: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == '__main__':
    reset_database()