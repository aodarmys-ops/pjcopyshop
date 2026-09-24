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
            brand TEXT DEFAULT '',
            model TEXT DEFAULT '',
            color TEXT DEFAULT '',
            price REAL NOT NULL,
            cost REAL NOT NULL,
            stock_qty INTEGER DEFAULT 0,
            reorder_level INTEGER DEFAULT 5,
            is_active INTEGER DEFAULT 1
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
            discount REAL DEFAULT 0,
            payment_method TEXT NOT NULL,
            payment_status TEXT DEFAULT 'Paid',
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
    # Purchases
    c.execute('''
        CREATE TABLE IF NOT EXISTS Purchases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            supplier_name TEXT,
            subtotal REAL NOT NULL,
            vat_amount REAL DEFAULT 0,
            total_amount REAL NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS Purchase_Items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            purchase_id INTEGER,
            product_id INTEGER,
            qty INTEGER NOT NULL,
            cost_price REAL NOT NULL,
            FOREIGN KEY(purchase_id) REFERENCES Purchases(id),
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

@app.route('/print-barcodes')
def print_barcodes():
    return render_template('print_barcodes.html')

@app.route('/purchases')
def purchases():
    return render_template('purchases.html')

@app.route('/pos')
def pos():
    return render_template('pos.html')

@app.route('/jobs')
def jobs():
    return render_template('jobs.html')

@app.route('/expenses')
def expenses():
    return render_template('expenses.html')

@app.route('/crm')
def crm():
    return render_template('crm.html')

@app.route('/reports')
def reports():
    return render_template('reports.html')

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
    products = conn.execute('SELECT * FROM Products_Services WHERE is_active = 1 ORDER BY id DESC').fetchall()
    conn.close()
    return jsonify([dict(ix) for ix in products])

@app.route('/api/products', methods=['POST'])
def add_product():
    new_product = request.get_json()
    name = new_product.get('name')
    type = new_product.get('type')
    brand = new_product.get('brand', '')
    model = new_product.get('model', '')
    color = new_product.get('color', '')
    
    import random
    barcode = new_product.get('barcode', '').strip()
    if not barcode:
        # Generate random 8 digit barcode
        barcode = str(random.randint(10000000, 99999999))
        
    price = new_product.get('price', 0.0)
    cost = new_product.get('cost', 0.0)
    stock_qty = new_product.get('stock_qty', 0)
    reorder_level = new_product.get('reorder_level', 5)

    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''
        INSERT INTO Products_Services (name, type, barcode, brand, model, color, price, cost, stock_qty, reorder_level)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (name, type, barcode, brand, model, color, price, cost, stock_qty, reorder_level))
    conn.commit()
    conn.close()
    return jsonify({"message": "Product added successfully"}), 201

@app.route('/api/products/<int:product_id>/stock', methods=['PUT'])
def add_product_stock(product_id):
    data = request.get_json()
    add_qty = data.get('add_qty', 0)
    
    if add_qty <= 0:
        return jsonify({"message": "Invalid quantity"}), 400
        
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('UPDATE Products_Services SET stock_qty = stock_qty + ? WHERE id = ?', (add_qty, product_id))
    conn.commit()
    conn.close()
    
    return jsonify({"message": "Stock updated successfully"})

@app.route('/api/products/<int:product_id>', methods=['DELETE'])
def delete_product(product_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('UPDATE Products_Services SET is_active = 0 WHERE id = ?', (product_id,))
    conn.commit()
    conn.close()
    
    return jsonify({"message": "Product deleted successfully"})

@app.route('/api/products/<int:product_id>', methods=['PUT'])
def update_product(product_id):
    data = request.get_json()
    name = data.get('name')
    type = data.get('type')
    brand = data.get('brand', '')
    model = data.get('model', '')
    color = data.get('color', '')
    barcode = data.get('barcode', '').strip()
    price = data.get('price', 0.0)
    cost = data.get('cost', 0.0)
    stock_qty = data.get('stock_qty', 0)
    reorder_level = data.get('reorder_level', 5)

    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''
        UPDATE Products_Services 
        SET name=?, type=?, barcode=?, brand=?, model=?, color=?, price=?, cost=?, stock_qty=?, reorder_level=?
        WHERE id = ?
    ''', (name, type, barcode, brand, model, color, price, cost, stock_qty, reorder_level, product_id))
    conn.commit()
    conn.close()
    
    return jsonify({"message": "Product updated successfully"})

@app.route('/api/products/<int:product_id>/price', methods=['PUT'])
def edit_product_price(product_id):
    data = request.get_json()
    cost = data.get('cost')
    price = data.get('price')
    
    if cost is None or price is None or cost < 0 or price < 0:
        return jsonify({"message": "Invalid cost or price"}), 400
        
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('UPDATE Products_Services SET cost = ?, price = ? WHERE id = ?', (cost, price, product_id))
    conn.commit()
    conn.close()
    
    return jsonify({"message": "Product price updated successfully"})

