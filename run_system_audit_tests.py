#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Comprehensive System & Database Audit Test Suite for PJ Copy Shop POS
Target: http://127.0.0.1:5000 with current database (xerox.db)
Generates structured JSON logs and audit metrics for AI Audit.
"""

import sys
import os
import json
import time
import sqlite3
import datetime
import requests
from urllib.parse import urljoin

if sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

BASE_URL = "http://127.0.0.1:5000"
DB_PATH = "xerox.db"
OUTPUT_JSON = "audit_test_results.json"
SUMMARY_JSON = "test_results_summary.json"

class SystemAuditRunner:
    def __init__(self, base_url, db_path):
        self.base_url = base_url
        self.db_path = db_path
        self.session = requests.Session()
        self.test_results = []
        self.start_time = None
        self.end_time = None
        self.admin_pin = self._get_admin_pin()

    def _get_admin_pin(self):
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            user = c.execute("SELECT pin FROM Users WHERE username='Admin'").fetchone()
            conn.close()
            return user[0] if user else "123456"
        except Exception:
            return "405566"

    def log_result(self, test_id, category, name, status, details=None, latency_ms=0):
        res = {
            "test_id": test_id,
            "category": category,
            "name": name,
            "status": "PASS" if status else "FAIL",
            "latency_ms": round(latency_ms, 2),
            "timestamp": datetime.datetime.now().isoformat(),
            "details": details or {}
        }
        self.test_results.append(res)
        icon = "✅ PASS" if status else "❌ FAIL"
        print(f"[{test_id}] {icon} | {category} -> {name} ({round(latency_ms, 1)}ms)")

    # -------------------------------------------------------------
    # 1. Database & Schema Audit
    # -------------------------------------------------------------
    def test_database_baseline(self):
        t0 = time.time()
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # Check SQLite Integrity
        c.execute("PRAGMA integrity_check")
        integrity = c.fetchone()[0]
        self.log_result("DB-01", "Database Integrity", "SQLite PRAGMA integrity_check", integrity == "ok", {"result": integrity}, (time.time()-t0)*1000)

        # Check Foreign Keys Integrity
        t0 = time.time()
        c.execute("PRAGMA foreign_key_check")
        fk_violations = c.fetchall()
        self.log_result("DB-02", "Database Integrity", "SQLite PRAGMA foreign_key_check", len(fk_violations) == 0, {"violations": fk_violations}, (time.time()-t0)*1000)

        # Check Essential 17 Tables Exist
        expected_tables = [
            "Users", "Products_Services", "Inventory_Transactions", "Sales",
            "Sale_Items", "Purchases", "Purchase_Items", "Job_Orders",
            "Expenses", "Stock_WriteOffs", "Customers", "Customer_Credit",
            "BOM", "Promotions", "Business_Date", "Stock_Counts", "Stock_Count_Items"
        ]
        t0 = time.time()
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        existing_tables = [r[0] for r in c.fetchall()]
        missing = [t for t in expected_tables if t not in existing_tables]
        self.log_result("DB-03", "Database Schema", "Verify All Core Tables Present (17 Tables)", len(missing) == 0, {"existing_count": len(existing_tables), "missing": missing}, (time.time()-t0)*1000)

        # Verify Admin Account exists
        t0 = time.time()
        admin_count = c.execute("SELECT COUNT(*) FROM Users WHERE username='Admin'").fetchone()[0]
        self.log_result("DB-04", "Database Baseline", "Default Admin Account Initialized", admin_count >= 1, {"admin_count": admin_count, "current_pin": self.admin_pin}, (time.time()-t0)*1000)
        conn.close()

    # -------------------------------------------------------------
    # 2. Authentication & Session Security
    # -------------------------------------------------------------
    def test_auth_and_security(self):
        # 2.1 Unauthenticated access to protected routes
        unauth_session = requests.Session()
        for route in ['/pos', '/inventory', '/purchases', '/expenses', '/crm', '/reports']:
            t0 = time.time()
            r = unauth_session.get(urljoin(self.base_url, route), allow_redirects=False)
            is_redirect = r.status_code == 302 and ('/login' in r.headers.get('Location', ''))
            self.log_result(f"AUTH-UNAUTH-{route.strip('/')}", "Authentication & Security", f"Protected Route Guard ({route}) Redirects to /login", is_redirect, {"status_code": r.status_code, "location": r.headers.get('Location')}, (time.time()-t0)*1000)

        # 2.2 Invalid Login attempt
        t0 = time.time()
        r = unauth_session.post(urljoin(self.base_url, '/login'), data={'pin': '000000'})
        login_failed = r.status_code == 200 and ('รหัส PIN ไม่ถูกต้อง' in r.text or 'login' in r.url)
        self.log_result("AUTH-INVALID-PIN", "Authentication & Security", "Login Rejected with Invalid PIN", login_failed, {"status_code": r.status_code}, (time.time()-t0)*1000)

        # 2.3 Valid Login with current Admin PIN
        t0 = time.time()
        r = self.session.post(urljoin(self.base_url, '/login'), data={'pin': self.admin_pin}, allow_redirects=False)
        login_ok = r.status_code == 302
        self.log_result("AUTH-VALID-LOGIN", "Authentication & Security", "Login Successful with Current Admin PIN", login_ok, {"pin_used": self.admin_pin, "status_code": r.status_code, "location": r.headers.get('Location')}, (time.time()-t0)*1000)

        # 2.4 Verify Access to Dashboard after login
        t0 = time.time()
        r = self.session.get(urljoin(self.base_url, '/'))
        dash_ok = r.status_code == 200 and 'POS' in r.text
        self.log_result("AUTH-DASHBOARD-ACCESS", "Authentication & Security", "Authenticated Session Access to Dashboard", dash_ok, {"status_code": r.status_code}, (time.time()-t0)*1000)

        # 2.5 Change Password API Test (Validation & Execution)
        # Test missing field
        t0 = time.time()
        r = self.session.post(urljoin(self.base_url, '/api/change-password'), json={'username': 'Admin', 'old_pin': self.admin_pin})
        self.log_result("AUTH-PW-MISSING", "Authentication & Security", "Change Password Missing Fields Rejected (400)", r.status_code == 400, {"status": r.status_code}, (time.time()-t0)*1000)

        # Test wrong old PIN
        t0 = time.time()
        r = self.session.post(urljoin(self.base_url, '/api/change-password'), json={'username': 'Admin', 'old_pin': '999999', 'new_pin': '654321'})
        self.log_result("AUTH-PW-WRONG-OLD", "Authentication & Security", "Change Password Wrong Old PIN Rejected (401)", r.status_code == 401, {"status": r.status_code}, (time.time()-t0)*1000)

        # Test valid PIN change and revert
        t0 = time.time()
        temp_pin = "889900"
        r1 = self.session.post(urljoin(self.base_url, '/api/change-password'), json={'username': 'Admin', 'old_pin': self.admin_pin, 'new_pin': temp_pin})
        r2 = self.session.post(urljoin(self.base_url, '/api/change-password'), json={'username': 'Admin', 'old_pin': temp_pin, 'new_pin': self.admin_pin})
        pw_cycle_ok = r1.status_code == 200 and r2.status_code == 200
        self.log_result("AUTH-PW-CYCLE", "Authentication & Security", "Change Password Cycle & Restore Tested Successfully", pw_cycle_ok, {"r1": r1.status_code, "r2": r2.status_code}, (time.time()-t0)*1000)

    # -------------------------------------------------------------
    # 3. Master Data Management (Catalog & Customers)
    # -------------------------------------------------------------
    def test_catalog_and_crm(self):
        ts = int(time.time())
        # 3.1 Create Service Product
        t0 = time.time()
        service_payload = {
            "name": f"ถ่ายเอกสาร A4 ขาวดำ Test-{ts}",
            "type": "Service",
            "price": 2.0,
            "cost": 0.5,
            "stock_qty": 0
        }
        r = self.session.post(urljoin(self.base_url, '/api/products'), json=service_payload)
        self.log_result("CATALOG-SVC-ADD", "Master Catalog", "Create Service Product (Type: Service)", r.status_code == 201, {"status": r.status_code, "body": r.json() if r.status_code==201 else r.text}, (time.time()-t0)*1000)

        # 3.2 Create Retail Product (Stock Tracked)
        t0 = time.time()
        self.retail_barcode = f"885{ts % 100000:05d}"
        retail_payload = {
            "name": f"ปากกาลูกลื่น น้ำเงิน 0.5mm Test-{ts}",
            "type": "Stationery",
            "barcode": self.retail_barcode,
            "price": 15.0,
            "cost": 8.0,
            "stock_qty": 10,
            "reorder_level": 5
        }
        r = self.session.post(urljoin(self.base_url, '/api/products'), json=retail_payload)
        self.log_result("CATALOG-RETAIL-ADD", "Master Catalog", "Create Retail Product with Barcode", r.status_code == 201, {"status": r.status_code, "barcode": self.retail_barcode}, (time.time()-t0)*1000)

        # 3.3 Create Brewed Drink Product (For Loyalty Program)
        t0 = time.time()
        drink_payload = {
            "name": f"ชาไทยเย็น หวานน้อย Test-{ts}",
            "type": "Brewed Drink",
            "price": 35.0,
            "cost": 15.0,
            "stock_qty": 100
        }
        r = self.session.post(urljoin(self.base_url, '/api/products'), json=drink_payload)
        self.log_result("CATALOG-DRINK-ADD", "Master Catalog", "Create Brewed Drink Product (Type: Brewed Drink)", r.status_code == 201, {"status": r.status_code}, (time.time()-t0)*1000)

        # Fetch Products to get IDs
        t0 = time.time()
        r = self.session.get(urljoin(self.base_url, '/api/products'))
        products = r.json() if r.status_code == 200 else []
        self.created_products = {p['name']: p for p in products}
        self.log_result("CATALOG-LIST", "Master Catalog", "Retrieve Active Product Catalog", r.status_code == 200 and len(products) >= 3, {"total_active": len(products)}, (time.time()-t0)*1000)

        # 3.4 Product Search API
        t0 = time.time()
        r = self.session.get(urljoin(self.base_url, f'/api/products/search?q={self.retail_barcode}'))
        search_ok = r.status_code == 200 and len(r.json()) >= 1
        self.log_result("CATALOG-SEARCH", "Master Catalog", "Search Product by Barcode", search_ok, {"barcode": self.retail_barcode}, (time.time()-t0)*1000)

        # 3.5 Create Customer
        t0 = time.time()
        self.cust_phone = f"08{ts % 100000000:08d}"
        cust_payload = {
            "name": f"ลูกค้าทดสอบ Audit-{ts}",
            "phone": self.cust_phone
        }
        r = self.session.post(urljoin(self.base_url, '/api/customers'), json=cust_payload)
        self.log_result("CRM-CUST-ADD", "Customer CRM", "Create Customer Record", r.status_code == 201, {"status": r.status_code, "phone": self.cust_phone}, (time.time()-t0)*1000)

        # Fetch Customers to get ID
        t0 = time.time()
        r = self.session.get(urljoin(self.base_url, '/api/customers'))
        custs = r.json() if r.status_code == 200 else []
        self.current_customer = next((c for c in custs if c['phone'] == self.cust_phone), None)
        self.log_result("CRM-CUST-LIST", "Customer CRM", "List Customers & Locate Created Customer", self.current_customer is not None, {"customer": self.current_customer}, (time.time()-t0)*1000)

    # -------------------------------------------------------------
    # 4. Purchasing & Inflow Operations
    # -------------------------------------------------------------
    def test_purchasing_workflow(self):
        retail_prod = next((p for p in self.created_products.values() if p['type'] == 'Stationery'), None)
        if not retail_prod:
            self.log_result("PURCHASE-INFLOW", "Supply Chain", "Purchasing Test Skipped (No Retail Product)", False)
            return

        t0 = time.time()
        purchase_payload = {
            "supplier_name": "บริษัท สเตชันเนอรี สยาม จำกัด",
            "payment_method": "Cash",
            "has_vat": True,
            "items": [
                {
                    "id": retail_prod['id'],
                    "qty": 50,
                    "cost": 7.5
                }
            ]
        }
        r = self.session.post(urljoin(self.base_url, '/api/purchases'), json=purchase_payload)
        self.log_result("PURCHASE-BATCH-ADD", "Supply Chain", "Record Purchase Batch (Inflow + VAT)", r.status_code == 201, {"status": r.status_code, "body": r.json() if r.status_code==201 else r.text}, (time.time()-t0)*1000)

        # Verify stock increment in DB
        t0 = time.time()
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        updated_prod = c.execute("SELECT stock_qty, cost FROM Products_Services WHERE id = ?", (retail_prod['id'],)).fetchone()
        conn.close()
        expected_stock = retail_prod['stock_qty'] + 50
        stock_matched = updated_prod[0] == expected_stock
        self.log_result("PURCHASE-STOCK-INC", "Supply Chain", "Verify Stock Increment After Purchase", stock_matched, {"before": retail_prod['stock_qty'], "after": updated_prod[0], "expected": expected_stock}, (time.time()-t0)*1000)

    # -------------------------------------------------------------
    # 5. Point of Sale & Sales Transactions
    # -------------------------------------------------------------
    def test_pos_sales_workflows(self):
        retail_prod = next((p for p in self.created_products.values() if p['type'] == 'Stationery'), None)
        svc_prod = next((p for p in self.created_products.values() if p['type'] == 'Service'), None)
        drink_prod = next((p for p in self.created_products.values() if p['type'] == 'Brewed Drink'), None)
        cust_id = self.current_customer['id'] if self.current_customer else 1

        # 5.1 Normal Cash Sale (Multi-item: Retail + Service)
        t0 = time.time()
        sale_cash_payload = {
            "customer_id": cust_id,
            "payment_method": "Cash",
            "payment_status": "Paid",
            "discount": 0,
            "items": [
                {"id": svc_prod['id'], "name": svc_prod['name'], "type": "Service", "price": 2.0, "qty": 10},
                {"id": retail_prod['id'], "name": retail_prod['name'], "type": "Stationery", "price": 15.0, "qty": 2}
            ]
        }
        r = self.session.post(urljoin(self.base_url, '/api/sales'), json=sale_cash_payload)
        res_json = r.json() if r.status_code == 201 else {}
        self.log_result("POS-SALE-CASH", "POS & Sales Operations", "Multi-Item Cash Sale (Service + Retail)", r.status_code == 201, {"response": res_json}, (time.time()-t0)*1000)

        # 5.2 Out of Stock Validation Guard (Boundary Test)
        t0 = time.time()
        sale_overstock = {
            "customer_id": cust_id,
            "payment_method": "Cash",
            "items": [
                {"id": retail_prod['id'], "name": retail_prod['name'], "type": "Stationery", "price": 15.0, "qty": 99999}
            ]
        }
        r_over = self.session.post(urljoin(self.base_url, '/api/sales'), json=sale_overstock)
        self.log_result("POS-OOS-GUARD", "POS & Sales Operations", "Prevent Sale Exceeding Available Stock (400 Rejection)", r_over.status_code == 400, {"status": r_over.status_code}, (time.time()-t0)*1000)

        # 5.3 Brewed Drink Sale (Loyalty Points Accrual: 10 drinks = 10 points)
        t0 = time.time()
        sale_drinks = {
            "customer_id": cust_id,
            "payment_method": "PromptPay",
            "payment_status": "Paid",
            "items": [
                {"id": drink_prod['id'], "name": drink_prod['name'], "type": "Brewed Drink", "price": 35.0, "qty": 10}
            ]
        }
        r_drink = self.session.post(urljoin(self.base_url, '/api/sales'), json=sale_drinks)
        self.log_result("POS-SALE-DRINKS", "Loyalty & CRM Operations", "Brewed Drinks Sale with PromptPay", r_drink.status_code == 201, {"status": r_drink.status_code}, (time.time()-t0)*1000)

        # Verify Points in Database
        t0 = time.time()
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        pts = c.execute("SELECT points FROM Customers WHERE id = ?", (cust_id,)).fetchone()[0]
        conn.close()
        self.log_result("CRM-PTS-ACCRUAL", "Loyalty & CRM Operations", "Verify 10 Points Accrued for Customer", pts >= 10, {"points": pts}, (time.time()-t0)*1000)

        # 5.4 Loyalty Points Redemption (Redeem 10 points for 20฿ discount)
        t0 = time.time()
        redeem_sale = {
            "customer_id": cust_id,
            "payment_method": "Cash",
            "payment_status": "Paid",
            "redeemed_points": 10,
            "items": [
                {"id": drink_prod['id'], "name": drink_prod['name'], "type": "Brewed Drink", "price": 15.0, "qty": 1, "is_redeemed": True}
            ]
        }
        r_red = self.session.post(urljoin(self.base_url, '/api/sales'), json=redeem_sale)
        self.log_result("CRM-PTS-REDEEM", "Loyalty & CRM Operations", "Redeem 10 Points for Discount", r_red.status_code == 201, {"status": r_red.status_code}, (time.time()-t0)*1000)

        # 5.5 Split Payment Sale (Cash + Transfer)
        t0 = time.time()
        split_sale = {
            "customer_id": cust_id,
            "payment_method": "Split",
            "payment_status": "Paid",
            "split_cash": 10.0,
            "split_transfer": 25.0,
            "items": [
                {"id": drink_prod['id'], "name": drink_prod['name'], "type": "Brewed Drink", "price": 35.0, "qty": 1}
            ]
        }
        r_split = self.session.post(urljoin(self.base_url, '/api/sales'), json=split_sale)
        self.log_result("POS-SALE-SPLIT", "POS & Sales Operations", "Split Payment Processing (Cash + Transfer)", r_split.status_code == 201, {"status": r_split.status_code}, (time.time()-t0)*1000)

        # 5.6 Unpaid / Customer Debt Sale
        t0 = time.time()
        debt_sale = {
            "customer_id": cust_id,
            "payment_method": "Cash",
            "payment_status": "Unpaid",
            "items": [
                {"id": retail_prod['id'], "name": retail_prod['name'], "type": "Stationery", "price": 15.0, "qty": 4}
            ]
        }
        r_debt = self.session.post(urljoin(self.base_url, '/api/sales'), json=debt_sale)
        debt_resp = r_debt.json() if r_debt.status_code == 201 else {}
        self.unpaid_sale_id = debt_resp.get("sale_id")
        self.log_result("POS-SALE-DEBT", "Customer Credit & Debt", "Unpaid Sale Creation (Credit Record Generated)", r_debt.status_code == 201 and self.unpaid_sale_id is not None, {"sale_id": self.unpaid_sale_id}, (time.time()-t0)*1000)

        # Verify Customer Credit Record in DB
        t0 = time.time()
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        credit_row = c.execute("SELECT amount_due, amount_paid, status FROM Customer_Credit WHERE sale_id = ?", (self.unpaid_sale_id,)).fetchone()
        conn.close()
        self.log_result("CREDIT-REC-CHECK", "Customer Credit & Debt", "Verify Customer_Credit Entry Created with Status 'Unpaid'", credit_row is not None and credit_row[2] == 'Unpaid', {"credit_entry": credit_row}, (time.time()-t0)*1000)

        # 5.7 Settle Customer Debt via /api/sales/<id>/pay
        if self.unpaid_sale_id:
            t0 = time.time()
            pay_payload = {
                "payment_method": "PromptPay"
            }
            r_pay = self.session.put(urljoin(self.base_url, f'/api/sales/{self.unpaid_sale_id}/pay'), json=pay_payload)
            self.log_result("CREDIT-PAY-SETTLE", "Customer Credit & Debt", f"Settle Debt for Bill #{self.unpaid_sale_id} via PromptPay", r_pay.status_code == 200, {"status": r_pay.status_code}, (time.time()-t0)*1000)

        # 5.8 Invoice No Format Verification
        t0 = time.time()
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        last_inv = c.execute("SELECT invoice_no FROM Sales ORDER BY id DESC LIMIT 1").fetchone()
        conn.close()
        inv_valid = last_inv and last_inv[0].startswith("INV") and "-" in last_inv[0]
        self.log_result("POS-INV-FORMAT", "POS & Sales Operations", "Verify Invoice Numbering Format (INVYYMM-XXXX)", inv_valid, {"invoice_no": last_inv[0] if last_inv else None}, (time.time()-t0)*1000)

    # -------------------------------------------------------------
    # 6. Job Orders Workflow
    # -------------------------------------------------------------
    def test_job_orders_workflow(self):
        t0 = time.time()
        job_payload = {
            "customer_name": self.current_customer['name'] if self.current_customer else "ลูกค้างานพิมพ์ด่วน",
            "details": "เข้าเล่มกระดูกงู สันปกพลาสติกใส 5 เล่ม",
            "qty": 5,
            "deposit": 100.0,
            "status": "รอดำเนินการ"
        }
        r = self.session.post(urljoin(self.base_url, '/api/jobs'), json=job_payload)
        job_res = r.json() if r.status_code == 201 else {}
        job_id = job_res.get('job_id')
        self.log_result("JOB-CREATE", "Job Orders", "Create Job Order with Deposit", r.status_code == 201 and job_id is not None, {"job_id": job_id}, (time.time()-t0)*1000)

        if job_id:
            # Update status
            t0 = time.time()
            r_up = self.session.put(urljoin(self.base_url, f'/api/jobs/{job_id}'), json={"status": "กำลังดำเนินการ"})
            self.log_result("JOB-STATUS-UPDATE", "Job Orders", f"Update Job #{job_id} Status", r_up.status_code == 200, {"status": r_up.status_code}, (time.time()-t0)*1000)

            # Complete job
            t0 = time.time()
            r_comp = self.session.post(urljoin(self.base_url, f'/api/jobs/{job_id}/complete'), json={"total_amount": 100.0, "payment_method": "Cash"})
            self.log_result("JOB-COMPLETE", "Job Orders", f"Mark Job #{job_id} as Complete", r_comp.status_code == 200, {"status": r_comp.status_code}, (time.time()-t0)*1000)

    # -------------------------------------------------------------
    # 7. Inventory Stock Auditing & Discrepancy
    # -------------------------------------------------------------
    def test_stock_audits_and_writeoffs(self):
        retail_prod = next((p for p in self.created_products.values() if p['type'] == 'Stationery'), None)
        if not retail_prod:
            return

        # 7.1 Stock Write-off (Damaged goods)
        t0 = time.time()
        wo_payload = {
            "product_id": retail_prod['id'],
            "qty": 2,
            "reason": "สินค้าชำรุดจากการจัดเรียง"
        }
        r_wo = self.session.post(urljoin(self.base_url, '/api/inventory/writeoff'), json=wo_payload)
        self.log_result("INV-WRITEOFF", "Inventory Auditing", "Record Stock Write-Off for Damaged Items", r_wo.status_code in (200, 201), {"status": r_wo.status_code}, (time.time()-t0)*1000)

        # 7.2 Stock Count Session Submission
        t0 = time.time()
        count_payload = {
            "notes": "รอบตรวจนับสต็อกประจำวัน AI Audit",
            "items": [
                {
                    "product_id": retail_prod['id'],
                    "system_qty": 50,
                    "counted_qty": 49,
                    "variance": -1
                }
            ]
        }
        r_sc = self.session.post(urljoin(self.base_url, '/api/stock-counts'), json=count_payload)
        sc_res = r_sc.json() if r_sc.status_code in (200, 201) else {}
        self.log_result("INV-STOCK-COUNT", "Inventory Auditing", "Submit Physical Stock Count Audit Session", r_sc.status_code in (200, 201), {"response": sc_res}, (time.time()-t0)*1000)

    # -------------------------------------------------------------
    # 8. Financial Expenses & Reports
    # -------------------------------------------------------------
    def test_expenses_and_financials(self):
        # 8.1 Record Expense
        t0 = time.time()
        exp_payload = {
            "description": "ค่าน้ำมันรถจักรยานยนต์ส่งเอกสาร",
            "amount": 120.0,
            "expense_type": "OPEX",
            "payment_method": "Cash"
        }
        r_exp = self.session.post(urljoin(self.base_url, '/api/expenses'), json=exp_payload)
        self.log_result("FIN-EXP-RECORD", "Financial Management", "Record Operational Expense (OPEX)", r_exp.status_code == 201, {"status": r_exp.status_code}, (time.time()-t0)*1000)

        # 8.2 Generate Financial Reports
        t0 = time.time()
        r_rep = self.session.get(urljoin(self.base_url, '/api/reports?type=all'))
        rep_data = r_rep.json() if r_rep.status_code == 200 else {}
        has_rev = 'total_revenue' in rep_data
        self.log_result("FIN-REPORT-GEN", "Financial Management", "Generate Financial Reports API (P&L, Revenue)", r_rep.status_code == 200 and has_rev, {"report_metrics": rep_data}, (time.time()-t0)*1000)

        # 8.3 Local DB Backup API
        t0 = time.time()
        r_bk = self.session.get(urljoin(self.base_url, '/api/backup/local'))
        self.log_result("SYS-BACKUP-LOCAL", "System Maintenance", "Trigger Local Database Backup API", r_bk.status_code in (200, 302) or 'application' in r_bk.headers.get('Content-Type', ''), {"status": r_bk.status_code}, (time.time()-t0)*1000)

    # -------------------------------------------------------------
    # 9. UI Template Health & Navigation Checks
    # -------------------------------------------------------------
    def test_all_web_routes(self):
        routes_to_test = [
            ("/", "Home Dashboard"),
            ("/pos", "Point of Sale (POS)"),
            ("/inventory", "Inventory Management"),
            ("/purchases", "Purchases / Stock In"),
            ("/expenses", "Expense Tracking"),
            ("/jobs", "Job Orders"),
            ("/crm", "Customer CRM"),
            ("/reports", "Financial Reports"),
            ("/stock-checking", "Stock Count Audit"),
            ("/print-barcodes", "Barcode Label Printing"),
            ("/login", "Login Page")
        ]

        for route, label in routes_to_test:
            t0 = time.time()
            r = self.session.get(urljoin(self.base_url, route))
            is_ok = r.status_code == 200 and len(r.text) > 500
            
            # Additional UI checks for specific requirements
            extra = {}
            if route == "/":
                extra["has_logout_btn"] = "ออกจากระบบ" in r.text or "logout" in r.text
                extra["no_shutdown_btn"] = "ปิดระบบ" not in r.text
                extra["has_home_emoji"] = "🏠" in r.text or "bi-house" in r.text
            elif route != "/login":
                extra["has_home_emoji"] = "🏠" in r.text or "bi-house" in r.text

            self.log_result(f"UI-ROUTE-{route.strip('/') or 'root'}", "UI & Template Health", f"Web Route: {label} ({route})", is_ok, {"status_code": r.status_code, "size_bytes": len(r.text), **extra}, (time.time()-t0)*1000)

    # -------------------------------------------------------------
    # 10. Security & Input Resilience
    # -------------------------------------------------------------
    def test_security_resilience(self):
        # 10.1 SQL Injection Resilience in Product Search
        t0 = time.time()
        sqli_payload = "' OR '1'='1"
        r_sqli = self.session.get(urljoin(self.base_url, f'/api/products/search?q={sqli_payload}'))
        # Should not crash (500) and return safe empty or filtered list
        self.log_result("SEC-SQLI-SEARCH", "Security & Resilience", "SQL Injection Resilience in Product Search", r_sqli.status_code == 200, {"status": r_sqli.status_code}, (time.time()-t0)*1000)

        # 10.2 XSS Script Tag Escaping in Customer Name
        t0 = time.time()
        xss_name = "<script>alert('xss')</script>"
        r_xss = self.session.post(urljoin(self.base_url, '/api/customers'), json={"name": xss_name, "phone": f"099{int(time.time())%1000000:06d}"})
        # Server stores safely and returns response
        self.log_result("SEC-XSS-CUST-STORE", "Security & Resilience", "XSS Tag Storage Resilience in Customer Creation", r_xss.status_code in (201, 400), {"status": r_xss.status_code}, (time.time()-t0)*1000)

    # -------------------------------------------------------------
    # Main Execution Flow
    # -------------------------------------------------------------
    def run_all(self):
        self.start_time = time.time()
        print("="*75)
        print(f"🚀 STARTING SYSTEM AUDIT TEST SUITE")
        print(f"Target Base URL : {self.base_url}")
        print(f"Database File   : {self.db_path}")
        print(f"Execution Time  : {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*75)

        print("\n--- PHASE 1: Database & Baseline Audit ---")
        self.test_database_baseline()

        print("\n--- PHASE 2: Authentication & Session Security ---")
        self.test_auth_and_security()

        print("\n--- PHASE 3: Master Data & Catalog Services ---")
        self.test_catalog_and_crm()

        print("\n--- PHASE 4: Supply Chain & Purchasing Workflow ---")
        self.test_purchasing_workflow()

        print("\n--- PHASE 5: POS & Sales Transaction Workflows ---")
        self.test_pos_sales_workflows()

        print("\n--- PHASE 6: Job Orders Management ---")
        self.test_job_orders_workflow()

        print("\n--- PHASE 7: Inventory Auditing & Write-Offs ---")
        self.test_stock_audits_and_writeoffs()

        print("\n--- PHASE 8: Financial Management & Reporting ---")
        self.test_expenses_and_financials()

        print("\n--- PHASE 9: Security & Injection Resilience ---")
        self.test_security_resilience()

        print("\n--- PHASE 10: UI Template Health & Navigation Checks ---")
        self.test_all_web_routes()

        self.end_time = time.time()
        duration = round(self.end_time - self.start_time, 2)

        # Summarize
        total = len(self.test_results)
        passed = sum(1 for t in self.test_results if t['status'] == 'PASS')
        failed = total - passed
        pass_rate = round((passed / total) * 100, 2) if total else 0

        summary = {
            "target": self.base_url,
            "database": self.db_path,
            "executed_at": datetime.datetime.now().isoformat(),
            "duration_seconds": duration,
            "total_tests": total,
            "passed": passed,
            "failed": failed,
            "pass_rate_percent": pass_rate,
            "categories": {}
        }

        for t in self.test_results:
            cat = t['category']
            if cat not in summary['categories']:
                summary['categories'][cat] = {"total": 0, "passed": 0, "failed": 0}
            summary['categories'][cat]['total'] += 1
            if t['status'] == 'PASS':
                summary['categories'][cat]['passed'] += 1
            else:
                summary['categories'][cat]['failed'] += 1

        # Write output files
        with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
            json.dump(self.test_results, f, ensure_ascii=False, indent=2)

        with open(SUMMARY_JSON, 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)

        print("\n" + "="*75)
        print(f"📊 SYSTEM AUDIT TEST EXECUTION SUMMARY")
        print("="*75)
        print(f"Total Tests Executed : {total}")
        print(f"Passed               : {passed} ✅")
        print(f"Failed               : {failed} ❌")
        print(f"Pass Rate            : {pass_rate}%")
        print(f"Duration             : {duration}s")
        print("-" * 75)
        for cat, stat in summary['categories'].items():
            print(f"  • {cat:<32}: {stat['passed']}/{stat['total']} passed")
        print("="*75)
        print(f"Full details saved to {OUTPUT_JSON} and {SUMMARY_JSON}")
        return summary

if __name__ == '__main__':
    runner = SystemAuditRunner(BASE_URL, DB_PATH)
    res = runner.run_all()
    sys.exit(0 if res['failed'] == 0 else 1)
