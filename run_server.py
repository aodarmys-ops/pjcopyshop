import os
import sys
import time
import socket
import threading
import webbrowser
# บังคับใช้ UTF-8 เพื่อป้องกันปัญหา UnicodeEncodeError (charmap / CP874) บน Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

def get_local_ip():
    """ดึง IP Address ภายในเครือข่ายวงแลน / Wi-Fi"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(1.0)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return '127.0.0.1'

def is_port_in_use(port, host='127.0.0.1'):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex((host, port)) == 0

def open_browser():
    time.sleep(1.5)
    webbrowser.open('http://127.0.0.1:5000')

if __name__ == '__main__':
    port = 5000
    local_ip = get_local_ip()

    if is_port_in_use(port):
        print("==============================================================")
        print("⚠️ ระบบ POS เปิดทำงานอยู่แล้ว!")
        print(f"👉 สามารถเปิดใช้งานได้ที่: http://127.0.0.1:{port}")
        print("==============================================================")
        webbrowser.open(f'http://127.0.0.1:{port}')
        sys.exit(0)

    try:
        from app import app, init_db, migrate_pins_to_hash
        from waitress import serve
    except ImportError as e:
        print(f"❌ ข้อผิดพลาด: ไม่พบ Library ที่จำเป็น ({e})")
        print("กรุณารันไฟล์ 'SETUP.bat' เพื่อติดตั้งระบบก่อนใช้งาน")
        input("กด Enter เพื่อออก...")
        sys.exit(1)

    print("==============================================================")
    print("🚀 กำลังเริ่มต้นระบบ PJ Copy Shop - POS...")
    print("==============================================================")
    print("📦 ตรวจสอบและตั้งค่าฐานข้อมูล...")
    init_db()
    migrate_pins_to_hash()
    print("✅ ฐานข้อมูลพร้อมใช้งาน")

    print("\n--------------------------------------------------------------")
    print(f"💻 ใช้งานบนเครื่องนี้ (Local):        http://127.0.0.1:{port}")
    if local_ip != '127.0.0.1':
        print(f"📱 เครื่องอื่น/มือถือในวง Wi-Fi:      http://{local_ip}:{port}")
    print("🔑 รหัส PIN เริ่มต้นของผู้ดูแลระบบ (Admin): 1234")
    print("--------------------------------------------------------------")
    print("💡 คำแนะนำ: ย่อหน้าต่างนี้ไว้ขณะใช้งาน (ห้ามปิดหน้าต่างนี้)")
    print("==============================================================\n")

    threading.Thread(target=open_browser, daemon=True).start()

    # Run production WSGI server
    serve(app, host='0.0.0.0', port=port, threads=6)
