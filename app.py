from flask import Flask, jsonify, request
import sqlite3

app = Flask(__name__)
DB_FILE = 'xerox.db'

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS Users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            role TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

@app.route('/')
def index():
    return jsonify({"message": "Welcome to Copy Shop & Retail Management System API"})

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)
