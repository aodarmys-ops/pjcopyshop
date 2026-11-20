# pyrefly: ignore [missing-import]
from flask import g, has_app_context, has_request_context, Flask, jsonify, request, render_template, session, redirect, url_for
from functools import wraps
import sqlite3
import os
import re
import math
import datetime
import random
import csv
import zipfile
import io
import shutil
import signal
import tempfile
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'pjcopyshop_secret_1234')  # Required for session

try:
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address
    limiter = Limiter(
        get_remote_address,
        app=app,
        default_limits=["200 per day", "50 per hour"],
        storage_uri="memory://"
    )
except ImportError:
    # Fallback if flask-limiter is not installed yet
    class DummyLimiter:
        def limit(self, *args, **kwargs):
            def decorator(f):
                return f
            return decorator
    limiter = DummyLimiter()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_FILE = os.environ.get('DB_FILE', os.path.join(BASE_DIR, 'xerox.db'))

def get_db_connection():
    def setup_conn(conn):
        conn.row_factory = sqlite3.Row
        conn.execute('PRAGMA foreign_keys = ON;')
        conn.execute('PRAGMA journal_mode = WAL;')
        conn.execute('PRAGMA synchronous = NORMAL;')
        conn.execute('PRAGMA temp_store = MEMORY;')
        conn.execute('PRAGMA busy_timeout = 5000;')
        return conn

    if has_app_context():
        if 'db' not in g:
            g.db = setup_conn(sqlite3.connect(DB_FILE, timeout=5.0))
        return g.db
    else:
        return setup_conn(sqlite3.connect(DB_FILE, timeout=5.0))

