# pyrefly: ignore [missing-import]
from flask import Flask, jsonify, request, render_template, session, redirect, url_for
import sqlite3

app = Flask(__name__)
app.secret_key = 'pjcopyshop_secret_1234' # Required for session
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
            role TEXT NOT NULL,
            pin TEXT
        )
    ''')
    # Insert default admin user if no users exist
    c.execute('SELECT COUNT(*) FROM Users')
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO Users (username, role, pin) VALUES ('Admin', 'Admin', '1234')")

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
            invoice_no TEXT,
            total_amount REAL NOT NULL,
            discount REAL DEFAULT 0,
            payment_method TEXT NOT NULL,
            split_cash REAL DEFAULT 0,
            split_transfer REAL DEFAULT 0,
            payment_status TEXT DEFAULT 'Paid',
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            customer_id INTEGER,
            redeemed_points INTEGER DEFAULT 0,
            notes TEXT
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
            qty INTEGER DEFAULT 1,
            deposit REAL DEFAULT 0,
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
            expense_type TEXT DEFAULT 'OPEX',
            payment_method TEXT DEFAULT 'Cash',
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
            points INTEGER DEFAULT 0,
            allow_points_with_debt INTEGER DEFAULT 0
        )
    ''')
    
    # Customer Credit (ลูกหนี้)
    c.execute('''
        CREATE TABLE IF NOT EXISTS Customer_Credit (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER,
            sale_id INTEGER,
            amount_due REAL NOT NULL,
            amount_paid REAL DEFAULT 0,
            status TEXT DEFAULT 'Unpaid',
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(customer_id) REFERENCES Customers(id),
            FOREIGN KEY(sale_id) REFERENCES Sales(id)
        )
    ''')

    # BOM (สูตรตัดสต็อก)
    c.execute('''
        CREATE TABLE IF NOT EXISTS BOM (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER,
            raw_material_id INTEGER,
            qty_required REAL NOT NULL,
            FOREIGN KEY(product_id) REFERENCES Products_Services(id),
            FOREIGN KEY(raw_material_id) REFERENCES Products_Services(id)
        )
    ''')

    # Promotions
    c.execute('''
        CREATE TABLE IF NOT EXISTS Promotions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            promo_type TEXT NOT NULL,
            discount_value REAL NOT NULL,
            condition_type TEXT,
            condition_value REAL,
            is_active INTEGER DEFAULT 1
        )
    ''')

    # Business Date (วันเปิดร้าน)
    c.execute('''
        CREATE TABLE IF NOT EXISTS Business_Date (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            current_date TEXT NOT NULL,
            is_closed INTEGER DEFAULT 0,
            starting_cash REAL DEFAULT 0,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

@app.before_request
def require_login():
    allowed_routes = ['login', 'static']
    if request.endpoint not in allowed_routes and 'user_id' not in session:
        return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        pin = request.form.get('pin')
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM Users WHERE pin = ?', (pin,)).fetchone()
        conn.close()
        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            return redirect(url_for('index'))
        else:
            return render_template('login.html', error='รหัส PIN ไม่ถูกต้อง')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/print-barcodes')
def print_barcodes():
    return render_template('print_barcodes.html')

@app.route('/inventory')
def inventory():
    return render_template('inventory.html')



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

@app.route('/stock-count')
def stock_count():
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM Products_Services WHERE is_active = 1 AND type != 'Service' ORDER BY type ASC, name ASC").fetchall()
    conn.close()
    
    type_map = {
        "Service": "งานบริการ",
        "Stationery": "เครื่องเขียน",
        "Gift shop": "กิ๊ฟช๊อป",
        "Dolls": "ตุ๊กตา",
        "Toys": "ของเล่น",
        "Perfume": "น้ำหอม",
        "IT equipment": "อุปกรณ์ IT",
        "Brewed Drink": "เครื่องดื่มชง",
        "Water": "น้ำเปล่า",
        "Soft drinks": "น้ำอัดลม",
        "Retail": "สินค้าปลีก"
    }
    
    grouped_products = {}
    for r in rows:
        ptype = r['type']
        thai_type = type_map.get(ptype, ptype)
        if thai_type not in grouped_products:
            grouped_products[thai_type] = []
        
        # We need to map the type inside the dict too so it renders correctly in the table column
        row_dict = dict(r)
        row_dict['type_th'] = thai_type
        grouped_products[thai_type].append(row_dict)
        
    return render_template('stock_count.html', grouped_products=grouped_products)

@app.route('/stock-checking')
def stock_checking():
    return render_template('stock_checking.html')

@app.route('/api/stock-counts', methods=['GET'])
def get_stock_counts():
    conn = get_db_connection()
    counts = conn.execute("SELECT * FROM Stock_Counts ORDER BY id DESC").fetchall()
    conn.close()
    return jsonify([dict(x) for x in counts])

@app.route('/api/stock-counts/<int:id>', methods=['GET'])
def get_stock_count_details(id):
    conn = get_db_connection()
    count_data = conn.execute("SELECT * FROM Stock_Counts WHERE id = ?", (id,)).fetchone()
    if not count_data:
        return jsonify({'error': 'Not found'}), 404
        
    items = conn.execute('''
        SELECT c.*, p.name, p.barcode, p.type 
        FROM Stock_Count_Items c
        JOIN Products_Services p ON c.product_id = p.id
        WHERE c.count_id = ?
    ''', (id,)).fetchall()
    conn.close()
    
    return jsonify({
        'count': dict(count_data),
        'items': [dict(x) for x in items]
    })

@app.route('/api/stock-counts', methods=['POST'])
def submit_stock_count():
    data = request.get_json()
    notes = data.get('notes', '')
    items = data.get('items', [])
    
    if not items:
        return jsonify({'error': 'No items provided'}), 400
        
    conn = get_db_connection()
    try:
        # Create Count session
        cursor = conn.execute(
            "INSERT INTO Stock_Counts (notes) VALUES (?)", 
            (notes,)
        )
        count_id = cursor.lastrowid
        
        # Insert Items and update stock
        for item in items:
            product_id = item['product_id']
            system_qty = item['system_qty']
            counted_qty = item['counted_qty']
            variance = item['variance']
            
            conn.execute('''
                INSERT INTO Stock_Count_Items (count_id, product_id, system_qty, counted_qty, variance)
                VALUES (?, ?, ?, ?, ?)
            ''', (count_id, product_id, system_qty, counted_qty, variance))
            
            if variance != 0:
                conn.execute(
                    "UPDATE Products_Services SET stock_qty = ? WHERE id = ?",
                    (counted_qty, product_id)
                )
                
        conn.commit()
        return jsonify({'success': True, 'count_id': count_id})
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

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
    
    # Record expense (OPEX)
    prod = c.execute('SELECT name, cost FROM Products_Services WHERE id = ?', (product_id,)).fetchone()
    if prod:
        total_cost = prod['cost'] * qty
        desc = f"ตัดของเสีย: {prod['name']} จำนวน {qty} ({reason})"
        c.execute('INSERT INTO Expenses (description, amount, expense_type, payment_method) VALUES (?, ?, ?, ?)',
                  (desc, total_cost, 'OPEX', 'None'))
    
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
    manual_discount = max(0, float(data.get('discount', 0)))
    payment_method = data.get('payment_method', 'Cash')
    payment_status = data.get('payment_status', 'Paid')
    split_cash = data.get('split_cash', 0.0)
    split_transfer = data.get('split_transfer', 0.0)
    notes = data.get('notes', '')
    customer_id = data.get('customer_id')
    redeemed_points = int(data.get('redeemed_points', 0))
    items = data.get('items', [])

    conn = get_db_connection()
    c = conn.cursor()
    
    # Calculate Total Amount and apply Round Up (ปัดเศษขึ้นเสมอ)
    import math
    subtotal = sum(item['price'] * item['qty'] for item in items)
    
    # 0. Check Stock
    for item in items:
        if item.get('type') != 'Service':
            p = c.execute('SELECT stock_qty FROM Products_Services WHERE id = ?', (item['id'],)).fetchone()
            if p and p['stock_qty'] < item['qty']:
                conn.close()
                return jsonify({"message": f"สินค้า {item.get('name', 'Product')} มีไม่พอในสต๊อก (มีอยู่ {p['stock_qty']})"}), 400

    loyalty_discount = 0

    if redeemed_points:
        if redeemed_points % 10 != 0 or not customer_id:
            conn.close()
            return jsonify({"message": "Invalid loyalty redemption"}), 400

        customer = c.execute('SELECT points FROM Customers WHERE id = ?', (customer_id,)).fetchone()
        if not customer or customer['points'] < redeemed_points:
            conn.close()
            return jsonify({"message": "Not enough points"}), 400
            
        # Frontend already applies discount to item prices, so loyalty_discount is 0 here

    discount = manual_discount + loyalty_discount
    total_amount = math.ceil(max(0, subtotal - discount))
    
    # Generate Invoice No (INVYYMM-XXXX)
    import datetime
    now = datetime.datetime.now()
    yy = str(now.year + 543)[2:]
    mm = f"{now.month:02d}"
    prefix = f"INV{yy}{mm}-"
    last_inv = c.execute("SELECT invoice_no FROM Sales WHERE invoice_no LIKE ? ORDER BY invoice_no DESC LIMIT 1", (prefix + '%',)).fetchone()
    seq = int(last_inv['invoice_no'].split('-')[1]) + 1 if last_inv else 1
    invoice_no = f"{prefix}{seq:04d}"
    
    # 1. Insert into Sales
    c.execute('''
        INSERT INTO Sales (invoice_no, total_amount, discount, payment_method, split_cash, split_transfer, payment_status, customer_id, redeemed_points, notes) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (invoice_no, total_amount, discount, payment_method, split_cash, split_transfer, payment_status, customer_id, redeemed_points, notes))
    sale_id = c.lastrowid
    
    # Insert into Customer_Credit if Unpaid (or Hold, though scope says Unpaid means Credit)
    if payment_status == 'Unpaid' and customer_id:
        c.execute('''
            INSERT INTO Customer_Credit (customer_id, sale_id, amount_due, amount_paid, status)
            VALUES (?, ?, ?, 0, 'Unpaid')
        ''', (customer_id, sale_id, total_amount))

    # 2. Insert into Sale_Items, update stock, and calculate points
    earned_points = 0
    for item in items:
        product_id = item['id']
        qty = item['qty']
        price = item['price']
        item_type = item.get('type', '')
        
        c.execute('INSERT INTO Sale_Items (sale_id, product_id, qty, price) VALUES (?, ?, ?, ?)',
                  (sale_id, product_id, qty, price))
                  
        if payment_status != 'Hold':
            if item_type == 'Brewed Drink' and not item.get('is_redeemed'):
                earned_points += qty
            
            # Check BOM for Raw Materials deduction
            bom_items = c.execute('SELECT raw_material_id, qty_required FROM BOM WHERE product_id = ?', (product_id,)).fetchall()
            if bom_items:
                for b in bom_items:
                    raw_qty = b['qty_required'] * qty
                    c.execute('UPDATE Products_Services SET stock_qty = stock_qty - ? WHERE id = ?', (raw_qty, b['raw_material_id']))
            else:
                # Normal stock deduction if no BOM and it is Retail
                if item_type != 'Service':
                    c.execute('UPDATE Products_Services SET stock_qty = stock_qty - ? WHERE id = ?', (qty, product_id))

    if payment_status != 'Hold':
        # 3. Add/subtract points to customer if applicable
        if customer_id and (earned_points > 0 or redeemed_points > 0):
            c.execute('UPDATE Customers SET points = points + ? - ? WHERE id = ?', (earned_points, redeemed_points, customer_id))
            if redeemed_points > 0:
                c.execute('UPDATE Customers SET allow_points_with_debt = 0 WHERE id = ?', (customer_id,))

    conn.commit()
    conn.close()
    return jsonify({"message": "Sale completed successfully", "sale_id": sale_id,
                    "loyalty_discount": loyalty_discount}), 201