@app.route('/api/sales', methods=['POST'])
def checkout_sale():
    data = request.get_json()
    total_amount = data.get('total_amount', 0)
    discount = data.get('discount', 0)
    payment_method = data.get('payment_method', 'Cash')
    payment_status = data.get('payment_status', 'Paid')
    items = data.get('items', [])

    conn = get_db_connection()
    c = conn.cursor()
    
    # 1. Insert into Sales
    c.execute('''
        INSERT INTO Sales (total_amount, discount, payment_method, payment_status) 
        VALUES (?, ?, ?, ?)
    ''', (total_amount, discount, payment_method, payment_status))
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

@app.route('/api/sales/<int:sale_id>/void', methods=['POST'])
def void_sale(sale_id):
    conn = get_db_connection()
    c = conn.cursor()
    
    # Check if already voided
    sale = c.execute("SELECT payment_status FROM Sales WHERE id = ?", (sale_id,)).fetchone()
    if not sale or sale['payment_status'] == 'ยกเลิกบิล':
        conn.close()
        return jsonify({"message": "Invalid or already voided sale"}), 400
        
    # Get items to return stock
    items = c.execute("SELECT product_id, qty FROM Sale_Items WHERE sale_id = ?", (sale_id,)).fetchall()
    
    for item in items:
        # We only return stock for Retail type (which is managed by stock_qty)
        # Actually, adding stock back to any product won't hurt if it's a Service (it stays 0 usually, but let's be safe)
        c.execute('UPDATE Products_Services SET stock_qty = stock_qty + ? WHERE id = ? AND type = "Retail"',
                  (item['qty'], item['product_id']))
                  
    # Mark as voided
    c.execute("UPDATE Sales SET payment_status = 'ยกเลิกบิล', total_amount = 0 WHERE id = ?", (sale_id,))
    
    conn.commit()
    conn.close()
    return jsonify({"message": "Sale voided successfully"})

# --- Purchasing / Procurement ---
@app.route('/api/purchases', methods=['POST'])
def add_purchase():
    data = request.get_json()
    supplier_name = data.get('supplier_name', 'ไม่ระบุ')
    has_vat = data.get('has_vat', False)
    items = data.get('items', [])

    if not items:
        return jsonify({"message": "No items in purchase"}), 400

    subtotal = sum(item['qty'] * item['cost'] for item in items)
    vat_amount = subtotal * 0.07 if has_vat else 0.0
    total_amount = subtotal + vat_amount

    conn = get_db_connection()
    c = conn.cursor()
    
    # 1. Insert Purchase
    c.execute('''
        INSERT INTO Purchases (supplier_name, subtotal, vat_amount, total_amount) 
        VALUES (?, ?, ?, ?)
    ''', (supplier_name, subtotal, vat_amount, total_amount))
    purchase_id = c.lastrowid

    # 2. Insert Items & Update Stock & Cost
    for item in items:
        product_id = item['id']
        qty = item['qty']
        cost = item['cost']
        
        c.execute('INSERT INTO Purchase_Items (purchase_id, product_id, qty, cost_price) VALUES (?, ?, ?, ?)',
                  (purchase_id, product_id, qty, cost))
        
        # Add stock and optionally update the cost to the latest purchase cost
        c.execute('UPDATE Products_Services SET stock_qty = stock_qty + ?, cost = ? WHERE id = ?',
                  (qty, cost, product_id))

    # 3. Add to Expenses automatically
    expense_desc = f"สั่งซื้อสินค้าเข้าสต๊อก (PO #{purchase_id}) - {supplier_name}"
    c.execute('INSERT INTO Expenses (description, amount) VALUES (?, ?)', (expense_desc, total_amount))

    conn.commit()
    conn.close()
    return jsonify({"message": "Purchase completed", "purchase_id": purchase_id}), 201

# --- Phase 3: Job Orders ---
@app.route('/api/jobs', methods=['GET'])
def get_jobs():
    conn = get_db_connection()
    jobs = conn.execute('SELECT * FROM Job_Orders ORDER BY timestamp DESC').fetchall()
    conn.close()
    return jsonify([dict(ix) for ix in jobs])

@app.route('/api/jobs', methods=['POST'])
def add_job():
    data = request.get_json()
    customer_name = data.get('customer_name')
    details = data.get('details')
    status = data.get('status', 'รอคิว')
    
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('INSERT INTO Job_Orders (customer_name, details, status) VALUES (?, ?, ?)', (customer_name, details, status))
    conn.commit()
    conn.close()
    return jsonify({"message": "Job created"}), 201

