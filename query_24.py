import sqlite3
import json
conn = sqlite3.connect('d:/xerox/xerox.db')
conn.row_factory = sqlite3.Row

res1 = conn.execute("SELECT SUM(total_amount) as sales, SUM(discount) as discount FROM Sales WHERE timestamp LIKE '2026-09-24%' AND payment_status NOT IN ('ยกเลิกบิล', 'ชำระบิลค้างชำระ')").fetchone()
res2 = conn.execute("SELECT SUM(total_amount) as purchases FROM Purchases WHERE timestamp LIKE '2026-09-24%'").fetchone()

print(f"Sales: {res1['sales']}, Discount: {res1['discount']}")
print(f"Purchases: {res2['purchases']}")
