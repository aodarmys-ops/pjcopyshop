import sqlite3
import sys

try:
    conn = sqlite3.connect('d:/xerox/xerox.db')
    c = conn.cursor()
    
    products = [
        ('33390852', 'กระดาษ A4 80 แกรม', 'ดับเบิ้ล A', '-', '-', 'Stationery', 100.00, 125.00, 0, 0),
        ('58228349', 'ปากกาน้ำเงิน', 'lancer', '-', '-', 'Stationery', 4.50, 7.00, 0, 0),
        ('21687618', 'โอเลี้ยง', '-', '-', '-', 'Brewed Drink', 20.00, 25.00, 0, 0),
        ('33569108', 'ปริ้นขาวดำ', '-', '-', '-', 'Service', 0.35, 2.00, 0, 0),
        ('31578376', 'ถ่ายเอกสารสี', '-', '-', '-', 'Service', 1.00, 5.00, 0, 0),
        ('56052559', 'ถ่ายเอกสารขาว-ดำ', '-', '-', '-', 'Service', 0.25, 1.00, 0, 0),
    ]
    
    for p in products:
        c.execute('''
            INSERT INTO Products_Services (barcode, name, brand, model, color, type, cost, price, stock_qty, reorder_level)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', p)
        
    conn.commit()
    conn.close()
    print("Re-seeded dummy products.")
except Exception as e:
    print(f"Error: {e}")
