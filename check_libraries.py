import sys

# Ensure UTF-8 output on Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

modules = [
    ('Flask - ระบบเว็บเซิร์ฟเวอร์', 'flask'),
    ('Waitress - เซิร์ฟเวอร์ Production รองรับเครื่องลูกข่าย', 'waitress'),
    ('QRCode & Pillow - สร้างคิวอาร์โค้ดพร้อมเพย์รับเงิน', 'qrcode'),
    ('Requests - เชื่อมต่อส่งข้อมูลผ่าน HTTP', 'requests'),
    ('Flask-Limiter - ระบบความปลอดภัยควบคุมอัตราการเรียก', 'flask_limiter'),
    ('Google API Client - ซิงค์ Google Sheets / Drive', 'googleapiclient'),
    ('Google Auth - ระบบยืนยันสิทธิ์กับ Google API', 'google.oauth2')
]

all_ok = True
for name, mod in modules:
    try:
        __import__(mod)
        print(f'   ✅  {name} : พร้อมใช้งาน')
    except ImportError as e:
        all_ok = False
        print(f'   ❌  {name} : ไม่พบ ({e})')

if all_ok:
    print('\n' + '=' * 60)
    print('🎉 ไลบรารีทั้งหมดติดตั้งและพร้อมใช้งาน 100% เรียบร้อยแล้ว!')
    print('=' * 60)
    sys.exit(0)
else:
    print('\n' + '=' * 60)
    print('⚠️ มีบางไลบรารียังติดตั้งไม่สมบูรณ์')
    print('=' * 60)
    sys.exit(1)
