# pyrefly: ignore [missing-import]
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
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            customer_id INTEGER,
            redeemed_points INTEGER DEFAULT 0
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
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS Stock_WriteOffs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER,
            qty INTEGER NOT NULL,
            reason TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(product_id) REFERENCES Products_Services(id)
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
        'SELECT * FROM Products_Services WHERE barcode LIKE ? OR name LIKE ?',
        (f'%{query}%', f'%{query}%')
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

@app.route('/api/inventory/writeoff', methods=['POST'])
def writeoff_stock():
    data = request.get_json()
    product_id = data.get('product_id')
    qty = data.get('qty', 0)
    reason = data.get('reason', 'ชำรุด')
    
    if not product_id or qty <= 0:
        return jsonify({"message": "Invalid data"}), 400
        
    conn = get_db_connection()
    c = conn.cursor()
    
    c.execute('UPDATE Products_Services SET stock_qty = stock_qty - ? WHERE id = ?', (qty, product_id))
    c.execute('INSERT INTO Stock_WriteOffs (product_id, qty, reason) VALUES (?, ?, ?)', (product_id, qty, reason))
    
    conn.commit()
    conn.close()
    return jsonify({"message": "Stock written off successfully"})

@app.route('/api/inventory/writeoff', methods=['GET'])
def get_writeoff_history():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    conn = get_db_connection()
    query = '''
        SELECT w.id, w.qty, w.reason, w.timestamp, p.name, p.barcode
        FROM Stock_WriteOffs w
        JOIN Products_Services p ON w.product_id = p.id
        WHERE 1=1
    '''
    params = []
    
    if start_date and end_date:
        query += " AND w.timestamp >= ? AND w.timestamp <= ?"
        params.extend([f"{start_date} 00:00:00", f"{end_date} 23:59:59"])
        
    query += " ORDER BY w.timestamp DESC"
    
    history = conn.execute(query, params).fetchall()
    conn.close()
    return jsonify([dict(ix) for ix in history])

