import sqlite3
import sys

try:
    sys.path.append('d:/xerox')
    from app import init_db

    conn = sqlite3.connect('d:/xerox/xerox.db')
    c = conn.cursor()
    c.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = c.fetchall()
    
    for table in tables:
        if table[0] != 'sqlite_sequence':
            c.execute(f"DROP TABLE IF EXISTS {table[0]}")
            
    conn.commit()
    conn.close()
    
    init_db()
    print("Database cleared and re-initialized.")
except Exception as e:
    print(f"Error: {e}")