@app.route('/api/jobs/<int:job_id>', methods=['PUT'])
def update_job_status(job_id):
    data = request.get_json()
    status = data.get('status')
    
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('UPDATE Job_Orders SET status = ? WHERE id = ?', (status, job_id))
    conn.commit()
    conn.close()
    return jsonify({"message": "Job status updated"})

# --- Phase 3: Expenses ---
@app.route('/api/expenses', methods=['GET'])
def get_expenses():
    conn = get_db_connection()
    expenses = conn.execute('SELECT * FROM Expenses ORDER BY timestamp DESC').fetchall()
    conn.close()
    return jsonify([dict(ix) for ix in expenses])

@app.route('/api/expenses', methods=['POST'])
def add_expense():
    data = request.get_json()
    description = data.get('description')
    amount = data.get('amount')
    
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('INSERT INTO Expenses (description, amount) VALUES (?, ?)', (description, amount))
    conn.commit()
    conn.close()
    return jsonify({"message": "Expense recorded"}), 201

# --- Phase 4: CRM & Loyalty ---
@app.route('/api/customers', methods=['GET'])
def get_customers():
    conn = get_db_connection()
    customers = conn.execute('SELECT * FROM Customers ORDER BY name').fetchall()
    conn.close()
    return jsonify([dict(ix) for ix in customers])

@app.route('/api/customers', methods=['POST'])
def add_customer():
    data = request.get_json()
    name = data.get('name')
    phone = data.get('phone', '')
    
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('INSERT INTO Customers (name, phone, points) VALUES (?, ?, 0)', (name, phone))
    conn.commit()
    conn.close()
    return jsonify({"message": "Customer added"}), 201

@app.route('/api/customers/<int:customer_id>/points', methods=['PUT'])
def update_points(customer_id):
    data = request.get_json()
    action = data.get('action') # 'add' or 'redeem'
    points = int(data.get('points', 0))
    
    conn = get_db_connection()
    c = conn.cursor()
    
    if action == 'add':
        c.execute('UPDATE Customers SET points = points + ? WHERE id = ?', (points, customer_id))
    elif action == 'redeem':
        # Don't let points go below zero
        c.execute('UPDATE Customers SET points = MAX(0, points - ?) WHERE id = ?', (points, customer_id))
        
    conn.commit()
    conn.close()
    return jsonify({"message": f"Points {action}ed successfully"})

@app.route('/receipt/<int:sale_id>')
def receipt(sale_id):
    conn = get_db_connection()
    sale = conn.execute('SELECT * FROM Sales WHERE id = ?', (sale_id,)).fetchone()
    if not sale:
        conn.close()
        return "Sale not found", 404
        
    items = conn.execute('''
        SELECT si.qty, si.price, p.name 
        FROM Sale_Items si
        JOIN Products_Services p ON si.product_id = p.id
        WHERE si.sale_id = ?
    ''', (sale_id,)).fetchall()
    conn.close()
    
    return render_template('receipt.html', sale=dict(sale), items=[dict(ix) for ix in items])

@app.route('/purchase-receipt/<int:purchase_id>')
def purchase_receipt(purchase_id):
    conn = get_db_connection()
    purchase = conn.execute('SELECT * FROM Purchases WHERE id = ?', (purchase_id,)).fetchone()
    if not purchase:
        conn.close()
        return "Purchase not found", 404
        
    items = conn.execute('''
        SELECT pi.qty, pi.cost_price, p.name 
        FROM Purchase_Items pi
        JOIN Products_Services p ON pi.product_id = p.id
        WHERE pi.purchase_id = ?
    ''', (purchase_id,)).fetchall()
    conn.close()
    
    return render_template('purchase_receipt.html', purchase=dict(purchase), items=[dict(ix) for ix in items])

# --- Phase 5: Reporting ---
@app.route('/api/reports', methods=['GET'])
def get_reports():
    conn = get_db_connection()
    
    # Total Revenue from Sales (excluding voided)
    sales_result = conn.execute("SELECT SUM(total_amount) as total_revenue FROM Sales WHERE payment_status != 'ยกเลิกบิล'").fetchone()
    total_revenue = sales_result['total_revenue'] if sales_result['total_revenue'] else 0.0
    
    # Total Expenses
    expenses_result = conn.execute('SELECT SUM(amount) as total_expenses FROM Expenses').fetchone()
    total_expenses = expenses_result['total_expenses'] if expenses_result['total_expenses'] else 0.0
    
    # Recent Sales List
    recent_sales = conn.execute('SELECT * FROM Sales ORDER BY timestamp DESC LIMIT 10').fetchall()
    
    conn.close()
    
    net_profit = total_revenue - total_expenses
    
    return jsonify({
        "total_revenue": total_revenue,
        "total_expenses": total_expenses,
        "net_profit": net_profit,
        "recent_sales": [dict(ix) for ix in recent_sales]
    })

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)