@app.route('/api/sales/held', methods=['GET'])
def get_held_sales():
    conn = get_db_connection()
    c = conn.cursor()
    sales = c.execute("SELECT * FROM Sales WHERE payment_status = 'Hold' ORDER BY timestamp DESC").fetchall()
    held_list = []
    for s in sales:
        s_dict = dict(s)
        items = c.execute('''
            SELECT si.*, p.name, p.barcode, p.type 
            FROM Sale_Items si 
            JOIN Products_Services p ON si.product_id = p.id 
            WHERE si.sale_id = ?
        ''', (s['id'],)).fetchall()
        s_dict['items'] = [dict(i) for i in items]
        held_list.append(s_dict)
    conn.close()
    return jsonify(held_list)

@app.route('/api/sales/held/<int:sale_id>', methods=['DELETE'])
def pull_held_sale(sale_id):
    conn = get_db_connection()
    c = conn.cursor()
    
    sale = c.execute("SELECT payment_status FROM Sales WHERE id = ?", (sale_id,)).fetchone()
    if not sale or sale['payment_status'] != 'Hold':
        conn.close()
        return jsonify({"message": "Invalid held sale"}), 400
        
    c.execute("DELETE FROM Sale_Items WHERE sale_id = ?", (sale_id,))
    c.execute("DELETE FROM Sales WHERE id = ?", (sale_id,))
    
    conn.commit()
    conn.close()
    return jsonify({"message": "Held sale deleted successfully"})

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
    payment_method = data.get('payment_method', 'Cash')
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
        INSERT INTO Purchases (supplier_name, subtotal, vat_amount, total_amount, payment_method) 
        VALUES (?, ?, ?, ?, ?)
    ''', (supplier_name, subtotal, vat_amount, total_amount, payment_method))
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
    qty = data.get('qty', 1)
    deposit = data.get('deposit', 0)
    status = data.get('status', 'รอสินค้า')
    
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('INSERT INTO Job_Orders (customer_name, details, qty, deposit, status) VALUES (?, ?, ?, ?, ?)', (customer_name, details, qty, deposit, status))
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
    payment_status = data.get('payment_status', 'Paid')
    split_cash = data.get('split_cash', 0)
    split_transfer = data.get('split_transfer', 0)
    items = data.get('items', [])
    
    conn = get_db_connection()
    c = conn.cursor()
    
    # Check Stock for scanned items
    if items:
        for item in items:
            if item.get('type') != 'Service':
                p = c.execute('SELECT stock_qty, name FROM Products_Services WHERE id = ?', (item['id'],)).fetchone()
                if p and p['stock_qty'] < item['qty']:
                    conn.close()
                    return jsonify({"message": f"สินค้า {p['name']} มีไม่พอในสต๊อก (มีอยู่ {p['stock_qty']})"}), 400

    # Update job status
    c.execute("UPDATE Job_Orders SET status = 'ส่งมอบแล้ว' WHERE id = ?", (job_id,))
    
    job = c.execute("SELECT * FROM Job_Orders WHERE id = ?", (job_id,)).fetchone()
    
    # Resolve customer_id from name
    cust = c.execute("SELECT id FROM Customers WHERE name = ?", (job['customer_name'],)).fetchone()
    customer_id = cust['id'] if cust else None
    
    # Generate Invoice No
    import datetime
    now = datetime.datetime.now()
    yy = str(now.year + 543)[2:]
    mm = f"{now.month:02d}"
    prefix = f"INV{yy}{mm}-"
    last_inv = c.execute("SELECT invoice_no FROM Sales WHERE invoice_no LIKE ? ORDER BY invoice_no DESC LIMIT 1", (prefix + '%',)).fetchone()
    seq = int(last_inv['invoice_no'].split('-')[1]) + 1 if last_inv else 1
    invoice_no = f"{prefix}{seq:04d}"
    
    notes = f"จากบิลจองงาน #JOB-{job_id:04d}"
    
    # Create Sale
    c.execute('''
        INSERT INTO Sales (invoice_no, total_amount, discount, payment_method, split_cash, split_transfer, payment_status, customer_id, notes) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (invoice_no, total_amount, discount, payment_method, split_cash, split_transfer, payment_status, customer_id, notes))
    sale_id = c.lastrowid
    
    if payment_status == 'Unpaid' and customer_id:
        c.execute('''
            INSERT INTO Customer_Credit (customer_id, sale_id, amount_due, amount_paid, status)
            VALUES (?, ?, ?, 0, 'Unpaid')
        ''', (customer_id, sale_id, total_amount))
    
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
        SELECT id, timestamp, description, amount, expense_type, payment_method
        FROM Expenses
        WHERE 1=1 {date_filter}
        
        UNION ALL
        
        SELECT id, timestamp, 'ซื้อสินค้าเข้าสต๊อก (PO #' || id || ')' as description, total_amount as amount, 'OPEX' as expense_type, 'N/A' as payment_method
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
    expense_type = data.get('expense_type', 'OPEX')
    payment_method = data.get('payment_method', 'Cash')
    
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('INSERT INTO Expenses (description, amount, expense_type, payment_method) VALUES (?, ?, ?, ?)', (description, amount, expense_type, payment_method))
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

