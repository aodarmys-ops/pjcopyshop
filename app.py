from flask import Flask, jsonify, request, render_template
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
    # Users & Roles
    c.execute('''
        CREATE TABLE IF NOT EXISTS Users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            role TEXT NOT NULL
        )
    ''')
    # Products & Services
    c.execute('''
        CREATE TABLE IF NOT EXISTS Products_Services (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            type TEXT NOT NULL,
            barcode TEXT,
            price REAL NOT NULL,
            cost REAL NOT NULL,
            stock_qty INTEGER DEFAULT 0,
            reorder_level INTEGER DEFAULT 5
        )
    ''')
    # Inventory Transactions
    c.execute('''
        CREATE TABLE IF NOT EXISTS Inventory_Transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER,
            qty INTEGER NOT NULL,
            type TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(product_id) REFERENCES Products_Services(id)
        )
    ''')
    # Sales
    c.execute('''
        CREATE TABLE IF NOT EXISTS Sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            total_amount REAL NOT NULL,
            payment_method TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS Sale_Items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sale_id INTEGER,
            product_id INTEGER,
            qty INTEGER NOT NULL,
            price REAL NOT NULL,
            FOREIGN KEY(sale_id) REFERENCES Sales(id),
            FOREIGN KEY(product_id) REFERENCES Products_Services(id)
        )
    ''')
    # Job Orders
    c.execute('''
        CREATE TABLE IF NOT EXISTS Job_Orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT,
            details TEXT,
            status TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    # Expenses
    c.execute('''
        CREATE TABLE IF NOT EXISTS Expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            description TEXT NOT NULL,
            amount REAL NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    # Customers
    c.execute('''
        CREATE TABLE IF NOT EXISTS Customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT,
            points INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/inventory')
def inventory():
    return render_template('inventory.html')

@app.route('/pos')
def pos():
    return render_template('pos.html')

@app.route('/api/products/search', methods=['GET'])
def search_product():
    query = request.args.get('q', '')
    conn = get_db_connection()
    products = conn.execute(
        'SELECT * FROM Products_Services WHERE barcode = ? OR name LIKE ?',
        (query, f'%{query}%')
    ).fetchall()
    conn.close()
    return jsonify([dict(ix) for ix in products])

@app.route('/api/products', methods=['GET'])
def get_products():
    conn = get_db_connection()
    products = conn.execute('SELECT * FROM Products_Services').fetchall()
    conn.close()
    return jsonify([dict(ix) for ix in products])

@app.route('/api/products', methods=['POST'])
def add_product():
    new_product = request.get_json()
    name = new_product.get('name')
    type = new_product.get('type')
    barcode = new_product.get('barcode', '')
    price = new_product.get('price', 0.0)
    cost = new_product.get('cost', 0.0)
    stock_qty = new_product.get('stock_qty', 0)
    reorder_level = new_product.get('reorder_level', 5)

    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''
        INSERT INTO Products_Services (name, type, barcode, price, cost, stock_qty, reorder_level)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (name, type, barcode, price, cost, stock_qty, reorder_level))
    conn.commit()
    conn.close()
    return jsonify({"message": "Product added successfully"}), 201

@app.route('/api/sales', methods=['POST'])
def checkout_sale():
    data = request.get_json()
    total_amount = data.get('total_amount', 0)
    payment_method = data.get('payment_method', 'Cash')
    items = data.get('items', [])

    conn = get_db_connection()
    c = conn.cursor()
    
    # 1. Insert into Sales
    c.execute('INSERT INTO Sales (total_amount, payment_method) VALUES (?, ?)', (total_amount, payment_method))
    sale_id = c.lastrowid

    # 2. Insert into Sale_Items and update stock
    for item in items:
        product_id = item['id']
        qty = item['qty']
        price = item['price']
        
        c.execute('INSERT INTO Sale_Items (sale_id, product_id, qty, price) VALUES (?, ?, ?, ?)',
                  (sale_id, product_id, qty, price))
        
        # Deduct stock if it is a retail product
        c.execute('UPDATE Products_Services SET stock_qty = stock_qty - ? WHERE id = ? AND type = "Retail"',
                  (qty, product_id))

    conn.commit()
    conn.close()
    return jsonify({"message": "Sale completed successfully", "sale_id": sale_id}), 201

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)
