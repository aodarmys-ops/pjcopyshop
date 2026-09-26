import sqlite3
import json

conn = sqlite3.connect('d:/xerox/xerox.db')
conn.row_factory = sqlite3.Row

data = {
    'total_revenue': dict(conn.execute("SELECT SUM(total_amount) as val FROM Sales WHERE payment_status NOT IN ('ยกเลิกบิล', 'ชำระบิลค้างชำระ')").fetchone())['val'],
    'cash': dict(conn.execute("SELECT SUM(total_amount) as val FROM Sales WHERE payment_status NOT IN ('ยกเลิกบิล', 'Unpaid', 'Pending') AND payment_method = 'Cash'").fetchone())['val'],
    'transfer': dict(conn.execute("SELECT SUM(total_amount) as val FROM Sales WHERE payment_status NOT IN ('ยกเลิกบิล', 'Unpaid', 'Pending') AND payment_method = 'PromptPay'").fetchone())['val'],
    'paid_unpaid': dict(conn.execute("SELECT SUM(total_amount) as val FROM Sales WHERE payment_status = 'ชำระบิลค้างชำระ'").fetchone())['val']
}

print(json.dumps(data, indent=2))
