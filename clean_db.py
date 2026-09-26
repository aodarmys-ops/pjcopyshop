import sqlite3
conn = sqlite3.connect('d:/xerox/xerox.db')
conn.execute("DELETE FROM Expenses WHERE description LIKE 'สั่งซื้อสินค้าเข้าสต๊อก (PO #%'")
conn.commit()
print("Done")