@app.route('/api/customers/<int:customer_id>/allow_points', methods=['PUT'])
def toggle_allow_points(customer_id):
    data = request.get_json()
    allow = data.get('allow', 0)
    conn = get_db_connection()
    conn.execute("UPDATE Customers SET allow_points_with_debt = ? WHERE id = ?", (allow, customer_id))
    conn.commit()
    conn.close()
    return jsonify({"message": "Settings updated"})

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
        SELECT s.id, s.timestamp, cc.amount_due - cc.amount_paid as remaining_amount, cc.amount_paid
        FROM Sales s
        JOIN Customer_Credit cc ON s.id = cc.sale_id
        WHERE s.customer_id = ? AND cc.status = 'Unpaid'
        ORDER BY s.timestamp ASC
    ''', (customer_id,)).fetchall()
    conn.close()
    return jsonify([dict(ix) for ix in bills])

@app.route('/api/sales/<int:sale_id>/pay', methods=['PUT'])
def pay_bill(sale_id):
    import datetime
    data = request.get_json() or {}
    method = data.get('payment_method', 'Cash')
    split_cash = float(data.get('split_cash', 0.0))
    split_transfer = float(data.get('split_transfer', 0.0))
    
    if method not in ('Cash', 'PromptPay', 'Split'):
        return jsonify({'error': 'Invalid payment method'}), 400
    conn = get_db_connection()
    
    # Get original bill details
    orig = conn.execute('SELECT * FROM Sales WHERE id = ?', (sale_id,)).fetchone()
    if not orig:
        conn.close()
        return jsonify({'error': 'Not found'}), 404
        
    orig_date = orig['timestamp'].split(' ')[0]
    today_date = datetime.datetime.utcnow().strftime('%Y-%m-%d')
    
    credit = conn.execute('SELECT * FROM Customer_Credit WHERE sale_id = ?', (sale_id,)).fetchone()
    if not credit:
        conn.close()
        return jsonify({'error': 'No credit record found'}), 404
        
    remaining = credit['amount_due'] - credit['amount_paid']
    
    pay_amount = float(data.get('pay_amount', remaining))
    if pay_amount > remaining:
        pay_amount = remaining
        
    new_paid = credit['amount_paid'] + pay_amount
    is_fully_paid = new_paid >= credit['amount_due']
    
    cursor = conn.cursor()
    
    if is_fully_paid:
        cursor.execute("UPDATE Customer_Credit SET amount_paid = amount_due, status = 'Paid' WHERE sale_id = ?", (sale_id,))
        if orig_date == today_date and pay_amount == remaining and credit['amount_paid'] == 0:
            # Same day full payment in one go: Just update original bill
            cursor.execute('''
                UPDATE Sales 
                SET payment_status = 'Paid', payment_method = ?, split_cash = ?, split_transfer = ?
                WHERE id = ?
            ''', (method, split_cash, split_transfer, sale_id))
            new_sale_id = sale_id
        else:
            # Cross-day or it was partially paid before
            cursor.execute("UPDATE Sales SET payment_status = 'เคลียร์แล้ว' WHERE id = ?", (sale_id,))
    else:
        cursor.execute("UPDATE Customer_Credit SET amount_paid = ? WHERE sale_id = ?", (new_paid, sale_id))
        
    if not (is_fully_paid and orig_date == today_date and pay_amount == remaining and credit['amount_paid'] == 0):
        # Create a new "Payment" bill for TODAY to record income
        cursor.execute('''
            INSERT INTO Sales (total_amount, discount, payment_method, split_cash, split_transfer, payment_status, customer_id)
            VALUES (?, 0, ?, ?, ?, 'ชำระบิลค้างชำระ', ?)
        ''', (pay_amount, method, split_cash, split_transfer, orig['customer_id']))
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
    # Since there is no discount deduction line in P&L, we use total_amount as Net Sales.
    sales_query = "SELECT SUM(total_amount) as total_revenue FROM Sales WHERE payment_status NOT IN ('ยกเลิกบิล', 'ชำระบิลค้างชำระ')"
    discount_query = "SELECT SUM(discount) as total_discount FROM Sales WHERE payment_status NOT IN ('ยกเลิกบิล', 'ชำระบิลค้างชำระ')"
    cash_query = "SELECT SUM(CASE WHEN payment_method = 'Cash' THEN total_amount WHEN payment_method = 'Split' THEN split_cash ELSE 0 END) as cash_total FROM Sales WHERE payment_status NOT IN ('ยกเลิกบิล', 'Unpaid', 'Pending', 'Hold')"
    transfer_query = "SELECT SUM(CASE WHEN payment_method IN ('PromptPay', 'Credit Card') THEN total_amount WHEN payment_method = 'Split' THEN split_transfer ELSE 0 END) as transfer_total FROM Sales WHERE payment_status NOT IN ('ยกเลิกบิล', 'Unpaid', 'Pending', 'Hold')"
    unpaid_query = "SELECT SUM(total_amount) as unpaid_total FROM Sales WHERE payment_status = 'Unpaid'"
    paid_unpaid_query = "SELECT SUM(total_amount) as paid_unpaid_total FROM Sales WHERE payment_status = 'ชำระบิลค้างชำระ'"
    expenses_query = "SELECT SUM(amount) as total_expenses FROM Expenses WHERE expense_type = 'OPEX'"
    owner_draw_query = "SELECT SUM(amount) as total_owner_draw FROM Expenses WHERE expense_type = 'Owner Draw'"
    purchases_query = "SELECT SUM(total_amount) as total_purchases FROM Purchases WHERE 1=1"
    cost_query = """
        SELECT SUM(si.qty * p.cost) as total_cost 
        FROM Sale_Items si 
        JOIN Sales s ON si.sale_id = s.id 
        JOIN Products_Services p ON si.product_id = p.id 
        WHERE s.payment_status NOT IN ('ยกเลิกบิล', 'ชำระบิลค้างชำระ')
        AND p.type != 'Brewed Drink'
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
    
    adjustment_query = """
        SELECT SUM(c.variance * p.cost) as total_adjustment
        FROM Stock_Count_Items c
        JOIN Stock_Counts sc ON c.count_id = sc.id
        JOIN Products_Services p ON c.product_id = p.id
        WHERE 1=1
    """
    
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
        owner_draw_query += date_filter
        purchases_query += date_filter
        recent_sales_query += date_filter
        free_drinks_query += date_filter
        
        # for join query
        item_sales_query += " AND s.timestamp >= ? AND s.timestamp <= ?"
        brewed_query += " AND s.timestamp >= ? AND s.timestamp <= ?"
        cost_query += " AND s.timestamp >= ? AND s.timestamp <= ?"
        adjustment_query += " AND sc.count_date >= ? AND sc.count_date <= ?"
        
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
    
    owner_draw_result = conn.execute(owner_draw_query, params).fetchone()
    total_owner_draw = owner_draw_result['total_owner_draw'] if owner_draw_result['total_owner_draw'] else 0.0
    
    purchases_result = conn.execute(purchases_query, params).fetchone()
    total_purchases = purchases_result['total_purchases'] if purchases_result['total_purchases'] else 0.0
    
    adj_result = conn.execute(adjustment_query, params).fetchone()
    total_adjustment = adj_result['total_adjustment'] if adj_result['total_adjustment'] else 0.0
    
    # Recent Sales List
    recent_sales_query += " ORDER BY timestamp DESC LIMIT 1000" # Increase limit if filtering by date
    recent_sales = conn.execute(recent_sales_query, params).fetchall()
    
    # Itemized Sales Summary
    item_sales_query += " GROUP BY p.id ORDER BY total_amount DESC"
    item_sales = conn.execute(item_sales_query, params).fetchall()
    
    conn.close()
    
    net_profit = total_revenue - total_expenses + total_adjustment
    
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
        "total_owner_draw": total_owner_draw,
        "total_adjustment": total_adjustment,
        "net_profit": net_profit,
        "recent_sales": [dict(ix) for ix in recent_sales],
        "item_sales": [dict(ix) for ix in item_sales]
    })

# --- Phase 7: Backup ---

from flask import send_file

@app.route('/api/backup/local', methods=['GET'])
def backup_local():
    import csv, zipfile, io
    import datetime
    
    conn = get_db_connection()
    tables = ['Products_Services', 'Customers', 'Sales', 'Sale_Items', 'Purchases', 'Purchase_Items', 'Expenses', 'Stock_WriteOffs', 'Customer_Credit']
    
    memory_file = io.BytesIO()
    with zipfile.ZipFile(memory_file, 'w') as zf:
        # Also backup the sqlite file itself for complete backup
        try:
            if os.path.exists(DB_FILE):
                with open(DB_FILE, 'rb') as f:
                    db_data = f.read()
                    zf.writestr('pjcopy.db', db_data)
                    zf.writestr('xerox.db', db_data)
        except Exception:
            pass
            
        for table in tables:
            rows = conn.execute(f"SELECT * FROM {table}").fetchall()
            if not rows:
                continue
            
            csv_buffer = io.StringIO()
            writer = csv.writer(csv_buffer)
            writer.writerow(rows[0].keys())
            for row in rows:
                writer.writerow(row)
                
            zf.writestr(f"{table}.csv", csv_buffer.getvalue())
            
    conn.close()
    memory_file.seek(0)
    
    now_str = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'pjcopy_backup_{now_str}.zip'
    
    return send_file(
        memory_file,
        mimetype='application/zip',
        as_attachment=True,
        download_name=filename
    )

@app.route('/api/backup/gdrive', methods=['POST'])
def backup_gdrive():
    import csv, zipfile, io
    import datetime
    try:
        from gdrive_upload import upload_to_drive
    except ImportError:
        return jsonify({"message": "Server error: Google API client libraries not installed."}), 500
        
    conn = get_db_connection()
    tables = ['Products_Services', 'Customers', 'Sales', 'Sale_Items', 'Purchases', 'Purchase_Items', 'Expenses', 'Stock_WriteOffs', 'Customer_Credit']
    
    memory_file = io.BytesIO()
    with zipfile.ZipFile(memory_file, 'w') as zf:
        # Also backup the sqlite file itself for complete backup
        try:
            if os.path.exists(DB_FILE):
                with open(DB_FILE, 'rb') as f:
                    db_data = f.read()
                    zf.writestr('pjcopy.db', db_data)
                    zf.writestr('xerox.db', db_data)
        except Exception:
            pass
            
        for table in tables:
            rows = conn.execute(f"SELECT * FROM {table}").fetchall()
            if not rows:
                continue
            
            csv_buffer = io.StringIO()
            writer = csv.writer(csv_buffer)
            writer.writerow(rows[0].keys())
            for row in rows:
                writer.writerow(row)
                
            zf.writestr(f"{table}.csv", csv_buffer.getvalue())
            
    conn.close()
    memory_file.seek(0)
    
    now_str = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'pjcopy_backup_{now_str}.zip'
    
    try:
        link = upload_to_drive(memory_file, filename)
        return jsonify({"message": "อัพโหลดไปยัง Google Drive สำเร็จ!", "link": link})
    except Exception as e:
        return jsonify({"message": f"Error: {str(e)}"}), 500

@app.route('/api/restore', methods=['POST'])
def restore_backup():
    import zipfile, io, os, shutil
    
    if 'file' not in request.files:
        return jsonify({"message": "No file uploaded"}), 400
        
    file = request.files['file']
    if file.filename == '':
        return jsonify({"message": "No file selected"}), 400
        
    try:
        memory_file = io.BytesIO(file.read())
        with zipfile.ZipFile(memory_file, 'r') as zf:
            db_entry = None
            for candidate in ['pjcopy.db', 'xerox.db']:
                if candidate in zf.namelist():
                    db_entry = candidate
                    break
                    
            if not db_entry:
                return jsonify({"message": "ไฟล์ Backup ไม่ถูกต้อง (ไม่พบไฟล์ฐานข้อมูล)"}), 400
                
            if os.path.exists(DB_FILE):
                shutil.copy2(DB_FILE, 'xerox_db.bak')
                
            with open(DB_FILE, 'wb') as f:
                f.write(zf.read(db_entry))
                
        return jsonify({"message": "เรียกคืนข้อมูลสำเร็จ! กรุณารีเฟรชหน้าเว็บ"})
    except Exception as e:
        if os.path.exists('xerox_db.bak'):
            shutil.copy2('xerox_db.bak', DB_FILE)
        return jsonify({"message": f"Error: {str(e)}"}), 500

@app.route('/api/shutdown', methods=['POST'])
def shutdown_server():
    import os, signal
    # Send interrupt signal to the current process to shut it down gracefully
    os.kill(os.getpid(), signal.SIGINT)
    return jsonify({"message": "กำลังปิดระบบ..."})

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)