@app.route('/api/sales', methods=['POST'])
def checkout_sale():
    data = request.get_json()
    total_amount = data.get('total_amount', 0)
    discount = data.get('discount', 0)
    payment_method = data.get('payment_method', 'Cash')
    payment_status = data.get('payment_status', 'Paid')
    customer_id = data.get('customer_id')
    redeemed_points = data.get('redeemed_points', 0)
    items = data.get('items', [])

    conn = get_db_connection()
    c = conn.cursor()
    
    # 1. Insert into Sales
    c.execute('''
        INSERT INTO Sales (total_amount, discount, payment_method, payment_status, customer_id, redeemed_points) 
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (total_amount, discount, payment_method, payment_status, customer_id, redeemed_points))
    sale_id = c.lastrowid

    # 2. Insert into Sale_Items, update stock, and calculate points
    earned_points = 0
    for item in items:
        product_id = item['id']
        qty = item['qty']
        price = item['price']
        item_type = item.get('type', '')
        
        if item_type == 'Brewed Drink':
            earned_points += qty
        
        c.execute('INSERT INTO Sale_Items (sale_id, product_id, qty, price) VALUES (?, ?, ?, ?)',
                  (sale_id, product_id, qty, price))
        
        # Deduct stock if it is a retail product (Brewed drinks might not use stock, but if they do, we'll keep the logic. Let's assume Retail only for now)
        c.execute('UPDATE Products_Services SET stock_qty = stock_qty - ? WHERE id = ? AND type = "Retail"',
                  (qty, product_id))

    # Adjust earned points if customer redeemed points for free drinks (10 points = 1 free drink)
    if redeemed_points >= 10:
        free_drinks = redeemed_points // 10
        earned_points = max(0, earned_points - free_drinks)

    # 3. Add/subtract points to customer if applicable
    if customer_id and (earned_points > 0 or redeemed_points > 0):
        c.execute('UPDATE Customers SET points = points + ? - ? WHERE id = ?', (earned_points, redeemed_points, customer_id))

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
        # Return stock for all product types except 'Service'
        c.execute("UPDATE Products_Services SET stock_qty = stock_qty + ? WHERE id = ? AND type != 'Service'",
                  (item['qty'], item['product_id']))
                  
    # Mark as voided
    c.execute("UPDATE Sales SET payment_status = 'ยกเลิกบิล', total_amount = 0 WHERE id = ?", (sale_id,))
    
    conn.commit()
    conn.close()
    return jsonify({"message": "Sale voided successfully"})

# --- Purchasing / Procurement ---
@app.route('/api/purchases', methods=['GET'])
def get_purchases():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    conn = get_db_connection()
    query = "SELECT * FROM Purchases WHERE 1=1"
    params = []
    
    if start_date and end_date:
        query += " AND timestamp >= ? AND timestamp <= ?"
        params.extend([f"{start_date} 00:00:00", f"{end_date} 23:59:59"])
        
    query += " ORDER BY timestamp DESC LIMIT 50"
    
    purchases = conn.execute(query, params).fetchall()
    
    result = []
    for p in purchases:
        purchase = dict(p)
        items = conn.execute('''
            SELECT pi.*, ps.name 
            FROM Purchase_Items pi 
            JOIN Products_Services ps ON pi.product_id = ps.id 
            WHERE pi.purchase_id = ?
        ''', (p['id'],)).fetchall()
        purchase['items'] = [dict(i) for i in items]
        result.append(purchase)
        
    conn.close()
    return jsonify(result)

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
        
        # Calculate Weighted Average Cost (ถัวเฉลี่ย)
        prod = c.execute('SELECT stock_qty, cost FROM Products_Services WHERE id = ?', (product_id,)).fetchone()
        if prod:
            old_qty = prod['stock_qty']
            if old_qty < 0:
                old_qty = 0  # Ignore negative stock in cost calculation
            old_cost = prod['cost']
            
            new_qty = old_qty + qty
            if new_qty > 0:
                new_avg_cost = ((old_qty * old_cost) + (qty * cost)) / new_qty
            else:
                new_avg_cost = cost
                
            c.execute('UPDATE Products_Services SET stock_qty = ?, cost = ? WHERE id = ?',
                      (new_qty, new_avg_cost, product_id))
    
    conn.commit()
    conn.close()
    return jsonify({"message": "Purchase completed", "purchase_id": purchase_id}), 201

# --- Phase 3: Job Orders ---
@app.route('/api/jobs', methods=['GET'])
def get_jobs():
    conn = get_db_connection()
    jobs = conn.execute("SELECT * FROM Job_Orders WHERE status NOT IN ('ส่งมอบแล้ว', 'ยกเลิก') ORDER BY timestamp DESC").fetchall()
    conn.close()
    return jsonify([dict(ix) for ix in jobs])

@app.route('/api/jobs', methods=['POST'])
def add_job():
    data = request.get_json()
    customer_name = data.get('customer_name')
    details = data.get('details')
    status = data.get('status', 'รอสินค้า')
    
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

@app.route('/api/jobs/<int:job_id>/complete', methods=['POST'])
def complete_job(job_id):
    data = request.get_json()
    total_amount = data.get('total_amount', 0)
    discount = data.get('discount', 0)
    payment_method = data.get('payment_method', 'Cash')
    items = data.get('items', [])
    
    conn = get_db_connection()
    c = conn.cursor()
    
    # Update job status
    c.execute("UPDATE Job_Orders SET status = 'ส่งมอบแล้ว' WHERE id = ?", (job_id,))
    
    job = c.execute("SELECT * FROM Job_Orders WHERE id = ?", (job_id,)).fetchone()
    
    # Create Sale
    c.execute('''
        INSERT INTO Sales (total_amount, discount, payment_method, payment_status, customer_id) 
        VALUES (?, ?, ?, ?, ?)
    ''', (total_amount, discount, payment_method, 'Paid', None))
    sale_id = c.lastrowid
    
    if items:
        # If user scanned items, insert them and deduct stock
        for item in items:
            prod_id = item['id']
            qty = item['qty']
            price = item['price']
            
            c.execute('''
                INSERT INTO Sale_Items (sale_id, product_id, qty, price)
                VALUES (?, ?, ?, ?)
            ''', (sale_id, prod_id, qty, price))
            
            c.execute('UPDATE Products_Services SET stock_qty = stock_qty - ? WHERE id = ?', (qty, prod_id))
    else:
        # Fallback if no items scanned: use generic service
        prod = c.execute("SELECT id FROM Products_Services WHERE name = 'งานบริการ (คิวงาน)'").fetchone()
        if not prod:
            c.execute('''
                INSERT INTO Products_Services (name, type, price, cost) 
                VALUES ('งานบริการ (คิวงาน)', 'Service', 0, 0)
            ''')
            prod_id = c.lastrowid
        else:
            prod_id = prod['id']
            
        c.execute('''
            INSERT INTO Sale_Items (sale_id, product_id, qty, price)
            VALUES (?, ?, 1, ?)
        ''', (sale_id, prod_id, total_amount + discount))
    
    conn.commit()
    conn.close()
    return jsonify({"message": "Job completed and payment recorded", "sale_id": sale_id})

@app.route('/api/jobs/<int:job_id>/cancel', methods=['POST'])
def cancel_job(job_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("UPDATE Job_Orders SET status = 'ยกเลิก' WHERE id = ?", (job_id,))
    conn.commit()
    conn.close()
    return jsonify({"message": "Job cancelled"})

# --- Phase 3: Expenses ---
@app.route('/api/expenses', methods=['GET'])
def get_expenses():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    conn = get_db_connection()
    
    date_filter = ""
    params = []
    
    if start_date and end_date:
        date_filter = " AND timestamp >= ? AND timestamp <= ?"
        # We need to provide the params twice, once for Expenses, once for Purchases
        params.extend([f"{start_date} 00:00:00", f"{end_date} 23:59:59"])
        params.extend([f"{start_date} 00:00:00", f"{end_date} 23:59:59"])
        
    query = f"""
        SELECT id, timestamp, description, amount
        FROM Expenses
        WHERE 1=1 {date_filter}
        
        UNION ALL
        
        SELECT id, timestamp, 'ซื้อสินค้าเข้าสต๊อก (PO #' || id || ')' as description, total_amount as amount
        FROM Purchases
        WHERE 1=1 {date_filter}
        
        ORDER BY timestamp DESC
    """
    
    expenses = conn.execute(query, params).fetchall()
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
    customers = conn.execute('''
        SELECT c.*, 
               COALESCE((SELECT SUM(total_amount - discount) FROM Sales WHERE customer_id = c.id AND payment_status = 'Unpaid'), 0) as unpaid_amount 
        FROM Customers c 
        ORDER BY c.name
    ''').fetchall()
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
    customer_id = c.lastrowid
    conn.commit()
    conn.close()
    return jsonify({"message": "Customer added", "id": customer_id}), 201

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

@app.route('/api/customers/<int:customer_id>/unpaid_bills', methods=['GET'])
def get_customer_unpaid_bills(customer_id):
    conn = get_db_connection()
    bills = conn.execute('''
        SELECT id, timestamp, total_amount, discount 
        FROM Sales 
        WHERE customer_id = ? AND payment_status = 'Unpaid'
        ORDER BY timestamp ASC
    ''', (customer_id,)).fetchall()
    conn.close()
    return jsonify([dict(ix) for ix in bills])

@app.route('/api/sales/<int:sale_id>/pay', methods=['PUT'])
def pay_bill(sale_id):
    import datetime
    data = request.get_json()
    method = data.get('payment_method')
    conn = get_db_connection()
    
    # Get original bill details
    orig = conn.execute('SELECT * FROM Sales WHERE id = ?', (sale_id,)).fetchone()
    if not orig:
        conn.close()
        return jsonify({'error': 'Not found'}), 404
        
    orig_date = orig['timestamp'].split(' ')[0]
    today_date = datetime.datetime.utcnow().strftime('%Y-%m-%d')
    
    if orig_date == today_date:
        # Same day payment: Just update the original bill to Paid and correct method
        conn.execute('''
            UPDATE Sales 
            SET payment_status = 'Paid', payment_method = ?
            WHERE id = ?
        ''', (method, sale_id))
        new_sale_id = sale_id
    else:
        # Cross-day payment: Update original bill to "Cleared"
        conn.execute('''
            UPDATE Sales 
            SET payment_status = 'เคลียร์แล้ว' 
            WHERE id = ?
        ''', (sale_id,))
        
        # Create a new "Payment" bill for TODAY to record income
        net_total = orig['total_amount'] - orig['discount']
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO Sales (total_amount, discount, payment_method, payment_status, customer_id)
            VALUES (?, 0, ?, 'ชำระบิลค้างชำระ', ?)
        ''', (net_total, method, orig['customer_id']))
        new_sale_id = cursor.lastrowid
        
        # Copy items to the new bill so they show on the receipt
        orig_items = conn.execute('SELECT product_id, qty, price FROM Sale_Items WHERE sale_id = ?', (sale_id,)).fetchall()
        for item in orig_items:
            cursor.execute('''
                INSERT INTO Sale_Items (sale_id, product_id, qty, price)
                VALUES (?, ?, ?, ?)
            ''', (new_sale_id, item['product_id'], item['qty'], item['price']))
    
    conn.commit()
    conn.close()
    return jsonify({'message': 'Paid'})

