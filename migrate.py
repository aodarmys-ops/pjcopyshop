import sqlite3
conn = sqlite3.connect('xerox.db')
try:
    conn.execute("ALTER TABLE Purchases ADD COLUMN payment_method TEXT DEFAULT 'Cash'")
except Exception as e:
    print(e)
conn.commit()
conn.close()