@app.teardown_appcontext
def close_connection(exception):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def generate_datatables_response(query_base, request_args, search_cols, order_cols):
    conn = get_db_connection()
    start = int(request_args.get('start', 0))
    length = int(request_args.get('length', 10))
    search_value = request_args.get('search[value]', '').strip()
    
    total_query = f"SELECT COUNT(*) as count FROM ({query_base})"
    total_records = conn.execute(total_query).fetchone()['count']
    
    search_clause = ""
    params = []
    if search_value:
        clauses = [f"{col} LIKE ?" for col in search_cols]
        search_clause = " WHERE " + " OR ".join(clauses)
        params.extend([f"%{search_value}%"] * len(search_cols))
        
    filtered_query = f"SELECT COUNT(*) as count FROM ({query_base}) {search_clause}"
    filtered_records = conn.execute(filtered_query, params).fetchone()['count']
    
    order_col_idx = request_args.get('order[0][column]')
    order_dir = request_args.get('order[0][dir]', 'asc').lower()
    order_clause = ""
    if order_col_idx is not None and order_col_idx.isdigit():
        idx = int(order_col_idx)
        if idx < len(order_cols) and order_cols[idx]:
            if order_dir not in ['asc', 'desc']: order_dir = 'asc'
            order_clause = f" ORDER BY {order_cols[idx]} {order_dir.upper()}"
            
    final_query = f"SELECT * FROM ({query_base}) {search_clause} {order_clause} LIMIT ? OFFSET ?"
    params.extend([length, start])
    
    rows = conn.execute(final_query, params).fetchall()
    conn.close()
    
    return jsonify({
        "draw": int(request_args.get('draw', 1)),
        "recordsTotal": total_records,
        "recordsFiltered": filtered_records,
        "data": [dict(ix) for ix in rows]
    })

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
        c.execute("INSERT INTO Users (username, role, pin) VALUES ('Admin', 'Admin', ?)",
                  (generate_password_hash('1234'),))

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
            cost_price REAL DEFAULT 0,
            FOREIGN KEY(sale_id) REFERENCES Sales(id),
            FOREIGN KEY(product_id) REFERENCES Products_Services(id)
        )
    ''')
    
    # Auto-migration for cost_price
    columns = [col['name'] for col in c.execute('PRAGMA table_info(Sale_Items)').fetchall()]
    if 'cost_price' not in columns:
        c.execute('ALTER TABLE Sale_Items ADD COLUMN cost_price REAL DEFAULT 0')
    # Purchases
    c.execute('''
        CREATE TABLE IF NOT EXISTS Purchases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            supplier_name TEXT,
            subtotal REAL NOT NULL,
            vat_amount REAL DEFAULT 0,
            total_amount REAL NOT NULL,
            payment_method TEXT DEFAULT 'Cash',
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

    # Stock Counts
    c.execute('''
        CREATE TABLE IF NOT EXISTS Stock_Counts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            count_date DATETIME DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'Completed',
            notes TEXT
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS Stock_Count_Items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            count_id INTEGER,
            product_id INTEGER,
            system_qty INTEGER,
            counted_qty INTEGER,
            variance INTEGER,
            FOREIGN KEY(count_id) REFERENCES Stock_Counts(id),
            FOREIGN KEY(product_id) REFERENCES Products_Services(id)
        )
    ''')
    # Settings (ตั้งค่าร้าน)
    c.execute('''
        CREATE TABLE IF NOT EXISTS Settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    ''')
    for _k, _v in [
        ('shop_name', 'PJ Copy Shop'), ('shop_address', ''), ('shop_phone', ''),
        ('promptpay_number', '0812345678'), ('vat_rate', '7'),
        ('receipt_footer', 'ขอบคุณที่ใช้บริการ'), ('currency_symbol', '฿'),
    ]:
        c.execute('INSERT OR IGNORE INTO Settings (key, value) VALUES (?, ?)', (_k, _v))

    # Audit Log
    c.execute('''
        CREATE TABLE IF NOT EXISTS Audit_Log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            action TEXT NOT NULL,
            details TEXT,
            entity_type TEXT,
            entity_id INTEGER,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Job_Orders column migrations (due_date, price)
    for _col_def in [('due_date', 'DATE'), ('price', 'REAL DEFAULT 0')]:
        try:
            c.execute(f'ALTER TABLE Job_Orders ADD COLUMN {_col_def[0]} {_col_def[1]}')
        except Exception:
            pass  # คอลัมน์มีอยู่แล้ว

    # UOM migrations
    for _col_def in [('base_unit', "TEXT DEFAULT 'ชิ้น'"), ('purchase_unit', "TEXT DEFAULT ''"), ('conversion_rate', "REAL DEFAULT 1.0")]:
        try:
            c.execute(f'ALTER TABLE Products_Services ADD COLUMN {_col_def[0]} {_col_def[1]}')
        except Exception:
            pass
            
    for _col_def in [('buy_unit', "TEXT"), ('buy_qty', "REAL"), ('buy_cost', "REAL"), ('multiplier', "REAL DEFAULT 1.0")]:
        try:
            c.execute(f'ALTER TABLE Purchase_Items ADD COLUMN {_col_def[0]} {_col_def[1]}')
        except Exception:
            pass

    # Promotions table migrations
    for _col_def in [
        ('description', "TEXT DEFAULT ''"),
        ('target_scope', "TEXT DEFAULT 'all'"),
        ('target_value', "TEXT DEFAULT ''"),
        ('start_date', "TEXT DEFAULT ''"),
        ('end_date', "TEXT DEFAULT ''"),
        ('priority', "INTEGER DEFAULT 0"),
        ('max_discount', "REAL DEFAULT 0"),
        ('is_stackable', "INTEGER DEFAULT 1"),
        ('allow_with_loyalty', "INTEGER DEFAULT 1"),
        ('min_spend', "REAL DEFAULT 0")
    ]:
        try:
            c.execute(f'ALTER TABLE Promotions ADD COLUMN {_col_def[0]} {_col_def[1]}')
        except Exception:
            pass

    # Sales table migrations for itemized discounts
    for _col_def in [
        ('promo_discount', "REAL DEFAULT 0"),
        ('loyalty_discount', "REAL DEFAULT 0"),
        ('manual_discount', "REAL DEFAULT 0")
    ]:
        try:
            c.execute(f'ALTER TABLE Sales ADD COLUMN {_col_def[0]} {_col_def[1]}')
        except Exception:
            pass

    # Sale_Promotions table (ประวัติโปรโมชั่นที่ใช้จริงในบิล)
    c.execute('''
        CREATE TABLE IF NOT EXISTS Sale_Promotions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sale_id INTEGER NOT NULL,
            promo_id INTEGER,
            promo_name TEXT NOT NULL,
            discount_amount REAL NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(sale_id) REFERENCES Sales(id)
        )
    ''')

    # Default Loyalty & Promotion Settings
    for _k, _v in [
        ('loyalty_enabled', '1'),
        ('loyalty_drink_types', '["Brewed Drink"]'),
        ('loyalty_points_per_cup', '1'),
        ('loyalty_points_per_unit', '10'),
        ('loyalty_discount_per_unit', '20.0'),
        ('promo_auto_apply', '1')
    ]:
        c.execute('INSERT OR IGNORE INTO Settings (key, value) VALUES (?, ?)', (_k, _v))

    # UNIQUE index เพื่อป้องกัน invoice_no ซ้ำกรณี concurrent access
    try:
        c.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_sales_invoice_no ON Sales(invoice_no) WHERE invoice_no IS NOT NULL')
    except Exception:
        pass  # ข้ามถ้าข้อมูลเก่ามี duplicate อยู่แล้ว
        
    # Performance Indexes
    indexes = [
        'CREATE INDEX IF NOT EXISTS idx_products_barcode ON Products_Services(barcode);',
        'CREATE INDEX IF NOT EXISTS idx_products_type ON Products_Services(type);',
        'CREATE INDEX IF NOT EXISTS idx_products_is_active ON Products_Services(is_active);',
        'CREATE INDEX IF NOT EXISTS idx_sales_timestamp ON Sales(timestamp);',
        'CREATE INDEX IF NOT EXISTS idx_sales_payment_status ON Sales(payment_status);',
        'CREATE INDEX IF NOT EXISTS idx_sale_items_sale_id ON Sale_Items(sale_id);',
        'CREATE INDEX IF NOT EXISTS idx_sale_items_product_id ON Sale_Items(product_id);',
        'CREATE INDEX IF NOT EXISTS idx_jobs_status ON Job_Orders(status);',
        'CREATE INDEX IF NOT EXISTS idx_purchases_timestamp ON Purchases(timestamp);',
        'CREATE INDEX IF NOT EXISTS idx_expenses_timestamp ON Expenses(timestamp);',
        'CREATE INDEX IF NOT EXISTS idx_stock_count_date ON Stock_Counts(count_date);'
    ]
    for idx in indexes:
        try:
            c.execute(idx)
        except Exception:
            pass
            
    conn.commit()
    conn.close()


def migrate_pins_to_hash():
    """อัปเกรด PIN แบบ plain-text ที่มีอยู่ให้เป็น hashed (รันครั้งเดียวหลัง upgrade)"""
    conn = get_db_connection()
    try:
        users = conn.execute('SELECT id, pin FROM Users').fetchall()
        for user in users:
            pin = user['pin']
            if pin and not pin.startswith(('pbkdf2:', 'scrypt:')):
                hashed = generate_password_hash(pin)
                conn.execute('UPDATE Users SET pin = ? WHERE id = ?', (hashed, user['id']))
        conn.commit()
    except Exception as ex:
        app.logger.warning(f'PIN migration warning: {ex}')
    finally:
        conn.close()


def get_setting(key, default=''):
    """ดึงค่าการตั้งค่าร้านจาก Settings table"""
    conn = get_db_connection()
    try:
        row = conn.execute('SELECT value FROM Settings WHERE key = ?', (key,)).fetchone()
        return row['value'] if row else default
    except Exception:
        return default
    finally:
        if not has_app_context():
            conn.close()


def _load_loyalty_settings():
    """ดึงค่าตั้งค่าระบบสะสมแต้มและเครื่องดื่มชง พร้อมค่า fallback ที่ปลอดภัย"""
    try:
        enabled_val = get_setting('loyalty_enabled', '1')
        enabled = str(enabled_val).strip() in ('1', 'true', 'True', 'yes')

        drink_types_val = get_setting('loyalty_drink_types', '["Brewed Drink"]')
        drink_types = []
        try:
            import json
            parsed = json.loads(drink_types_val)
            if isinstance(parsed, list):
                drink_types = [str(x).strip() for x in parsed if str(x).strip()]
            elif isinstance(parsed, str):
                drink_types = [parsed.strip()]
        except Exception:
            drink_types = [t.strip() for t in str(drink_types_val).split(',') if t.strip()]

        if not drink_types:
            drink_types = ['Brewed Drink']

        try:
            points_per_cup = int(get_setting('loyalty_points_per_cup', '1'))
            if points_per_cup < 0:
                points_per_cup = 1
        except Exception:
            points_per_cup = 1

        try:
            points_per_unit = int(get_setting('loyalty_points_per_unit', '10'))
            if points_per_unit <= 0:  # ป้องกันตัวหารเป็น 0
                points_per_unit = 10
        except Exception:
            points_per_unit = 10

        try:
            discount_per_unit = float(get_setting('loyalty_discount_per_unit', '20.0'))
            if discount_per_unit < 0:
                discount_per_unit = 20.0
        except Exception:
            discount_per_unit = 20.0

        promo_auto_val = get_setting('promo_auto_apply', '1')
        promo_auto_apply = str(promo_auto_val).strip() in ('1', 'true', 'True', 'yes')

        return {
            'enabled': enabled,
            'drink_types': drink_types,
            'points_per_cup': points_per_cup,
            'points_per_unit': points_per_unit,
            'discount_per_unit': discount_per_unit,
            'promo_auto_apply': promo_auto_apply
        }
    except Exception:
        return {
            'enabled': True,
            'drink_types': ['Brewed Drink'],
            'points_per_cup': 1,
            'points_per_unit': 10,
            'discount_per_unit': 20.0,
            'promo_auto_apply': True
        }


def get_active_redeem_rule(conn=None):
    """
    หาโปรโมชั่นประเภท 'loyalty_redeem' (แลกแต้ม: ครบ X แต้ม/แก้ว แก้วถัดไปราคาพิเศษ Y บาท)
    ที่เปิดใช้งานและอยู่ในช่วงวันที่ โดยเลือก priority สูงสุด
    - condition_value = จำนวนแต้มที่ต้องใช้ต่อ 1 แก้ว
    - discount_value  = ราคาพิเศษต่อแก้วที่แลก
    """
    close_at_end = False
    if conn is None:
        conn = get_db_connection()
        close_at_end = not has_app_context()
    try:
        today_str = datetime.date.today().isoformat()
        rows = conn.execute(
            "SELECT * FROM Promotions WHERE is_active = 1 AND promo_type = 'loyalty_redeem' "
            "ORDER BY priority DESC, id DESC"
        ).fetchall()
        for r in rows:
            p = dict(r)
            start_date = str(p.get('start_date') or '').strip()
            end_date = str(p.get('end_date') or '').strip()
            if start_date and today_str < start_date:
                continue
            if end_date and today_str > end_date:
                continue
            pts = int(p.get('condition_value') or 0)
            if pts <= 0:
                continue
            return {
                'promo_id': p['id'],
                'name': p['name'],
                'points_required': pts,
                'special_price': max(0.0, float(p.get('discount_value') or 0)),
                'target_scope': p.get('target_scope') or 'all',
                'target_value': str(p.get('target_value') or '').strip()
            }
        return None
    except Exception:
        return None
    finally:
        if close_at_end:
            conn.close()


def get_loyalty_config(conn=None):
    """ค่าตั้งค่า loyalty + กติกาแลกแต้มจากหน้าโปรโมชั่น (ถ้ามี จะ override แต้มที่ใช้ต่อแก้ว)"""
    cfg = _load_loyalty_settings()
    rule = get_active_redeem_rule(conn)
    cfg['redeem_rule'] = rule
    if rule:
        cfg['points_per_unit'] = rule['points_required']
    return cfg


def compute_loyalty_discount(items, redeemed_points, loyalty_conf):
    """
    คำนวณส่วนลดจากการแลกแต้ม คืนค่า (discount, units, qualifying_cups)
    - มีโปร loyalty_redeem: แก้วที่แลกคิดราคาพิเศษ (ส่วนลด = ราคาแก้ว - ราคาพิเศษ) เลือกแก้วราคาสูงสุดก่อน
    - ไม่มี: ใช้ discount_per_unit จากหน้าตั้งค่าตามเดิม
    """
    ppu = loyalty_conf.get('points_per_unit') or 0
    rule = loyalty_conf.get('redeem_rule')

    if rule and rule['target_scope'] == 'category' and rule['target_value']:
        qualifies = lambda it: it.get('type') == rule['target_value']
    elif rule and rule['target_scope'] == 'product' and rule['target_value']:
        _ids = {x.strip() for x in rule['target_value'].split(',') if x.strip()}
        qualifies = lambda it: str(it.get('id')) in _ids
    else:
        _types = loyalty_conf.get('drink_types') or []
        qualifies = lambda it: it.get('type') in _types

    prices = []
    for it in items:
        if qualifies(it):
            prices.extend([float(it.get('price', 0))] * int(it.get('qty', 0)))
    prices.sort(reverse=True)
    qualifying_cups = len(prices)

    if not redeemed_points or not loyalty_conf.get('enabled') or ppu <= 0:
        return 0.0, 0, qualifying_cups

    units = redeemed_points // ppu
    if rule:
        discount = sum(max(0.0, p - rule['special_price']) for p in prices[:units])
    else:
        discount = units * loyalty_conf['discount_per_unit']
    return round(float(discount), 2), units, qualifying_cups


def evaluate_promotions_logic(items, customer_id=None, redeemed_points=0, selected_promo_ids=None, conn=None):
    """
    ฟังก์ชันคำนวณโปรโมชั่นส่วนกลาง ใช้ทั้งตอนพรีวิว (/api/promotions/evaluate)
    และตอนบันทึกบิลจริง (/api/sales) เพื่อให้ผลตรงกัน 100%
    """
    close_at_end = False
    if conn is None:
        conn = get_db_connection()
        close_at_end = True

    try:
        # เติม type ของสินค้าจากฐานข้อมูลฝั่งเซิร์ฟเวอร์ (ไม่เชื่อค่าจาก client)
        # เพื่อให้โปรโมชั่นแบบ category ทำงานตรงกันทั้งตอนพรีวิวและตอนบันทึกบิล
        enriched_items = []
        for it in items:
            it = dict(it)
            row = conn.execute('SELECT type FROM Products_Services WHERE id = ?', (it.get('id'),)).fetchone()
            if row:
                it['type'] = row['type']
            enriched_items.append(it)
        items = enriched_items

        today_str = datetime.date.today().isoformat()
        promos = conn.execute(
            'SELECT * FROM Promotions WHERE is_active = 1 ORDER BY priority DESC, id DESC'
        ).fetchall()

        # คำนวณยอดรวมและจำนวนรวมในตะกร้า
        cart_subtotal = sum(float(it.get('price', 0)) * int(it.get('qty', 0)) for it in items)
        cart_total_qty = sum(int(it.get('qty', 0)) for it in items)

        # Loyalty config สำหรับคำนวณส่วนลดแต้ม (เพื่อตรวจเพดานส่วนลด)
        loyalty_conf = get_loyalty_config(conn)
        loyalty_discount, _units, _cups = compute_loyalty_discount(items, redeemed_points, loyalty_conf)

        eligible_promos = []

        for p_row in promos:
            p = dict(p_row)
            p_type = p.get('promo_type', '')
            disc_val = float(p.get('discount_value', 0) or 0)
            cond_type = p.get('condition_type') or 'none'
            cond_val = float(p.get('condition_value', 0) or 0)
            scope = p.get('target_scope') or 'all'
            target_val = str(p.get('target_value') or '').strip()
            start_date = str(p.get('start_date') or '').strip()
            end_date = str(p.get('end_date') or '').strip()
            max_disc = float(p.get('max_discount', 0) or 0)
            allow_with_loyalty = int(p.get('allow_with_loyalty', 1))

            # 1. ตรวจช่วงวันที่
            if start_date and today_str < start_date:
                continue
            if end_date and today_str > end_date:
                continue

            # 2. ตรวจการใช้ร่วมกับแต้มสะสม
            if redeemed_points > 0 and allow_with_loyalty == 0:
                continue

            # 3. คัดกรองสินค้าตาม scope
            if scope == 'category' and target_val:
                matching_items = [it for it in items if it.get('type') == target_val]
            elif scope == 'product' and target_val:
                target_ids = {x.strip() for x in target_val.split(',') if x.strip()}
                matching_items = [it for it in items if str(it.get('id')) in target_ids]
            else:
                matching_items = items

            matching_subtotal = sum(float(it.get('price', 0)) * int(it.get('qty', 0)) for it in matching_items)
            matching_qty = sum(int(it.get('qty', 0)) for it in matching_items)

            # 4. ตรวจเงื่อนไขขั้นต่ำ (condition_type)
            if cond_type == 'min_spend':
                eval_amount = matching_subtotal if scope in ('category', 'product') else cart_subtotal
                if eval_amount < cond_val:
                    continue
            elif cond_type == 'min_qty':
                eval_qty = matching_qty if scope in ('category', 'product') else cart_total_qty
                if eval_qty < cond_val:
                    continue

            # 5. คำนวณมูลค่าส่วนลดตามประเภทโปรโมชั่น
            raw_discount = 0.0

            # 5.1 ซื้อครบ X บาท ลด Y บาท
            if p_type in ('spend_threshold', 'spend_x_disc_y'):
                spend_target = cond_val if cond_val > 0 else float(p.get('min_spend', 0) or 0)
                eval_amount = matching_subtotal if scope in ('category', 'product') else cart_subtotal
                if eval_amount >= spend_target and spend_target > 0:
                    raw_discount = disc_val
                elif spend_target == 0:
                    raw_discount = disc_val

            # 5.2 ลดเป็น % ทั้งบิล
            elif p_type in ('percent_bill', 'bill_percent'):
                raw_discount = cart_subtotal * (disc_val / 100.0)

            # 5.3 ลดเป็นบาททั้งบิล
            elif p_type in ('fixed_bill', 'bill_fixed', 'discount', 'bill_discount'):
                raw_discount = disc_val

            # 5.4 ลด % ตามประเภทสินค้า หรือ สินค้าเฉพาะ
            elif p_type in ('percent_category', 'percent_product'):
                raw_discount = matching_subtotal * (disc_val / 100.0)

            # 5.5 ลดเป็นบาทตามประเภทสินค้า หรือ สินค้าเฉพาะ (ลดต่อชิ้น)
            elif p_type in ('fixed_category', 'fixed_product'):
                raw_discount = matching_qty * disc_val

            # 5.6 ซื้อครบ N ชิ้น ลด/แถม (เช่น ซื้อ X ชิ้น ฟรี Y ชิ้น)
            elif p_type in ('buy_x_get_y', 'freebie', 'bundle_qty'):
                buy_n = int(cond_val) if cond_val > 0 else 1
                free_m = int(disc_val) if disc_val > 0 else 1
                if matching_qty >= buy_n and buy_n > 0:
                    unit_prices = []
                    for it in matching_items:
                        p_price = float(it.get('price', 0))
                        unit_prices.extend([p_price] * int(it.get('qty', 0)))
                    unit_prices.sort()
                    num_free_units = (matching_qty // buy_n) * free_m
                    raw_discount = sum(unit_prices[:num_free_units])

            max_possible = matching_subtotal if scope in ('category', 'product') else cart_subtotal
            calculated_discount = min(raw_discount, max_possible)

            if max_disc > 0:
                calculated_discount = min(calculated_discount, max_disc)

            calculated_discount = round(calculated_discount, 2)

            if calculated_discount > 0:
                p['calculated_discount'] = calculated_discount
                eligible_promos.append(p)

        # 6. เลือกโปรโมชั่นที่ถูกนำมาใช้จริง (Stacking & Priority)
        applied_promos = []

        if selected_promo_ids is not None:
            # กรณีระบุโปรที่ต้องการใช้มาเจาะจง
            selected_ids = [int(x) for x in selected_promo_ids if str(x).isdigit()]
            candidate_promos = [p for p in eligible_promos if p['id'] in selected_ids]

            has_non_stackable = any(p['is_stackable'] == 0 for p in candidate_promos)
            if has_non_stackable:
                if candidate_promos:
                    best = max(candidate_promos, key=lambda x: (x['priority'], x['calculated_discount']))
                    applied_promos = [best]
            else:
                applied_promos = candidate_promos
        else:
            # กรณีคำนวณอัตโนมัติ (Auto-apply)
            if eligible_promos:
                stackable_promos = [p for p in eligible_promos if p['is_stackable'] == 1]
                stackable_sum = sum(p['calculated_discount'] for p in stackable_promos)

                non_stackable_promos = [p for p in eligible_promos if p['is_stackable'] == 0]
                best_non_stackable = max(non_stackable_promos, key=lambda x: (x['calculated_discount'], x['priority'])) if non_stackable_promos else None
                best_non_stackable_amt = best_non_stackable['calculated_discount'] if best_non_stackable else 0

                if best_non_stackable_amt > stackable_sum:
                    applied_promos = [best_non_stackable]
                else:
                    applied_promos = stackable_promos

        # ป้องกันไม่ให้ส่วนลดโปรโมชั่นทำให้ยอดสุทธิติดลบ
        remaining_budget = max(0.0, cart_subtotal - loyalty_discount)
        final_applied = []
        total_promo_discount = 0.0

        for ap in applied_promos:
            if remaining_budget <= 0:
                break
            actual_disc = min(ap['calculated_discount'], remaining_budget)
            if actual_disc > 0:
                total_promo_discount += actual_disc
                remaining_budget -= actual_disc
                final_applied.append({
                    'id': ap['id'],
                    'name': ap['name'],
                    'promo_type': ap['promo_type'],
                    'discount': round(actual_disc, 2),
                    'priority': ap['priority'],
                    'is_stackable': ap['is_stackable']
                })

        total_promo_discount = round(total_promo_discount, 2)
        total_amount = math.ceil(max(0.0, cart_subtotal - loyalty_discount - total_promo_discount))

        return {
            'eligible_promotions': [
                {
                    'id': ep['id'],
                    'name': ep['name'],
                    'description': ep.get('description', ''),
                    'promo_type': ep['promo_type'],
                    'discount': ep['calculated_discount'],
                    'priority': ep['priority'],
                    'is_stackable': ep['is_stackable'],
                    'allow_with_loyalty': ep['allow_with_loyalty']
                } for ep in eligible_promos
            ],
            'applied_promotions': final_applied,
            'promo_discount': total_promo_discount,
            'loyalty_discount': round(loyalty_discount, 2),
            'subtotal': round(cart_subtotal, 2),
            'total_amount': total_amount,
            'net_total': total_amount,
            'success': True
        }
    finally:
        if close_at_end:
            conn.close()


def log_action(action, details='', entity_type='', entity_id=None):
    """บันทึก Audit Log สำหรับการกระทำสำคัญ"""
    try:
        conn = get_db_connection()
        user_id = session.get('user_id') if has_request_context() else None
        username = session.get('username', 'System') if has_request_context() else 'System'
        conn.execute(
            'INSERT INTO Audit_Log (user_id, username, action, details, entity_type, entity_id) VALUES (?,?,?,?,?,?)',
            (user_id, username, action, details, entity_type, entity_id)
        )
        conn.commit()
        if not has_app_context():
            conn.close()
    except Exception:
        pass


def require_role(*allowed_roles):
    """Decorator สำหรับบังคับสิทธิ์การเข้าถึงตาม Role"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            role = session.get('role')
            if not role:
                return jsonify({'error': 'Unauthorized — กรุณาเข้าสู่ระบบ'}), 401
            if role not in allowed_roles:
                return jsonify({'error': f'Access denied — ต้องการสิทธิ์: {", ".join(allowed_roles)}'}), 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def generate_invoice_no(cursor=None):
    """สร้างเลขที่ใบเสร็จ (INVYYMM-XXXX) โดยใช้ connection แยกเพื่อหลีกเลี่ยง race condition"""
    now = datetime.datetime.now()
    yy = str(now.year + 543)[2:]
    mm = f"{now.month:02d}"
    prefix = f"INV{yy}{mm}-"

    # ใช้ connection แยก (read committed data จาก transaction อื่น)
    check_conn = sqlite3.connect(DB_FILE, timeout=10)
    check_conn.row_factory = sqlite3.Row
    try:
        for _ in range(20):
            # ใช้ MAX(CAST) เพื่อหา sequence สูงสุดแบบตัวเลข (ไม่ใช่ alphabetic sort)
            row = check_conn.execute(
                "SELECT MAX(CAST(SUBSTR(invoice_no, ?) AS INTEGER)) as max_seq "
                "FROM Sales WHERE invoice_no LIKE ?",
                (len(prefix) + 1, prefix + '%')
            ).fetchone()
            seq = (row['max_seq'] or 0) + 1
            candidate = f"{prefix}{seq:04d}"
            # ตรวจว่าไม่ซ้ำ
            if not check_conn.execute('SELECT id FROM Sales WHERE invoice_no = ?', (candidate,)).fetchone():
                return candidate
            # ถ้าซ้ำ (concurrent) ให้ข้ามไปเลขถัดไปทันที
            seq += 1
    finally:
        check_conn.close()

    # Fallback: random suffix
    return f"{prefix}{random.randint(10001, 19999):05d}"


def create_backup_zip(conn):
    """สร้างไฟล์ ZIP สำหรับ backup ฐานข้อมูล (hot backup ผ่าน sqlite3.backup)"""
    tables = ['Products_Services', 'Customers', 'Sales', 'Sale_Items', 'Purchases',
              'Purchase_Items', 'Expenses', 'Stock_WriteOffs', 'Customer_Credit']

    memory_file = io.BytesIO()
    with zipfile.ZipFile(memory_file, 'w') as zf:
        try:
            if os.path.exists(DB_FILE):
                fd, tmp_path = tempfile.mkstemp(suffix='.db')
                os.close(fd)
                try:
                    with sqlite3.connect(DB_FILE) as src:
                        dest = sqlite3.connect(tmp_path)
                        src.backup(dest)
                        dest.close()
                    with open(tmp_path, 'rb') as f:
                        db_data = f.read()
                    zf.writestr('pjcopy.db', db_data)
                    zf.writestr('xerox.db', db_data)
                finally:
                    if os.path.exists(tmp_path):
                        os.unlink(tmp_path)
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

    memory_file.seek(0)
    return memory_file


@app.before_request
def require_login():
    allowed_routes = ['login', 'static', 'change_password', 'customer_display', 'api_customer_display_state', 'api_customer_display_info']
    if request.endpoint not in allowed_routes and 'user_id' not in session:
        return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def login():
    if request.method == 'POST':
        pin = request.form.get('pin')
        conn = get_db_connection()
        all_users = conn.execute('SELECT * FROM Users').fetchall()
        conn.close()
        user = None
        for u in all_users:
            if check_password_hash(u['pin'], pin):
                user = u
                break
        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            
            # Detect Mobile
            user_agent = request.headers.get('User-Agent', '').lower()
            if any(m in user_agent for m in ['mobile', 'android', 'iphone', 'ipad']):
                return redirect(url_for('mobile_app'))
                
            return redirect(url_for('index'))
        else:
            return render_template('login.html', error='รหัส PIN ไม่ถูกต้อง')
    return render_template('login.html')

@app.route('/mobile-app')
def mobile_app():
    return render_template('mobile_app.html')

@app.route('/mobile-count')
def mobile_count():
    return render_template('mobile_count.html')



@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/api/change-password', methods=['POST'])
def change_password():
    data = request.get_json() or {}
    username = data.get('username')
    old_pin = data.get('old_pin')
    new_pin = data.get('new_pin')
    
    if not username or not old_pin or not new_pin:
        return jsonify({'error': 'ข้อมูลไม่ครบถ้วน'}), 400
        
    conn = get_db_connection()
    all_users = conn.execute('SELECT * FROM Users WHERE username = ?', (username,)).fetchall()
    user = None
    for u in all_users:
        if check_password_hash(u['pin'], old_pin):
            user = u
            break
    if not user:
        conn.close()
        return jsonify({'error': 'ชื่อผู้ใช้หรือรหัสผ่านเก่าไม่ถูกต้อง'}), 401
        
    conn.execute('UPDATE Users SET pin = ? WHERE id = ?', (generate_password_hash(new_pin), user['id']))
    conn.commit()
    conn.close()
    
    return jsonify({'message': 'เปลี่ยนรหัสผ่านสำเร็จ'})

@app.route('/api/sync-google-sheets', methods=['POST'])
def api_sync_google_sheets():
    try:
        from sheets_sync import sync_data
        result = sync_data()
        return jsonify({'success': True, 'result': result})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/')
def index():
    user_agent = request.headers.get('User-Agent', '').lower()
    if any(m in user_agent for m in ['mobile', 'android', 'iphone', 'ipad']):
        return redirect(url_for('mobile_app'))
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

customer_display_state = {
    'items': [],
    'subtotal': 0,
    'totalDiscount': 0,
    'total': 0,
    'paymentMethod': 'Cash',
    'qrImage': None,
    'status': 'idle',
    'timestamp': 0
}

@app.route('/customer-display')
def customer_display():
    shop_name = get_setting('shop_name', 'PJ Copy Shop')
    return render_template('customer_display.html', shop_name=shop_name)

@app.route('/api/customer-display/state', methods=['GET', 'POST'])
def api_customer_display_state():
    global customer_display_state
    if request.method == 'POST':
        data = request.get_json(silent=True) or {}
        customer_display_state = data
        return jsonify({'success': True})
    else:
        return jsonify(customer_display_state)

@app.route('/api/customer-display/info', methods=['GET'])
def api_customer_display_info():
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.5)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
    except Exception:
        ip = '127.0.0.1'
        
    url = f"http://{ip}:5000/customer-display"
    
    qr_b64 = ''
    try:
        import qrcode
        import io
        import base64
        img = qrcode.make(url)
        buf = io.BytesIO()
        img.save(buf, 'PNG')
        buf.seek(0)
        qr_b64 = f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode('utf-8')}"
    except Exception as e:
        app.logger.warning(f"Could not generate display info QR: {e}")

    return jsonify({
        'ip': ip,
        'url': url,
        'qr_image': qr_b64
    })

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
    count_id = data.get('count_id', None)
    
    if not items:
        return jsonify({'error': 'No items provided'}), 400
        
    conn = get_db_connection()
    try:
        if not count_id:
            # Create Count session
            cursor = conn.execute(
                "INSERT INTO Stock_Counts (notes) VALUES (?)", 
                (notes,)
            )
            count_id = cursor.lastrowid
        else:
            # If joining existing session from mobile, append mobile badge note
            if notes and 'นับผ่านมือถือ' in notes:
                existing = conn.execute("SELECT notes FROM Stock_Counts WHERE id = ?", (count_id,)).fetchone()
                if existing:
                    existing_notes = existing['notes'] or ''
                    if 'นับผ่านมือถือ' not in existing_notes:
                        new_notes = f"{existing_notes} | {notes}" if existing_notes.strip() and existing_notes.strip() != '-' else notes
                        conn.execute("UPDATE Stock_Counts SET notes = ? WHERE id = ?", (new_notes, count_id))
        
        # Insert Items and update stock
        for item in items:
            product_id = item.get('product_id')
            p = conn.execute("SELECT id FROM Products_Services WHERE id = ?", (product_id,)).fetchone()
            if not p:
                conn.close()
                return jsonify({'error': f"Product {product_id} not found"}), 400

            system_qty = item['system_qty']
            counted_qty = item['counted_qty']
            variance = item['variance']
            
            existing_item = conn.execute("SELECT id FROM Stock_Count_Items WHERE count_id = ? AND product_id = ?", (count_id, product_id)).fetchone()
            
            if existing_item:
                conn.execute('''
                    UPDATE Stock_Count_Items 
                    SET system_qty = ?, counted_qty = ?, variance = ? 
                    WHERE id = ?
                ''', (system_qty, counted_qty, variance, existing_item['id']))
            else:
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
    query = request.args.get('q', '').strip()
    conn = get_db_connection()
    products = conn.execute(
        'SELECT * FROM Products_Services WHERE barcode LIKE ? OR name LIKE ? OR id = ? LIMIT 50',
        (f'%{query}%', f'%{query}%', query if query.isdigit() else -1)
    ).fetchall()
    conn.close()
    return jsonify([dict(ix) for ix in products])

@app.route('/api/products/dt', methods=['GET'])
def products_dt():
    conn = get_db_connection()
    draw = request.args.get('draw', type=int)
    start = request.args.get('start', type=int, default=0)
    length = request.args.get('length', type=int, default=10)
    search_value = request.args.get('search[value]', '')
    
    query = "SELECT * FROM Products_Services WHERE is_active = 1"
    params = []
    
    if search_value:
        query += " AND (name LIKE ? OR barcode LIKE ? OR id LIKE ?)"
        params.extend([f"%{search_value}%", f"%{search_value}%", f"%{search_value}%"])
        
    total_records = conn.execute("SELECT COUNT(*) FROM Products_Services WHERE is_active = 1").fetchone()[0]
    total_filtered = conn.execute(f"SELECT COUNT(*) FROM ({query})", params).fetchone()[0]
    
    order_col_idx = request.args.get('order[0][column]', type=int, default=0)
    order_dir = request.args.get('order[0][dir]', default='desc')
    
    columns_map = ['barcode', 'name', 'brand', 'type', 'price', 'stock_qty', 'id']
    order_col = columns_map[order_col_idx] if order_col_idx < len(columns_map) else 'id'
    if order_dir not in ['asc', 'desc']: order_dir = 'desc'
    
    query += f" ORDER BY {order_col} {order_dir} LIMIT ? OFFSET ?"
    params.extend([length, start])
    
    products = conn.execute(query, params).fetchall()
    conn.close()
    
    return jsonify({
        "draw": draw,
        "recordsTotal": total_records,
        "recordsFiltered": total_filtered,
        "data": [dict(p) for p in products]
    })

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
    
    if not name or not type:
        return jsonify({"message": "กรุณาระบุชื่อสินค้าและประเภท"}), 400
    
    brand = new_product.get('brand', '')
    model = new_product.get('model', '')
    color = new_product.get('color', '')
    
    barcode = new_product.get('barcode', '').strip()
    if not barcode:
        # Generate random 8 digit barcode
        barcode = str(random.randint(10000000, 99999999))
        
    price = new_product.get('price', 0.0)
    cost = new_product.get('cost', 0.0)
    stock_qty = new_product.get('stock_qty', 0)
    reorder_level = new_product.get('reorder_level', 5)
    
    base_unit = new_product.get('base_unit', 'ชิ้น')
    purchase_unit = new_product.get('purchase_unit', '')
    conversion_rate = new_product.get('conversion_rate', 1.0)

    conn = get_db_connection()
    c = conn.cursor()
    
    # Check for duplicates
    if barcode:
        existing = c.execute('SELECT name, barcode FROM Products_Services WHERE barcode = ? AND is_active = 1', (barcode,)).fetchone()
        if existing:
            conn.close()
            return jsonify({"message": f"มีสินค้ารหัสบาร์โค้ดนี้ ในระบบแล้ว!"}), 400
            
    existing_exact = c.execute('SELECT name FROM Products_Services WHERE name = ? AND brand = ? AND model = ? AND color = ? AND is_active = 1', (name, brand, model, color)).fetchone()
    if existing_exact:
        conn.close()
        return jsonify({"message": f"มีสินค้านี้ (ชื่อ, ยี่ห้อ, รุ่น, สี เดียวกัน) ในระบบแล้ว!"}), 400

    c.execute('''
        INSERT INTO Products_Services (name, type, barcode, brand, model, color, price, cost, stock_qty, reorder_level, base_unit, purchase_unit, conversion_rate)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (name, type, barcode, brand, model, color, price, cost, stock_qty, reorder_level, base_unit, purchase_unit, conversion_rate))
    conn.commit()
    conn.close()
    return jsonify({"message": "เพิ่มสินค้าใหม่เรียบร้อยแล้ว"}), 201

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
    
    base_unit = data.get('base_unit', 'ชิ้น')
    purchase_unit = data.get('purchase_unit', '')
    conversion_rate = data.get('conversion_rate', 1.0)

    conn = get_db_connection()
    c = conn.cursor()
    
    # Check for duplicates
    if barcode:
        existing = c.execute('SELECT name, barcode FROM Products_Services WHERE barcode = ? AND id != ? AND is_active = 1', (barcode, product_id)).fetchone()
        if existing:
            conn.close()
            return jsonify({"message": f"มีสินค้ารหัสบาร์โค้ดนี้ ในระบบแล้ว!"}), 400
            
    existing_exact = c.execute('SELECT name FROM Products_Services WHERE name = ? AND brand = ? AND model = ? AND color = ? AND id != ? AND is_active = 1', (name, brand, model, color, product_id)).fetchone()
    if existing_exact:
        conn.close()
        return jsonify({"message": f"มีสินค้านี้ (ชื่อ, ยี่ห้อ, รุ่น, สี เดียวกัน) ในระบบแล้ว!"}), 400

    c.execute('''
        UPDATE Products_Services 
        SET name=?, type=?, barcode=?, brand=?, model=?, color=?, price=?, cost=?, stock_qty=?, reorder_level=?, base_unit=?, purchase_unit=?, conversion_rate=?
        WHERE id = ?
    ''', (name, type, barcode, brand, model, color, price, cost, stock_qty, reorder_level, base_unit, purchase_unit, conversion_rate, product_id))
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
    data = request.get_json(silent=True) or {}
    product_id = data.get('product_id')
    raw_qty = data.get('qty', 0)
    reason = data.get('reason', 'ชำรุด')
    
    try:
        qty = int(raw_qty)
    except (ValueError, TypeError):
        return jsonify({"message": "Invalid quantity"}), 400

    if not product_id or qty <= 0:
        return jsonify({"message": "Invalid data"}), 400
        
    conn = get_db_connection()
    c = conn.cursor()

    # ตรวจสอบสต็อกก่อนตัดของเสีย
    current = c.execute('SELECT stock_qty FROM Products_Services WHERE id = ?', (product_id,)).fetchone()
    if not current or current['stock_qty'] < qty:
        conn.close()
        available = current['stock_qty'] if current else 0
        return jsonify({"message": f"สต็อกไม่เพียงพอ (มีอยู่ {available} ชิ้น ไม่สามารถตัด {qty} ชิ้นได้)"}), 400

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
    data = request.get_json() or {}
    manual_discount = max(0.0, float(data.get('discount', 0) or 0))
    payment_method = data.get('payment_method', 'Cash')
    payment_status = data.get('payment_status', 'Paid')
    split_cash = float(data.get('split_cash', 0.0) or 0)
    split_transfer = float(data.get('split_transfer', 0.0) or 0)
    notes = data.get('notes', '')
    customer_id = data.get('customer_id')
    redeemed_points = int(data.get('redeemed_points', 0) or 0)
    items = data.get('items', [])
    promo_ids = data.get('promo_ids') or data.get('selected_promo_ids')

    # ตรวจสอบความถูกต้องของรายการสินค้า
    if not items:
        return jsonify({"message": "ไม่มีสินค้าในตะกร้า"}), 400
    try:
        for item in items:
            if int(item.get('qty', 0)) <= 0 or float(item.get('price', 0)) < 0:
                return jsonify({"message": "จำนวนสินค้าต้องมากกว่า 0 และราคาต้องไม่ติดลบ"}), 400
    except (TypeError, ValueError):
        return jsonify({"message": "ข้อมูลสินค้าไม่ถูกต้อง"}), 400

    conn = get_db_connection()
    c = conn.cursor()

    # 0. Check Stock & Product Existence (ข้ามสำหรับ Hold เพราะยังไม่ตัดสต๊อก)
    if payment_status != 'Hold':
        for item in items:
            p = c.execute('SELECT stock_qty, type FROM Products_Services WHERE id = ?', (item.get('id'),)).fetchone()
            if not p:
                conn.close()
                return jsonify({"message": f"Product id {item.get('id')} not found"}), 400
            if p['type'] != 'Service' and p['stock_qty'] < item.get('qty', 0):
                conn.close()
                return jsonify({"message": f"สินค้า {item.get('name', 'Product')} มีไม่พอในสต๊อก (มีอยู่ {p['stock_qty']})"}), 400

    subtotal = sum(float(item['price']) * int(item['qty']) for item in items)

    # 1. คำนวณส่วนลดแต้มสะสมจาก Loyalty Config (ไม่เชื่อตัวเลขที่ client ส่งมา)
    loyalty_config = get_loyalty_config(conn)
    loyalty_discount = 0.0

    if redeemed_points > 0:
        if not loyalty_config['enabled']:
            conn.close()
            return jsonify({"message": "ระบบสะสมแต้มปิดใช้งานอยู่"}), 400

        points_per_unit = loyalty_config['points_per_unit']
        if redeemed_points % points_per_unit != 0 or not customer_id:
            conn.close()
            return jsonify({"message": f"จำนวนแต้มที่แลกไม่ถูกต้อง (ต้องเป็นทวีคูณของ {points_per_unit} แต้ม)"}), 400

        customer = c.execute('SELECT points FROM Customers WHERE id = ?', (customer_id,)).fetchone()
        if not customer or customer['points'] < redeemed_points:
            conn.close()
            return jsonify({"message": "แต้มสะสมของลูกค้าไม่เพียงพอ"}), 400

        # ส่วนลดแลกแต้ม: ดึงจากโปรโมชั่นแลกแต้ม (ราคาพิเศษต่อแก้ว) ถ้ามี ไม่เช่นนั้นใช้ค่าจากหน้าตั้งค่า
        loyalty_discount, redeem_units, qualifying_cups = compute_loyalty_discount(items, redeemed_points, loyalty_config)
        if qualifying_cups <= 0:
            conn.close()
            return jsonify({"message": "แต้มสะสมสามารถใช้แลกได้เฉพาะสินค้ากลุ่มเครื่องดื่มที่กำหนดเท่านั้น"}), 400
        if redeem_units > qualifying_cups:
            conn.close()
            return jsonify({"message": f"แลกได้สูงสุด {qualifying_cups} แก้วตามจำนวนเครื่องดื่มในตะกร้า"}), 400

    # 2. คำนวณส่วนลดโปรโมชั่นที่ฝั่งเซิร์ฟเวอร์ใหม่ทุกครั้ง (ห้ามเชื่อยอดจากหน้าเว็บ)
    promo_eval = evaluate_promotions_logic(
        items=items,
        customer_id=customer_id,
        redeemed_points=redeemed_points,
        selected_promo_ids=promo_ids,
        conn=conn
    )
    promo_discount = promo_eval['promo_discount']
    applied_promotions = promo_eval['applied_promotions']

    # 3. รวมส่วนลด (manual + loyalty + promo) และคำนวณยอดสุทธิ (ปัดเศษขึ้นเสมอ)
    total_discount = manual_discount + loyalty_discount + promo_discount
    total_amount = math.ceil(max(0.0, subtotal - total_discount))

    # Generate Invoice No
    invoice_no = generate_invoice_no()

    # 4. Insert into Sales
    for _attempt in range(3):
        try:
            c.execute('''
                INSERT INTO Sales (
                    invoice_no, total_amount, discount, promo_discount, loyalty_discount, manual_discount,
                    payment_method, split_cash, split_transfer, payment_status, customer_id, redeemed_points, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                invoice_no, total_amount, total_discount, promo_discount, loyalty_discount, manual_discount,
                payment_method, split_cash, split_transfer, payment_status, customer_id, redeemed_points, notes
            ))
            break
        except sqlite3.IntegrityError as e:
            if 'UNIQUE constraint failed: Sales.invoice_no' in str(e) and _attempt < 2:
                invoice_no = generate_invoice_no()
            else:
                conn.close()
                return jsonify({"message": "ไม่สามารถสร้างเลขบิลได้ กรุณาลองใหม่"}), 500
    sale_id = c.lastrowid

    # 5. Insert into Sale_Promotions (บันทึกโปรโมชั่นที่ใช้จริงลงบิล)
    for ap in applied_promotions:
        c.execute('''
            INSERT INTO Sale_Promotions (sale_id, promo_id, promo_name, discount_amount)
            VALUES (?, ?, ?, ?)
        ''', (sale_id, ap['id'], ap['name'], ap['discount']))

    # 6. Customer Credit if Unpaid
    if payment_status == 'Unpaid' and customer_id:
        c.execute('''
            INSERT INTO Customer_Credit (customer_id, sale_id, amount_due, amount_paid, status)
            VALUES (?, ?, ?, 0, 'Unpaid')
        ''', (customer_id, sale_id, total_amount))

    # 7. Insert Sale_Items, update stock, and calculate earned points
    earned_points = 0
    for item in items:
        product_id = item['id']
        qty = int(item['qty'])
        price = float(item['price'])
        prod_info = c.execute('SELECT type, cost FROM Products_Services WHERE id = ?', (product_id,)).fetchone()
        item_type = prod_info['type'] if prod_info else ''
        base_cost = prod_info['cost'] if prod_info else 0.0

        bom_items = c.execute('SELECT raw_material_id, qty_required FROM BOM WHERE product_id = ?', (product_id,)).fetchall()

        item_cost = 0.0
        if bom_items:
            for b in bom_items:
                raw_prod = c.execute('SELECT cost FROM Products_Services WHERE id = ?', (b['raw_material_id'],)).fetchone()
                raw_cost = raw_prod['cost'] if raw_prod else 0.0
                item_cost += (raw_cost * b['qty_required'])
        else:
            item_cost = base_cost

        c.execute('INSERT INTO Sale_Items (sale_id, product_id, qty, price, cost_price) VALUES (?, ?, ?, ?, ?)',
                  (sale_id, product_id, qty, price, item_cost))

        if payment_status != 'Hold':
            # คำนวณแต้มสะสมตามค่าตั้งค่า loyalty
            if loyalty_config['enabled'] and item_type in loyalty_config['drink_types'] and not item.get('is_redeemed') and not redeemed_points:
                earned_points += qty * loyalty_config['points_per_cup']

            if bom_items:
                for b in bom_items:
                    raw_qty = b['qty_required'] * qty
                    c.execute('UPDATE Products_Services SET stock_qty = stock_qty - ? WHERE id = ? AND stock_qty >= ?',
                              (raw_qty, b['raw_material_id'], raw_qty))
                    if c.rowcount == 0:
                        conn.rollback()
                        conn.close()
                        return jsonify({"message": f"วัตถุดิบไอดี {b['raw_material_id']} มีไม่พอในสต๊อกขณะชำระเงิน"}), 400
            else:
                if item_type != 'Service':
                    c.execute('UPDATE Products_Services SET stock_qty = stock_qty - ? WHERE id = ? AND stock_qty >= ?',
                              (qty, product_id, qty))
                    if c.rowcount == 0:
                        conn.rollback()
                        conn.close()
                        return jsonify({"message": f"สินค้าสต๊อกไม่เพียงพอขณะชำระเงิน กรุณาตรวจสอบใหม่"}), 400

    if payment_status != 'Hold':
        if customer_id and (earned_points > 0 or redeemed_points > 0):
            c.execute('UPDATE Customers SET points = points + ? - ? WHERE id = ?',
                      (earned_points, redeemed_points, customer_id))
            if redeemed_points > 0:
                c.execute('UPDATE Customers SET allow_points_with_debt = 0 WHERE id = ?', (customer_id,))

    conn.commit()
    conn.close()
    return jsonify({
        "message": "Sale completed successfully",
        "sale_id": sale_id,
        "loyalty_discount": loyalty_discount,
        "promo_discount": promo_discount,
        "manual_discount": manual_discount,
        "total_amount": total_amount,
        "applied_promotions": applied_promotions
    }), 201


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
@require_role('Admin', 'Manager')
def void_sale(sale_id):
    conn = get_db_connection()
    c = conn.cursor()
    
    # Check if already voided
    sale = c.execute("SELECT payment_status FROM Sales WHERE id = ?", (sale_id,)).fetchone()
    if not sale or sale['payment_status'] == 'ยกเลิกบิล':
        conn.close()
        return jsonify({"message": "Invalid or already voided sale"}), 400
        
    # ดึงข้อมูลบิลเพื่อคืนแต้มสะสม
    sale_detail = c.execute("SELECT customer_id, redeemed_points FROM Sales WHERE id = ?", (sale_id,)).fetchone()

    # คืนสต็อกและนับแต้มที่เคยได้จากบิลนี้
    items = c.execute('''
        SELECT si.product_id, si.qty, p.type AS product_type
        FROM Sale_Items si
        JOIN Products_Services p ON si.product_id = p.id
        WHERE si.sale_id = ?
    ''', (sale_id,)).fetchall()

    loyalty_config = get_loyalty_config()
    earned_points = 0
    for item in items:
        # ตอนขายบิลที่แลกแต้มจะไม่ได้แต้มใหม่ (ดู checkout_sale) จึงไม่ต้องหักแต้มคืนตอน void
        if (not (sale_detail and sale_detail['redeemed_points'])) and loyalty_config['enabled'] and item['product_type'] in loyalty_config['drink_types']:
            earned_points += item['qty'] * loyalty_config['points_per_cup']
        
        # ตรวจ BOM เพื่อคืนสต็อกวัตถุดิบ
        bom_items = c.execute('SELECT raw_material_id, qty_required FROM BOM WHERE product_id = ?',
                              (item['product_id'],)).fetchall()
        if bom_items:
            for b in bom_items:
                raw_qty = b['qty_required'] * item['qty']
                c.execute("UPDATE Products_Services SET stock_qty = stock_qty + ? WHERE id = ?",
                          (raw_qty, b['raw_material_id']))
        elif item['product_type'] != 'Service':
            # คืนสต็อกปกติ (ไม่มี BOM)
            c.execute("UPDATE Products_Services SET stock_qty = stock_qty + ? WHERE id = ?",
                      (item['qty'], item['product_id']))

    # ย้อนแต้มสะสม: หักแต้มที่เคยได้ + คืนแต้มที่เคยใช้แลก
    if sale_detail and sale_detail['customer_id']:
        redeemed = sale_detail['redeemed_points'] or 0
        c.execute(
            'UPDATE Customers SET points = MAX(0, points - ? + ?) WHERE id = ?',
            (earned_points, redeemed, sale_detail['customer_id'])
        )

    # ยกเลิก Customer_Credit (ถ้ามี)
    c.execute("UPDATE Customer_Credit SET status = 'Cancelled', amount_due = 0 WHERE sale_id = ?", (sale_id,))

    # ทำเครื่องหมายยกเลิก
    c.execute("UPDATE Sales SET payment_status = 'ยกเลิกบิล', total_amount = 0 WHERE id = ?", (sale_id,))
    
    log_action('VOID_SALE', f'ยกเลิกบิล #{sale_id}', 'Sale', sale_id)
    conn.commit()
    conn.close()
    return jsonify({"message": "Sale voided successfully"})

# --- Purchasing / Procurement ---
@app.route('/api/purchases/dt', methods=['GET'])
def get_purchases_dt():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    query_base = "SELECT * FROM Purchases"
    if start_date and end_date:
        query_base += f" WHERE timestamp >= '{start_date} 00:00:00' AND timestamp <= '{end_date} 23:59:59'"
        
    search_cols = ['supplier_name', 'payment_method']
    order_cols = ['id', 'timestamp', 'supplier_name', 'total_amount', 'payment_method']
    return generate_datatables_response(query_base, request.args, search_cols, order_cols)

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
        buy_qty = float(item.get('qty', 1.0))
        buy_cost = float(item.get('cost', 0.0))
        multiplier = float(item.get('multiplier', 1.0))
        buy_unit = item.get('buy_unit', '')
        
        base_qty = buy_qty * multiplier
        base_cost = buy_cost / multiplier if multiplier > 0 else buy_cost
        
        c.execute('INSERT INTO Purchase_Items (purchase_id, product_id, qty, cost_price, buy_unit, buy_qty, buy_cost, multiplier) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                  (purchase_id, product_id, base_qty, base_cost, buy_unit, buy_qty, buy_cost, multiplier))
        
        # Calculate Weighted Average Cost (ถัวเฉลี่ย)
        prod = c.execute('SELECT stock_qty, cost FROM Products_Services WHERE id = ?', (product_id,)).fetchone()
        if prod:
            actual_old_qty = prod['stock_qty']
            old_cost = prod['cost']
            
            # จำนวนสต๊อกจริงที่จะอัปเดตเข้า DB (ล้างค่าที่ติดลบออกไปบางส่วนหรือทั้งหมด)
            new_actual_qty = actual_old_qty + base_qty
            
            # การคำนวณต้นทุน: ถ้าสต๊อกเก่าติดลบ ถือว่ามูลค่าบัญชีเก่าเป็น 0 
            # และของใหม่ที่เข้ามาจะถูกใช้ล้าง Backorder ด้วยต้นทุนล็อตนี้ทันที
            if actual_old_qty <= 0:
                new_avg_cost = base_cost
            else:
                # WAC ปกติ: (มูลค่าของเดิม + มูลค่าของใหม่) / จำนวนรวม
                new_avg_cost = ((actual_old_qty * old_cost) + (base_qty * base_cost)) / new_actual_qty
                
            c.execute('UPDATE Products_Services SET stock_qty = ?, cost = ? WHERE id = ?',
                      (new_actual_qty, new_avg_cost, product_id))
    
    conn.commit()
    conn.close()
    return jsonify({"message": "Purchase completed", "purchase_id": purchase_id}), 201

# --- Phase 3: Job Orders ---
@app.route('/api/jobs/dt', methods=['GET'])
def get_jobs_dt():
    query_base = "SELECT * FROM Job_Orders"
    search_cols = ['customer_name', 'details', 'status']
    order_cols = ['id', 'timestamp', 'customer_name', 'details', 'status', 'due_date']
    return generate_datatables_response(query_base, request.args, search_cols, order_cols)

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
    qty = int(data.get('qty', 1))
    deposit = float(data.get('deposit', 0))
    status = data.get('status', 'รอสินค้า')
    due_date = data.get('due_date') or None
    price = float(data.get('price', 0))

    conn = get_db_connection()
    c = conn.cursor()

    # Auto-add customer if not exists
    if customer_name:
        existing_cust = c.execute('SELECT id FROM Customers WHERE name = ?', (customer_name,)).fetchone()
        if not existing_cust:
            c.execute('INSERT INTO Customers (name, phone) VALUES (?, "")', (customer_name,))

    c.execute(
        'INSERT INTO Job_Orders (customer_name, details, qty, deposit, status, due_date, price) VALUES (?,?,?,?,?,?,?)',
        (customer_name, details, qty, deposit, status, due_date, price)
    )
    job_id = c.lastrowid
    conn.commit()
    conn.close()
    log_action('ADD_JOB', f'เพิ่มคิวงาน #{job_id} - {customer_name}', 'Job', job_id)
    return jsonify({"message": "Job created", "job_id": job_id}), 201

@app.route('/api/jobs/<int:job_id>', methods=['PUT'])
def update_job_status(job_id):
    data = request.get_json() or {}

    conn = get_db_connection()
    c = conn.cursor()

    updates, params = [], []
    for field in ['status', 'due_date', 'price', 'details', 'qty', 'deposit']:
        if field in data:
            updates.append(f'{field} = ?')
            val = data[field]
            if field == 'due_date' and not val:
                val = None
            params.append(val)

    if updates:
        params.append(job_id)
        c.execute(f'UPDATE Job_Orders SET {", ".join(updates)} WHERE id = ?', params)
        conn.commit()
    conn.close()
    return jsonify({"message": "Job updated"})

@app.route('/api/jobs/<int:job_id>/complete', methods=['POST'])
def complete_job(job_id):
    data = request.get_json(silent=True) or {}
    total_amount = data.get('total_amount', 0)
    discount = data.get('discount', 0)
    payment_method = data.get('payment_method', 'Cash')
    payment_status = data.get('payment_status', 'Paid')
    split_cash = data.get('split_cash', 0)
    split_transfer = data.get('split_transfer', 0)
    items = data.get('items', [])
    
    conn = get_db_connection()
    c = conn.cursor()
    
    # Check if trying to use Unpaid for General Customer
    if payment_status == 'Unpaid':
        job = c.execute("SELECT * FROM Job_Orders WHERE id = ?", (job_id,)).fetchone()
        if not job or job['customer_name'] == 'ทั่วไป':
            conn.close()
            return jsonify({"message": "ไม่สามารถบันทึกค้างชำระสำหรับ 'ลูกค้าทั่วไป' ได้ กรุณาเลือกลูกค้าจากระบบสมาชิก"}), 400

    # Check Stock for scanned items
    if items:
        for item in items:
            p = c.execute('SELECT stock_qty, name, type FROM Products_Services WHERE id = ?', (item['id'],)).fetchone()
            if p and p['type'] != 'Service' and p['stock_qty'] < item['qty']:
                conn.close()
                return jsonify({"message": f"สินค้า {p['name']} มีไม่พอในสต๊อก (มีอยู่ {p['stock_qty']})"}), 400

    # Update job status
    c.execute("UPDATE Job_Orders SET status = 'ส่งมอบแล้ว' WHERE id = ?", (job_id,))
    
    job = c.execute("SELECT * FROM Job_Orders WHERE id = ?", (job_id,)).fetchone()
    
    # Resolve customer_id from name
    cust = c.execute("SELECT id FROM Customers WHERE name = ?", (job['customer_name'],)).fetchone()
    customer_id = cust['id'] if cust else None
    
    # Generate Invoice No — ใช้ helper function
    invoice_no = generate_invoice_no()
    
    notes = f"จากบิลจองงาน #JOB-{job_id:04d}"
    
    # Create Sale with Retry
    for _attempt in range(3):
        try:
            c.execute('''
                INSERT INTO Sales (invoice_no, total_amount, discount, payment_method, split_cash, split_transfer, payment_status, customer_id, notes) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (invoice_no, total_amount, discount, payment_method, split_cash, split_transfer, payment_status, customer_id, notes))
            break
        except sqlite3.IntegrityError as e:
            if 'UNIQUE constraint failed: Sales.invoice_no' in str(e) and _attempt < 2:
                invoice_no = generate_invoice_no()
            else:
                conn.close()
                return jsonify({"message": "ไม่สามารถสร้างเลขบิลได้ กรุณาลองใหม่"}), 500
    
    sale_id = c.lastrowid
    
    if payment_status == 'Unpaid' and customer_id:
        c.execute('''
            INSERT INTO Customer_Credit (customer_id, sale_id, amount_due, amount_paid, status)
            VALUES (?, ?, ?, 0, 'Unpaid')
        ''', (customer_id, sale_id, total_amount))
    
    if items:
        # If user scanned items, insert them and deduct stock (BOM-aware)
        for item in items:
            prod_id = item['id']
            qty = item['qty']
            price = item['price']
            
            prod_info = c.execute('SELECT type, cost FROM Products_Services WHERE id = ?', (prod_id,)).fetchone()
            base_cost = prod_info['cost'] if prod_info else 0.0
            bom_items = c.execute('SELECT raw_material_id, qty_required FROM BOM WHERE product_id = ?', (prod_id,)).fetchall()
            
            # Calculate item cost dynamically from BOM or use base cost
            item_cost = 0.0
            if bom_items:
                for b in bom_items:
                    raw_prod = c.execute('SELECT cost FROM Products_Services WHERE id = ?', (b['raw_material_id'],)).fetchone()
                    raw_cost = raw_prod['cost'] if raw_prod else 0.0
                    item_cost += (raw_cost * b['qty_required'])
            else:
                item_cost = base_cost
            
            c.execute('''
                INSERT INTO Sale_Items (sale_id, product_id, qty, price, cost_price)
                VALUES (?, ?, ?, ?, ?)
            ''', (sale_id, prod_id, qty, price, item_cost))
            
            # Stock deduction
            if bom_items:
                for b in bom_items:
                    raw_qty = b['qty_required'] * qty
                    c.execute('UPDATE Products_Services SET stock_qty = stock_qty - ? WHERE id = ?', (raw_qty, b['raw_material_id']))
            elif prod_info and prod_info['type'] != 'Service':
                c.execute('UPDATE Products_Services SET stock_qty = stock_qty - ? WHERE id = ?', (qty, prod_id))
    else:
        # Fallback if no items scanned: use generic service
        prod = c.execute("SELECT id, cost FROM Products_Services WHERE name = 'งานบริการ (คิวงาน)'").fetchone()
        if not prod:
            c.execute('''
                INSERT INTO Products_Services (name, type, price, cost) 
                VALUES ('งานบริการ (คิวงาน)', 'Service', 0, 0)
            ''')
            prod_id = c.lastrowid
            item_cost = 0.0
        else:
            prod_id = prod['id']
            item_cost = prod['cost']
            
        c.execute('''
            INSERT INTO Sale_Items (sale_id, product_id, qty, price, cost_price)
            VALUES (?, ?, 1, ?, ?)
        ''', (sale_id, prod_id, total_amount + discount, item_cost))
    
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
@app.route('/api/expenses/dt', methods=['GET'])
def get_expenses_dt():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    query_base = "SELECT * FROM Expenses"
    if start_date and end_date:
        query_base += f" WHERE timestamp >= '{start_date} 00:00:00' AND timestamp <= '{end_date} 23:59:59'"
        
    search_cols = ['description', 'expense_type', 'payment_method']
    order_cols = ['id', 'timestamp', 'description', 'amount', 'expense_type', 'payment_method']
    return generate_datatables_response(query_base, request.args, search_cols, order_cols)

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
        
        SELECT id, timestamp, 'ซื้อสินค้าเข้าสต๊อก (PO #' || id || ')' as description, total_amount as amount, 'ซื้อสต็อก' as expense_type, payment_method
        FROM Purchases
        WHERE 1=1 {date_filter}
        
        ORDER BY timestamp DESC
    """
    
    expenses = conn.execute(query, params).fetchall()
    conn.close()
    return jsonify([dict(ix) for ix in expenses])

@app.route('/api/expenses', methods=['POST'])
def add_expense():
    data = request.get_json(silent=True) or {}
    description = data.get('description')
    amount = data.get('amount')
    expense_type = data.get('expense_type', 'OPEX')
    payment_method = data.get('payment_method', 'Cash')
    
    if not description or amount is None:
        return jsonify({"message": "Invalid expense data"}), 400
        
    try:
        amount = float(amount)
    except (ValueError, TypeError):
        return jsonify({"message": "Invalid expense amount"}), 400
        
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
    
    # Check for duplicates
    existing = c.execute('SELECT id FROM Customers WHERE name = ? OR (phone != "" AND phone = ?)', (name, phone)).fetchone()
    if existing:
        conn.close()
        return jsonify({"message": "มีชื่อลูกค้า หรือ เบอร์โทรนี้ ในระบบแล้ว!"}), 400
        
    c.execute('INSERT INTO Customers (name, phone, points) VALUES (?, ?, 0)', (name, phone))
    customer_id = c.lastrowid
    conn.commit()
    conn.close()
    return jsonify({"message": "เพิ่มข้อมูลลูกค้าสำเร็จ", "id": customer_id}), 201

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
    
    if points <= 0:
        return jsonify({"message": "จำนวนแต้มต้องมากกว่า 0"}), 400
    
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
    today_date = datetime.datetime.now().strftime('%Y-%m-%d')  # ใช้ local time (UTC+7) แทน UTC
    
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
    
    promos = conn.execute('''
        SELECT * FROM Sale_Promotions WHERE sale_id = ?
    ''', (sale_id,)).fetchall()
    conn.close()
    
    return render_template('receipt.html', sale=dict(sale), items=[dict(ix) for ix in items],
                           promotions=[dict(p) for p in promos])

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

@app.route('/api/sales/dt', methods=['GET'])
def get_sales_dt():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    query_base = "SELECT * FROM Sales"
    if start_date and end_date:
        query_base += f" WHERE timestamp >= '{start_date} 00:00:00' AND timestamp <= '{end_date} 23:59:59'"
        
    search_cols = ['invoice_no', 'payment_method', 'payment_status', 'timestamp']
    order_cols = ['invoice_no', 'timestamp', 'payment_status', 'total_amount']
    
    return generate_datatables_response(query_base, request.args, search_cols, order_cols)

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
        SELECT SUM(si.qty * si.cost_price) as total_cost 
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
    loyalty_config = get_loyalty_config()
    drink_types = loyalty_config['drink_types'] or ['Brewed Drink']
    dt_ph = ', '.join(['?'] * len(drink_types))

    brewed_query = f"""
        SELECT SUM(si.qty * si.price) as brewed_total
        FROM Sale_Items si
        JOIN Sales s ON si.sale_id = s.id
        JOIN Products_Services p ON si.product_id = p.id
        WHERE s.payment_status NOT IN ('ยกเลิกบิล', 'ชำระบิลค้างชำระ') AND p.type IN ({dt_ph})
    """
    free_drinks_query = "SELECT SUM(redeemed_points) as total_redeemed FROM Sales WHERE payment_status NOT IN ('ยกเลิกบิล', 'ชำระบิลค้างชำระ')"
    promo_discount_query = """
        SELECT SUM(discount_amount) as promo_total
        FROM Sale_Promotions sp
        JOIN Sales s ON sp.sale_id = s.id
        WHERE s.payment_status NOT IN ('ยกเลิกบิล', 'ชำระบิลค้างชำระ')
    """
    
    adjustment_query = """
        SELECT SUM(c.variance * p.cost) as total_adjustment
        FROM Stock_Count_Items c
        JOIN Stock_Counts sc ON c.count_id = sc.id
        JOIN Products_Services p ON c.product_id = p.id
        WHERE 1=1
    """
    
    params = []
    brewed_params = list(drink_types)
    promo_params = []
    
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
        promo_discount_query += " AND s.timestamp >= ? AND s.timestamp <= ?"
        
        # for join query
        item_sales_query += " AND s.timestamp >= ? AND s.timestamp <= ?"
        brewed_query += " AND s.timestamp >= ? AND s.timestamp <= ?"
        cost_query += " AND s.timestamp >= ? AND s.timestamp <= ?"
        adjustment_query += " AND sc.count_date >= ? AND sc.count_date <= ?"
        
        # params for each query
        params = [start, end]
        brewed_params.extend([start, end])
        promo_params = [start, end]

    # Total Revenue from Sales (excluding voided)
    sales_result = conn.execute(sales_query, params).fetchone()
    total_revenue = sales_result['total_revenue'] if sales_result['total_revenue'] else 0.0
    
    discount_result = conn.execute(discount_query, params).fetchone()
    total_discount = discount_result['total_discount'] if discount_result['total_discount'] else 0.0

    promo_result = conn.execute(promo_discount_query, promo_params).fetchone()
    promo_discount_total = promo_result['promo_total'] if promo_result and promo_result['promo_total'] else 0.0
    
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
    
    brewed_result = conn.execute(brewed_query, brewed_params).fetchone()
    brewed_total = brewed_result['brewed_total'] if brewed_result['brewed_total'] else 0.0
    
    free_drinks_result = conn.execute(free_drinks_query, params).fetchone()
    total_redeemed_pts = free_drinks_result['total_redeemed'] if free_drinks_result['total_redeemed'] else 0
    pts_unit = loyalty_config['points_per_unit']
    total_free_drinks = int(total_redeemed_pts / pts_unit) if pts_unit > 0 else 0

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
    
    # สูตร P&L: รายได้สุทธิ − ต้นทุนขาย (COGS) − ค่าใช้จ่าย OPEX ± Inventory Adjustment
    # (Owner Draw เป็นการลดส่วนทุนในงบดุล ไม่ใช่ค่าใช้จ่ายดำเนินงาน จึงไม่นำมาหักลบ)
    net_profit = total_revenue - total_cost - total_expenses + total_adjustment
    
    return jsonify({
        "total_revenue": total_revenue,
        "total_discount": total_discount,
        "promo_discount_total": promo_discount_total,
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
        "loyalty_drink_types": loyalty_config['drink_types'],
        "recent_sales": [dict(ix) for ix in recent_sales],
        "item_sales": [dict(ix) for ix in item_sales]
    })

# --- Phase 7: Backup ---

from flask import send_file

@app.route('/api/backup/local', methods=['GET'])
@require_role('Admin')
def backup_local():
    conn = get_db_connection()
    memory_file = create_backup_zip(conn)
    conn.close()
    now_str = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'pjcopy_backup_{now_str}.zip'
    return send_file(
        memory_file,
        mimetype='application/zip',
        as_attachment=True,
        download_name=filename
    )

@app.route('/api/backup/gdrive', methods=['POST'])
@require_role('Admin')
def backup_gdrive():
    try:
        from gdrive_upload import upload_to_drive
    except ImportError:
        return jsonify({"message": "Server error: Google API client libraries not installed."}), 500

    conn = get_db_connection()
    memory_file = create_backup_zip(conn)
    conn.close()
    now_str = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'pjcopy_backup_{now_str}.zip'
    try:
        link = upload_to_drive(memory_file, filename)
        return jsonify({"message": "อัพโหลดไปยัง Google Drive สำเร็จ!", "link": link})
    except Exception as e:
        return jsonify({"message": f"Error: {str(e)}"}), 500

@app.route('/api/restore', methods=['POST'])
@require_role('Admin')
def restore_backup():
    import zipfile, io, os, shutil
    
    if 'file' not in request.files:
        return jsonify({"message": "No file uploaded"}), 400
        
    file = request.files['file']
    if file.filename == '':
        return jsonify({"message": "No file selected"}), 400
        
    try:
        raw_data = file.read()
        if len(raw_data) > 100 * 1024 * 1024:  # Max 100MB for uploaded ZIP
            return jsonify({"message": "ไฟล์ Backup มีขนาดใหญ่เกินไป (สูงสุด 100MB)"}), 400

        memory_file = io.BytesIO(raw_data)
        with zipfile.ZipFile(memory_file, 'r') as zf:
            db_entry = None
            for candidate in ['pjcopy.db', 'xerox.db']:
                if candidate in zf.namelist():
                    db_entry = candidate
                    break
                    
            if not db_entry:
                return jsonify({"message": "ไฟล์ Backup ไม่ถูกต้อง (ไม่พบไฟล์ฐานข้อมูล)"}), 400
                
            info = zf.getinfo(db_entry)
            if info.file_size > 500 * 1024 * 1024:  # Max 500MB extracted DB
                return jsonify({"message": "ฐานข้อมูลมีขนาดใหญ่เกินกว่าที่ระบบจะกู้คืนได้"}), 400
                
            if os.path.exists(DB_FILE):
                shutil.copy2(DB_FILE, 'xerox_db.bak')
                
            with open(DB_FILE, 'wb') as f:
                f.write(zf.read(db_entry))
                
        return jsonify({"message": "เรียกคืนข้อมูลสำเร็จ! กรุณารีเฟรชหน้าเว็บ"})
    except Exception as e:
        if os.path.exists('xerox_db.bak'):
            shutil.copy2('xerox_db.bak', DB_FILE)
        return jsonify({"message": f"Error: {str(e)}"}), 500

@app.route('/api/maintenance/vacuum', methods=['POST'])
@require_role('Admin')
def vacuum_database():
    try:
        size_before = os.path.getsize(DB_FILE) if os.path.exists(DB_FILE) else 0
        conn = sqlite3.connect(DB_FILE, isolation_level=None)
        conn.execute("VACUUM")
        conn.execute("PRAGMA optimize")
        conn.close()
        size_after = os.path.getsize(DB_FILE) if os.path.exists(DB_FILE) else 0
        saved_bytes = max(0, size_before - size_after)
        return jsonify({
            "message": "จัดเรียงและกระชับฐานข้อมูล (VACUUM) เรียบร้อยแล้ว!",
            "size_before_kb": round(size_before / 1024, 2),
            "size_after_kb": round(size_after / 1024, 2),
            "saved_kb": round(saved_bytes / 1024, 2)
        }), 200
    except Exception as e:
        return jsonify({"message": f"เกิดข้อผิดพลาด: {str(e)}"}), 500

@app.route('/api/shutdown', methods=['POST'])
@require_role('Admin')
def shutdown_server():
    import os, signal
    # Send interrupt signal to the current process to shut it down gracefully
    os.kill(os.getpid(), signal.SIGINT)
    return jsonify({"message": "กำลังปิดระบบ..."})


# =============================================================================
# ฟีเจอร์ใหม่: Settings / Audit Log / Expenses CRUD / Promotions / BOM / Reorder / Business Date
# =============================================================================

# ---- Settings ----
@app.route('/settings')
def settings_page():
    if session.get('role') != 'Admin':
        return redirect(url_for('index'))
    return render_template('settings.html')

@app.route('/api/settings', methods=['GET'])
def get_settings_api():
    conn = get_db_connection()
    rows = conn.execute('SELECT key, value FROM Settings').fetchall()
    conn.close()
    return jsonify({r['key']: r['value'] for r in rows})

@app.route('/api/loyalty/config', methods=['GET'])
def get_loyalty_config_api():
    return jsonify(get_loyalty_config())

@app.route('/api/product-types', methods=['GET'])
def get_product_types_api():
    conn = get_db_connection()
    rows = conn.execute("SELECT DISTINCT type FROM Products_Services WHERE type IS NOT NULL AND type != ''").fetchall()
    conn.close()
    types = list({r['type'] for r in rows})
    default_types = [
        "Brewed Drink", "Stationery", "Gift shop", "Dolls",
        "Toys", "Perfume", "IT equipment", "Water", "Soft drinks", "Retail"
    ]
    for dt in default_types:
        if dt not in types:
            types.append(dt)
    types.sort()
    return jsonify(types)

@app.route('/api/settings', methods=['PUT'])
@require_role('Admin')
def update_settings_api():
    data = request.get_json() or {}

    # ตรวจสอบความถูกต้องของค่า Loyalty Settings
    if 'loyalty_points_per_unit' in data:
        try:
            ppu = int(data['loyalty_points_per_unit'])
            if ppu <= 0:
                return jsonify({'error': 'แต้มที่ใช้ต่อ 1 หน่วยแลก ต้องมากกว่า 0 (ห้ามเป็น 0 หรือติดลบ)'}), 400
        except (ValueError, TypeError):
            return jsonify({'error': 'แต้มที่ใช้ต่อ 1 หน่วยแลก ต้องเป็นจำนวนเต็มที่มากกว่า 0'}), 400

    if 'loyalty_points_per_cup' in data:
        try:
            ppc = int(data['loyalty_points_per_cup'])
            if ppc < 0:
                return jsonify({'error': 'แต้มที่ได้ต่อแก้ว ต้องไม่ติดลบ'}), 400
        except (ValueError, TypeError):
            return jsonify({'error': 'แต้มที่ได้ต่อแก้ว ต้องเป็นจำนวนเต็ม'}), 400

    if 'loyalty_discount_per_unit' in data:
        try:
            dpu = float(data['loyalty_discount_per_unit'])
            if dpu < 0:
                return jsonify({'error': 'ส่วนลดต่อหน่วยแลก ต้องไม่ติดลบ'}), 400
        except (ValueError, TypeError):
            return jsonify({'error': 'ส่วนลดต่อหน่วยแลก ต้องเป็นตัวเลข'}), 400

    conn = get_db_connection()
    for key, value in data.items():
        if isinstance(value, (list, dict)):
            import json
            val_str = json.dumps(value, ensure_ascii=False)
        else:
            val_str = str(value)
        conn.execute('INSERT OR REPLACE INTO Settings (key, value) VALUES (?, ?)', (key, val_str))
    conn.commit()
    conn.close()
    log_action('UPDATE_SETTINGS', f'Updated {len(data)} settings keys: {", ".join(data.keys())}')
    return jsonify({'message': 'บันทึกการตั้งค่าสำเร็จ'})

# ---- Audit Log ----
@app.route('/api/audit-log', methods=['GET'])
@require_role('Admin')
def get_audit_log():
    limit = min(int(request.args.get('limit', 100)), 500)
    conn = get_db_connection()
    rows = conn.execute('SELECT * FROM Audit_Log ORDER BY timestamp DESC LIMIT ?', (limit,)).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

# ---- Expense Edit / Delete ----
@app.route('/api/expenses/<int:expense_id>', methods=['PUT'])
def edit_expense(expense_id):
    if session.get('role') not in ('Admin', 'Manager'):
        return jsonify({'error': 'Access denied'}), 403
    data = request.get_json() or {}
    description = data.get('description')
    amount = data.get('amount')
    expense_type = data.get('expense_type', 'OPEX')
    payment_method = data.get('payment_method', 'Cash')
    if not description or amount is None:
        return jsonify({'message': 'ข้อมูลไม่ครบถ้วน'}), 400
    conn = get_db_connection()
    conn.execute(
        'UPDATE Expenses SET description=?, amount=?, expense_type=?, payment_method=? WHERE id=?',
        (description, float(amount), expense_type, payment_method, expense_id)
    )
    conn.commit()
    conn.close()
    log_action('EDIT_EXPENSE', f'Edited expense #{expense_id}', 'Expense', expense_id)
    return jsonify({'message': 'แก้ไขรายการค่าใช้จ่ายสำเร็จ'})

@app.route('/api/expenses/<int:expense_id>', methods=['DELETE'])
def delete_expense(expense_id):
    if session.get('role') not in ('Admin', 'Manager'):
        return jsonify({'error': 'Access denied'}), 403
    conn = get_db_connection()
    exp = conn.execute('SELECT description FROM Expenses WHERE id=?', (expense_id,)).fetchone()
    conn.execute('DELETE FROM Expenses WHERE id=?', (expense_id,))
    conn.commit()
    conn.close()
    desc = exp['description'] if exp else f'#{expense_id}'
    log_action('DELETE_EXPENSE', f'Deleted expense: {desc}', 'Expense', expense_id)
    return jsonify({'message': 'ลบรายการค่าใช้จ่ายสำเร็จ'})

# ---- Promotions CRUD & Evaluate ----
@app.route('/promotions')
def promotions_page():
    return render_template('promotions.html')

@app.route('/api/promotions', methods=['GET'])
def get_promotions():
    conn = get_db_connection()
    promos = conn.execute('SELECT * FROM Promotions ORDER BY is_active DESC, priority DESC, id DESC').fetchall()
    conn.close()
    return jsonify([dict(p) for p in promos])

@app.route('/api/promotions', methods=['POST'])
def add_promotion():
    if session.get('role') not in ('Admin', 'Manager'):
        return jsonify({'error': 'Access denied'}), 403
    data = request.get_json() or {}
    name = str(data.get('name') or '').strip()
    promo_type = str(data.get('promo_type') or '').strip()
    discount_value = max(0.0, float(data.get('discount_value', 0) or 0))
    condition_type = str(data.get('condition_type') or 'none').strip()
    condition_value = max(0.0, float(data.get('condition_value', 0) or 0))
    is_active = int(data.get('is_active', 1))
    description = str(data.get('description') or '').strip()
    target_scope = str(data.get('target_scope') or 'all').strip()
    target_value = str(data.get('target_value') or '').strip()
    start_date = str(data.get('start_date') or '').strip()
    end_date = str(data.get('end_date') or '').strip()
    priority = int(data.get('priority', 0) or 0)
    max_discount = max(0.0, float(data.get('max_discount', 0) or 0))
    is_stackable = int(data.get('is_stackable', 1))
    allow_with_loyalty = int(data.get('allow_with_loyalty', 1))

    if not name or not promo_type:
        return jsonify({'message': 'กรุณาระบุชื่อและประเภทโปรโมชั่น'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO Promotions (
            name, promo_type, discount_value, condition_type, condition_value, is_active,
            description, target_scope, target_value, start_date, end_date, priority,
            max_discount, is_stackable, allow_with_loyalty, min_spend
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        name, promo_type, discount_value, condition_type, condition_value, is_active,
        description, target_scope, target_value, start_date, end_date, priority,
        max_discount, is_stackable, allow_with_loyalty, condition_value if condition_type == 'min_spend' else 0
    ))
    promo_id = cursor.lastrowid
    conn.commit()
    conn.close()
    log_action('CREATE_PROMOTION', f'Created promotion #{promo_id}: {name}', 'Promotion', promo_id)
    return jsonify({'message': 'เพิ่มโปรโมชั่นสำเร็จ', 'id': promo_id}), 201

@app.route('/api/promotions/<int:promo_id>', methods=['PUT'])
def update_promotion(promo_id):
    if session.get('role') not in ('Admin', 'Manager'):
        return jsonify({'error': 'Access denied'}), 403
    data = request.get_json() or {}
    name = str(data.get('name') or '').strip()
    promo_type = str(data.get('promo_type') or '').strip()
    discount_value = max(0.0, float(data.get('discount_value', 0) or 0))
    condition_type = str(data.get('condition_type') or 'none').strip()
    condition_value = max(0.0, float(data.get('condition_value', 0) or 0))
    is_active = int(data.get('is_active', 1))
    description = str(data.get('description') or '').strip()
    target_scope = str(data.get('target_scope') or 'all').strip()
    target_value = str(data.get('target_value') or '').strip()
    start_date = str(data.get('start_date') or '').strip()
    end_date = str(data.get('end_date') or '').strip()
    priority = int(data.get('priority', 0) or 0)
    max_discount = max(0.0, float(data.get('max_discount', 0) or 0))
    is_stackable = int(data.get('is_stackable', 1))
    allow_with_loyalty = int(data.get('allow_with_loyalty', 1))

    if not name or not promo_type:
        return jsonify({'message': 'กรุณาระบุชื่อและประเภทโปรโมชั่น'}), 400

    conn = get_db_connection()
    conn.execute('''
        UPDATE Promotions SET
            name=?, promo_type=?, discount_value=?, condition_type=?, condition_value=?, is_active=?,
            description=?, target_scope=?, target_value=?, start_date=?, end_date=?, priority=?,
            max_discount=?, is_stackable=?, allow_with_loyalty=?, min_spend=?
        WHERE id=?
    ''', (
        name, promo_type, discount_value, condition_type, condition_value, is_active,
        description, target_scope, target_value, start_date, end_date, priority,
        max_discount, is_stackable, allow_with_loyalty,
        condition_value if condition_type == 'min_spend' else 0,
        promo_id
    ))
    conn.commit()
    conn.close()
    log_action('UPDATE_PROMOTION', f'Updated promo #{promo_id}: {name}', 'Promotion', promo_id)
    return jsonify({'message': 'อัปเดตโปรโมชั่นสำเร็จ'})

@app.route('/api/promotions/<int:promo_id>', methods=['DELETE'])
def delete_promotion(promo_id):
    if session.get('role') not in ('Admin',):
        return jsonify({'error': 'Access denied'}), 403
    conn = get_db_connection()
    promo = conn.execute('SELECT name FROM Promotions WHERE id=?', (promo_id,)).fetchone()
    conn.execute('DELETE FROM Promotions WHERE id=?', (promo_id,))
    conn.commit()
    conn.close()
    promo_name = promo['name'] if promo else f'#{promo_id}'
    log_action('DELETE_PROMOTION', f'Deleted promo #{promo_id} ({promo_name})', 'Promotion', promo_id)
    return jsonify({'message': 'ลบโปรโมชั่นสำเร็จ'})

@app.route('/api/promotions/<int:promo_id>/toggle', methods=['POST'])
def toggle_promotion(promo_id):
    if session.get('role') not in ('Admin', 'Manager'):
        return jsonify({'error': 'Access denied'}), 403
    conn = get_db_connection()
    conn.execute('UPDATE Promotions SET is_active = 1 - is_active WHERE id=?', (promo_id,))
    conn.commit()
    promo = conn.execute('SELECT name, is_active FROM Promotions WHERE id=?', (promo_id,)).fetchone()
    conn.close()
    status = 'เปิดใช้งาน' if promo and promo['is_active'] else 'ปิดใช้งาน'
    p_name = promo['name'] if promo else f'#{promo_id}'
    log_action('TOGGLE_PROMOTION', f'Toggled promo #{promo_id} ({p_name}) to {status}', 'Promotion', promo_id)
    return jsonify({'message': f'โปรโมชั่น{status}แล้ว', 'is_active': promo['is_active'] if promo else 0})

@app.route('/api/promotions/evaluate', methods=['POST'])
def evaluate_promotions_api():
    """API ประเมินโปรโมชั่นที่ใช้ได้และคำนวณส่วนลดตามตะกร้าสินค้า"""
    data = request.get_json() or {}
    items = data.get('items', [])
    customer_id = data.get('customer_id')
    redeemed_points = int(data.get('redeemed_points', 0) or 0)
    selected_promo_ids = data.get('selected_promo_ids') or data.get('promo_ids')

    result = evaluate_promotions_logic(
        items=items,
        customer_id=customer_id,
        redeemed_points=redeemed_points,
        selected_promo_ids=selected_promo_ids
    )
    return jsonify(result)

# ---- BOM CRUD ----
@app.route('/api/bom', methods=['GET'])
def get_all_bom():
    conn = get_db_connection()
    rows = conn.execute('''
        SELECT b.id, b.product_id, b.raw_material_id, b.qty_required,
               p1.name AS product_name, p2.name AS material_name,
               p2.stock_qty AS material_stock, p2.type AS material_type
        FROM BOM b
        JOIN Products_Services p1 ON b.product_id = p1.id
        JOIN Products_Services p2 ON b.raw_material_id = p2.id
        ORDER BY p1.name, p2.name
    ''').fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/api/bom/<int:product_id>', methods=['GET'])
def get_bom_by_product(product_id):
    conn = get_db_connection()
    rows = conn.execute('''
        SELECT b.id, b.raw_material_id, b.qty_required,
               p.name AS material_name, p.stock_qty, p.type
        FROM BOM b
        JOIN Products_Services p ON b.raw_material_id = p.id
        WHERE b.product_id = ?
    ''', (product_id,)).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/api/bom', methods=['POST'])
def add_bom_item():
    if session.get('role') not in ('Admin', 'Manager'):
        return jsonify({'error': 'Access denied'}), 403
    data = request.get_json() or {}
    product_id = data.get('product_id')
    raw_material_id = data.get('raw_material_id')
    qty_required = float(data.get('qty_required', 1))
    if not product_id or not raw_material_id:
        return jsonify({'message': 'กรุณาระบุสินค้าและวัตถุดิบ'}), 400
    if product_id == raw_material_id:
        return jsonify({'message': 'สินค้าและวัตถุดิบต้องไม่ใช่ชิ้นเดียวกัน'}), 400
    conn = get_db_connection()
    existing = conn.execute('SELECT id FROM BOM WHERE product_id=? AND raw_material_id=?', (product_id, raw_material_id)).fetchone()
    if existing:
        conn.execute('UPDATE BOM SET qty_required=? WHERE id=?', (qty_required, existing['id']))
        msg = 'อัปเดต BOM สำเร็จ'
    else:
        conn.execute('INSERT INTO BOM (product_id, raw_material_id, qty_required) VALUES (?,?,?)', (product_id, raw_material_id, qty_required))
        msg = 'เพิ่ม BOM สำเร็จ'
    conn.commit()
    conn.close()
    return jsonify({'message': msg}), 201

@app.route('/api/bom/<int:bom_id>', methods=['DELETE'])
def delete_bom_item(bom_id):
    if session.get('role') not in ('Admin', 'Manager'):
        return jsonify({'error': 'Access denied'}), 403
    conn = get_db_connection()
    conn.execute('DELETE FROM BOM WHERE id=?', (bom_id,))
    conn.commit()
    conn.close()
    return jsonify({'message': 'ลบ BOM สำเร็จ'})

# ---- Reorder Alerts ----
@app.route('/api/reorder-alerts', methods=['GET'])
def get_reorder_alerts():
    conn = get_db_connection()
    products = conn.execute('''
        SELECT id, name, type, barcode, stock_qty, reorder_level,
               (reorder_level - stock_qty) AS deficit
        FROM Products_Services
        WHERE is_active = 1 AND type != 'Service' AND stock_qty <= reorder_level
        ORDER BY deficit DESC
    ''').fetchall()
    conn.close()
    return jsonify([dict(p) for p in products])

# ---- Daily Closing (Business_Date) ----
@app.route('/api/business/current', methods=['GET'])
def get_current_business():
    today = datetime.date.today().isoformat()
    conn = get_db_connection()
    record = conn.execute(
        'SELECT * FROM Business_Date WHERE current_date = ? ORDER BY id DESC LIMIT 1', (today,)
    ).fetchone()
    conn.close()
    if record:
        return jsonify(dict(record))
    return jsonify({'is_closed': 1, 'current_date': today, 'starting_cash': 0, 'id': None})

@app.route('/api/business/open', methods=['POST'])
def open_business_day():
    if session.get('role') not in ('Admin', 'Manager'):
        return jsonify({'error': 'Access denied'}), 403
    data = request.get_json() or {}
    starting_cash = float(data.get('starting_cash', 0))
    today = datetime.date.today().isoformat()
    conn = get_db_connection()
    existing = conn.execute('SELECT id FROM Business_Date WHERE current_date = ?', (today,)).fetchone()
    if existing:
        conn.close()
        return jsonify({'message': 'วันนี้เปิดร้านแล้ว'}), 400
    conn.execute(
        'INSERT INTO Business_Date (current_date, is_closed, starting_cash) VALUES (?, 0, ?)',
        (today, starting_cash)
    )
    conn.commit()
    conn.close()
    log_action('OPEN_DAY', f'เปิดร้าน วันที่ {today} เงินตั้งต้น {starting_cash:.2f} บาท')
    return jsonify({'message': f'เปิดร้านสำเร็จ 📅 {today}', 'date': today})

@app.route('/api/business/close', methods=['POST'])
def close_business_day():
    if session.get('role') not in ('Admin', 'Manager'):
        return jsonify({'error': 'Access denied'}), 403
    today = datetime.date.today().isoformat()
    conn = get_db_connection()
    record = conn.execute(
        'SELECT id FROM Business_Date WHERE current_date = ? AND is_closed = 0', (today,)
    ).fetchone()
    if not record:
        conn.close()
        return jsonify({'message': 'ไม่พบรายการเปิดร้านวันนี้ หรือปิดแล้ว'}), 404
    conn.execute('UPDATE Business_Date SET is_closed = 1 WHERE id = ?', (record['id'],))
    conn.commit()
    conn.close()
    log_action('CLOSE_DAY', f'ปิดร้าน วันที่ {today}')
    return jsonify({'message': f'ปิดร้านสำเร็จ 🔒 {today}', 'date': today})

# ---- Job History ----
@app.route('/api/jobs/history', methods=['GET'])
def get_jobs_history():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    conn = get_db_connection()
    query = 'SELECT * FROM Job_Orders WHERE 1=1'
    params = []
    if start_date and end_date:
        query += ' AND timestamp >= ? AND timestamp <= ?'
        params.extend([f'{start_date} 00:00:00', f'{end_date} 23:59:59'])
    query += ' ORDER BY timestamp DESC LIMIT 200'
    jobs = conn.execute(query, params).fetchall()
    conn.close()
    return jsonify([dict(j) for j in jobs])


@app.errorhandler(Exception)
def handle_exception(e):
    from werkzeug.exceptions import HTTPException
    if isinstance(e, HTTPException):
        return e
    import traceback
    traceback.print_exc()
    # Log error จริงไว้ใน console แต่ไม่ส่ง internal detail กลับไปยัง client
    app.logger.error(f'Unhandled exception: {e}')
    return jsonify({"error": "เกิดข้อผิดพลาดภายในระบบ กรุณาลองใหม่อีกครั้ง"}), 500


@app.route('/api/users', methods=['POST'])
@require_role('Admin')
def add_user():
    data = request.get_json() or {}
    username = data.get('username')
    pin = data.get('pin', '0000')
    role = data.get('role', 'Staff')
    if not username: return jsonify({"error": "Missing username"}), 400
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute('INSERT INTO Users (username, pin, role) VALUES (?, ?, ?)', (username, generate_password_hash(pin), role))
        conn.commit()
    except Exception as e:
        return jsonify({"error": str(e)}), 400
    return jsonify({"message": "User created"}), 201

@app.route('/api/users', methods=['GET'])
@require_role('Admin')
def get_users():
    conn = get_db_connection()
    users = conn.execute('SELECT id, username, role FROM Users ORDER BY id').fetchall()
    conn.close()
    return jsonify([dict(u) for u in users])

@app.route('/api/users/<int:user_id>', methods=['DELETE'])
@require_role('Admin')
def delete_user(user_id):
    if session.get('user_id') == user_id:
        return jsonify({"error": "ไม่สามารถลบบัญชีตัวเองได้"}), 400
    conn = get_db_connection()
    user = conn.execute('SELECT username FROM Users WHERE id = ?', (user_id,)).fetchone()
    if not user:
        conn.close()
        return jsonify({"error": "ไม่พบผู้ใช้"}), 404
    conn.execute('DELETE FROM Users WHERE id = ?', (user_id,))
    conn.commit()
    conn.close()
    log_action('DELETE_USER', f'ลบผู้ใช้ {user["username"]}', 'User', user_id)
    return jsonify({"message": "ลบผู้ใช้สำเร็จ"})

@app.route('/api/users/<int:user_id>', methods=['PUT'])
@require_role('Admin')
def update_user(user_id):
    data = request.get_json() or {}
    conn = get_db_connection()
    updates, params = [], []
    if 'username' in data:
        updates.append('username = ?')
        params.append(data['username'])
    if 'role' in data:
        updates.append('role = ?')
        params.append(data['role'])
    if 'pin' in data and data['pin']:
        updates.append('pin = ?')
        params.append(generate_password_hash(data['pin']))
    if not updates:
        conn.close()
        return jsonify({"error": "ไม่มีข้อมูลที่ต้องแก้ไข"}), 400
    params.append(user_id)
    conn.execute(f'UPDATE Users SET {", ".join(updates)} WHERE id = ?', params)
    conn.commit()
    conn.close()
    log_action('UPDATE_USER', f'แก้ไขผู้ใช้ #{user_id}', 'User', user_id)
    return jsonify({"message": "แก้ไขผู้ใช้สำเร็จ"})

@app.route('/api/customers/<int:customer_id>', methods=['PUT'])
def update_customer(customer_id):
    if session.get('role') not in ('Admin', 'Manager'):
        return jsonify({'error': 'Access denied'}), 403
    data = request.get_json() or {}
    name = data.get('name')
    phone = data.get('phone')
    if not name:
        return jsonify({"message": "กรุณาระบุชื่อลูกค้า"}), 400
    conn = get_db_connection()
    # Check duplicate (excluding self)
    existing = conn.execute(
        'SELECT id FROM Customers WHERE (name = ? OR (phone != "" AND phone = ?)) AND id != ?',
        (name, phone or '', customer_id)
    ).fetchone()
    if existing:
        conn.close()
        return jsonify({"message": "มีชื่อลูกค้า หรือ เบอร์โทรนี้ ในระบบแล้ว!"}), 400
    conn.execute('UPDATE Customers SET name = ?, phone = ? WHERE id = ?', (name, phone or '', customer_id))
    conn.commit()
    conn.close()
    return jsonify({"message": "แก้ไขข้อมูลลูกค้าสำเร็จ"})

@app.route('/api/customers/<int:customer_id>', methods=['DELETE'])
@require_role('Admin')
def delete_customer(customer_id):
    conn = get_db_connection()
    # Check for unpaid bills
    unpaid = conn.execute(
        "SELECT COUNT(*) as cnt FROM Customer_Credit WHERE customer_id = ? AND status = 'Unpaid'",
        (customer_id,)
    ).fetchone()
    if unpaid and unpaid['cnt'] > 0:
        conn.close()
        return jsonify({"message": "ไม่สามารถลบลูกค้าที่ยังมียอดค้างชำระได้"}), 400
    cust = conn.execute('SELECT name FROM Customers WHERE id = ?', (customer_id,)).fetchone()
    if not cust:
        conn.close()
        return jsonify({"error": "ไม่พบลูกค้า"}), 404
    conn.execute('DELETE FROM Customers WHERE id = ?', (customer_id,))
    conn.commit()
    conn.close()
    log_action('DELETE_CUSTOMER', f'ลบลูกค้า {cust["name"]}', 'Customer', customer_id)
    return jsonify({"message": "ลบลูกค้าสำเร็จ"})

@app.route('/api/sales/<int:sale_id>', methods=['GET'])
def get_sale_detail(sale_id):
    conn = get_db_connection()
    sale = conn.execute('''
        SELECT s.*, c.name as customer_name 
        FROM Sales s 
        LEFT JOIN Customers c ON s.customer_id = c.id 
        WHERE s.id = ?
    ''', (sale_id,)).fetchone()
    if not sale:
        conn.close()
        return jsonify({"error": "ไม่พบบิล"}), 404
    items = conn.execute('''
        SELECT si.qty, si.price, p.name, p.type, p.barcode
        FROM Sale_Items si
        JOIN Products_Services p ON si.product_id = p.id
        WHERE si.sale_id = ?
    ''', (sale_id,)).fetchall()
    promos = conn.execute('''
        SELECT * FROM Sale_Promotions WHERE sale_id = ?
    ''', (sale_id,)).fetchall()
    conn.close()
    return jsonify({
        'sale': dict(sale),
        'items': [dict(i) for i in items],
        'promotions': [dict(p) for p in promos]
    })

def crc16_ccitt(data):
    crc = 0xFFFF
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = (crc << 1) ^ 0x1021
            else:
                crc <<= 1
            crc &= 0xFFFF
    return crc

def generate_promptpay_payload(target, amount=None):
    target = re.sub(r'[^0-9]', '', str(target or ''))
    if len(target) == 10 and target.startswith('0'):
        sub_tag = '01'
        val = '0066' + target[1:]
    elif len(target) == 13:
        sub_tag = '02'
        val = target
    else:
        sub_tag = '01'
        val = '0066' + target.lstrip('0') if target.startswith('0') else target
        
    tag29_value = f"0016A000000677010111{sub_tag}{len(val):02d}{val}"
    
    initiation_method = "12" if (amount and float(amount) > 0) else "11"
    payload = f"0002010102{initiation_method}"
    payload += f"29{len(tag29_value):02d}{tag29_value}"
    payload += "5802TH5303764"
    if amount:
        try:
            amt_num = float(amount)
            if amt_num > 0:
                amt_str = f"{amt_num:.2f}"
                payload += f"54{len(amt_str):02d}{amt_str}"
        except (ValueError, TypeError):
            pass
    payload += "6304"
    
    crc = crc16_ccitt(payload.encode('ascii'))
    return payload + f"{crc:04X}"

@app.route('/api/generate-qr', methods=['GET', 'POST'])
def generate_qr():
    try:
        import qrcode
        import io
        import base64
    except ImportError:
        return jsonify({'error': 'Missing libraries'}), 500
        
    if request.method == 'GET':
        amount = request.args.get('amount')
    else:
        data = request.get_json(silent=True) or {}
        amount = data.get('amount')

    promptpay_number = get_setting('promptpay_number', '0812345678')
    
    try:
        payload = generate_promptpay_payload(promptpay_number, amount)
        img = qrcode.make(payload)
        img_io = io.BytesIO()
        img.save(img_io, 'PNG')
        img_io.seek(0)
        img_b64 = base64.b64encode(img_io.getvalue()).decode('utf-8')
        
        return jsonify({
            'success': True, 
            'qr_image': f"data:image/png;base64,{img_b64}"
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.after_request
def add_header(r):
    r.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    r.headers["Pragma"] = "no-cache"
    r.headers["Expires"] = "0"
    return r

if __name__ == '__main__':
    init_db()
    migrate_pins_to_hash()  # อัปเกรด PIN เก่าให้เป็น hashed (ทำงานครั้งเดียว)
    app.run(host='0.0.0.0', debug=True, port=5000)