@app.route('/receipt/<int:sale_id>')
def receipt(sale_id):
    conn = get_db_connection()
    sale = conn.execute('''
        SELECT s.*, c.name as customer_name 
        FROM Sales s 
        LEFT JOIN Customers c ON s.customer_id = c.id 
        WHERE s.id = ?
    ''', (sale_id,)).fetchone()
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
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    conn = get_db_connection()
    
    # Note: total_amount in Sales table is ALREADY the NET amount (after discount).
    # To get Gross Revenue, we must add discount back.
    sales_query = "SELECT SUM(total_amount + discount) as total_revenue FROM Sales WHERE payment_status NOT IN ('ยกเลิกบิล', 'ชำระบิลค้างชำระ')"
    discount_query = "SELECT SUM(discount) as total_discount FROM Sales WHERE payment_status NOT IN ('ยกเลิกบิล', 'ชำระบิลค้างชำระ')"
    cash_query = "SELECT SUM(total_amount) as cash_total FROM Sales WHERE payment_status NOT IN ('ยกเลิกบิล', 'Unpaid', 'Pending') AND payment_method = 'Cash'"
    transfer_query = "SELECT SUM(total_amount) as transfer_total FROM Sales WHERE payment_status NOT IN ('ยกเลิกบิล', 'Unpaid', 'Pending') AND payment_method = 'PromptPay'"
    unpaid_query = "SELECT SUM(total_amount) as unpaid_total FROM Sales WHERE payment_status = 'Unpaid'"
    paid_unpaid_query = "SELECT SUM(total_amount) as paid_unpaid_total FROM Sales WHERE payment_status = 'ชำระบิลค้างชำระ'"
    expenses_query = "SELECT SUM(amount) as total_expenses FROM Expenses WHERE 1=1"
    purchases_query = "SELECT SUM(total_amount) as total_purchases FROM Purchases WHERE 1=1"
    cost_query = """
        SELECT SUM(si.qty * p.cost) as total_cost 
        FROM Sale_Items si 
        JOIN Sales s ON si.sale_id = s.id 
        JOIN Products_Services p ON si.product_id = p.id 
        WHERE s.payment_status NOT IN ('ยกเลิกบิล', 'ชำระบิลค้างชำระ')
    """
    recent_sales_query = "SELECT * FROM Sales WHERE 1=1"
    item_sales_query = """
        SELECT p.name, p.type, SUM(si.qty) as total_qty, SUM(si.qty * si.price) as total_amount
        FROM Sale_Items si
        JOIN Sales s ON si.sale_id = s.id
        JOIN Products_Services p ON si.product_id = p.id
        WHERE s.payment_status NOT IN ('ยกเลิกบิล', 'ชำระบิลค้างชำระ')
    """
    brewed_query = """
        SELECT SUM(si.qty * si.price) as brewed_total
        FROM Sale_Items si
        JOIN Sales s ON si.sale_id = s.id
        JOIN Products_Services p ON si.product_id = p.id
        WHERE s.payment_status NOT IN ('ยกเลิกบิล', 'ชำระบิลค้างชำระ') AND p.type = 'Brewed Drink'
    """
    free_drinks_query = "SELECT SUM(redeemed_points) as total_redeemed FROM Sales WHERE payment_status NOT IN ('ยกเลิกบิล', 'ชำระบิลค้างชำระ')"
    
    params = []
    
    if start_date and end_date:
        # SQLite DATETIME works well with 'YYYY-MM-DD HH:MM:SS'
        # Add time boundaries to cover the full days
        start = f"{start_date} 00:00:00"
        end = f"{end_date} 23:59:59"
        
        date_filter = " AND timestamp >= ? AND timestamp <= ?"
        sales_query += date_filter
        discount_query += date_filter
        cash_query += date_filter
        transfer_query += date_filter
        unpaid_query += date_filter
        paid_unpaid_query += date_filter
        expenses_query += date_filter
        purchases_query += date_filter
        recent_sales_query += date_filter
        free_drinks_query += date_filter
        
        # for join query
        item_sales_query += " AND s.timestamp >= ? AND s.timestamp <= ?"
        brewed_query += " AND s.timestamp >= ? AND s.timestamp <= ?"
        cost_query += " AND s.timestamp >= ? AND s.timestamp <= ?"
        
        # params for each query
        params = [start, end]

    # Total Revenue from Sales (excluding voided)
    sales_result = conn.execute(sales_query, params).fetchone()
    total_revenue = sales_result['total_revenue'] if sales_result['total_revenue'] else 0.0
    
    discount_result = conn.execute(discount_query, params).fetchone()
    total_discount = discount_result['total_discount'] if discount_result['total_discount'] else 0.0
    
    cash_result = conn.execute(cash_query, params).fetchone()
    cash_total = cash_result['cash_total'] if cash_result['cash_total'] else 0.0
    
    transfer_result = conn.execute(transfer_query, params).fetchone()
    transfer_total = transfer_result['transfer_total'] if transfer_result['transfer_total'] else 0.0
    
    unpaid_result = conn.execute(unpaid_query, params).fetchone()
    unpaid_total = unpaid_result['unpaid_total'] if unpaid_result['unpaid_total'] else 0.0
    
    paid_unpaid_result = conn.execute(paid_unpaid_query, params).fetchone()
    paid_unpaid_total = paid_unpaid_result['paid_unpaid_total'] if paid_unpaid_result['paid_unpaid_total'] else 0.0
    
    cost_result = conn.execute(cost_query, params).fetchone()
    total_cost = cost_result['total_cost'] if cost_result['total_cost'] else 0.0
    
    brewed_result = conn.execute(brewed_query, params).fetchone()
    brewed_total = brewed_result['brewed_total'] if brewed_result['brewed_total'] else 0.0
    
    free_drinks_result = conn.execute(free_drinks_query, params).fetchone()
    total_redeemed_pts = free_drinks_result['total_redeemed'] if free_drinks_result['total_redeemed'] else 0
    total_free_drinks = int(total_redeemed_pts / 10)

    # Total Expenses
    expenses_result = conn.execute(expenses_query, params).fetchone()
    total_expenses = expenses_result['total_expenses'] if expenses_result['total_expenses'] else 0.0
    
    purchases_result = conn.execute(purchases_query, params).fetchone()
    total_purchases = purchases_result['total_purchases'] if purchases_result['total_purchases'] else 0.0
    
    # Recent Sales List
    recent_sales_query += " ORDER BY timestamp DESC LIMIT 1000" # Increase limit if filtering by date
    recent_sales = conn.execute(recent_sales_query, params).fetchall()
    
    # Itemized Sales Summary
    item_sales_query += " GROUP BY p.id ORDER BY total_amount DESC"
    item_sales = conn.execute(item_sales_query, params).fetchall()
    
    conn.close()
    
    net_profit = total_revenue - total_expenses
    
    return jsonify({
        "total_revenue": total_revenue,
        "total_discount": total_discount,
        "total_cost": total_cost,
        "total_purchases": total_purchases,
        "cash_total": cash_total,
        "transfer_total": transfer_total,
        "unpaid_total": unpaid_total,
        "paid_unpaid_total": paid_unpaid_total,
        "brewed_total": brewed_total,
        "total_free_drinks": total_free_drinks,
        "total_expenses": total_expenses,
        "net_profit": net_profit,
        "recent_sales": [dict(ix) for ix in recent_sales],
        "item_sales": [dict(ix) for ix in item_sales]
    })

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)
