import os
import sqlite3
import tempfile
import unittest

import app


class DailyWorkflowTest(unittest.TestCase):
    """One business-day scenario: receiving stock, selling every category, loyalty."""

    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.tmp.close()
        self.original_db = app.DB_FILE
        app.DB_FILE = self.tmp.name
        app.app.config['TESTING'] = True
        app.init_db()
        self.client = app.app.test_client()
        with self.client.session_transaction() as session:
            session['user_id'] = 1
        self.conn = sqlite3.connect(app.DB_FILE)
        self.conn.row_factory = sqlite3.Row
        self.conn.executemany(
            '''INSERT INTO Products_Services (name, type, price, cost, stock_qty)
               VALUES (?, ?, ?, ?, 0)''',
            [
                ('ถ่ายเอกสาร', 'Service', 2, 0.5), ('ปริ้นเอกสาร', 'Service', 5, 1),
                ('เข้าเล่ม', 'Service', 30, 8), ('กิ๊ฟช็อป', 'Retail', 49, 25),
                ('เครื่องเขียน', 'Stationery', 15, 6), ('ขนม', 'Snack', 20, 10),
                ('น้ำหอม', 'Retail', 199, 100), ('ของเล่น', 'Retail', 89, 45),
                ('ตุ๊กตา', 'Retail', 159, 80), ('น้ำเปล่า', 'Water', 10, 4),
                ('น้ำอัดลม', 'Soft drinks', 20, 9), ('ชาเย็น', 'Brewed Drink', 30, 12),
            ],
        )
        self.conn.execute("INSERT INTO Customers (name, phone) VALUES ('ลูกค้าทดสอบ', '0800000000')")
        self.conn.commit()

    def tearDown(self):
        self.conn.close()
        app.DB_FILE = self.original_db
        os.unlink(self.tmp.name)

    def products(self):
        return {row['name']: dict(row) for row in self.conn.execute('SELECT * FROM Products_Services')}

    def test_one_day_workflow_and_loyalty_discount(self):
        products = self.products()
        received = [
            {'id': product['id'], 'qty': 20, 'cost': product['cost']}
            for product in products.values() if product['type'] != 'Service'
        ]
        purchase = self.client.post('/api/purchases', json={'supplier_name': 'ผู้จำหน่ายทดสอบ', 'items': received})
        self.assertEqual(purchase.status_code, 201)

        # Sell each service and retail category once; only brewed drinks accrue points.
        sale_items = [
            {'id': product['id'], 'type': product['type'], 'price': product['price'], 'qty': 1}
            for product in products.values()
        ]
        sale = self.client.post('/api/sales', json={'customer_id': 1, 'items': sale_items})
        self.assertEqual(sale.status_code, 201)
        self.assertEqual(self.conn.execute('SELECT points FROM Customers WHERE id = 1').fetchone()['points'], 1)

        drink = products['ชาเย็น']
        for _ in range(9):
            response = self.client.post('/api/sales', json={'customer_id': 1, 'items': [
                {'id': drink['id'], 'type': 'Brewed Drink', 'price': 30, 'qty': 1}
            ]})
            self.assertEqual(response.status_code, 201)
        self.assertEqual(self.conn.execute('SELECT points FROM Customers WHERE id = 1').fetchone()['points'], 10)

        eleventh = self.client.post('/api/sales', json={'customer_id': 1, 'redeemed_points': 10, 'items': [
            {'id': drink['id'], 'type': 'Brewed Drink', 'price': 30, 'qty': 1}
        ]})
        self.assertEqual(eleventh.status_code, 201)
        self.assertEqual(eleventh.get_json()['loyalty_discount'], 20)
        self.assertEqual(self.conn.execute('SELECT points FROM Customers WHERE id = 1').fetchone()['points'], 0)
        self.assertEqual(self.conn.execute('SELECT total_amount FROM Sales ORDER BY id DESC LIMIT 1').fetchone()['total_amount'], 10)

        # Retail/water/soft drinks cannot be used to redeem brewed-drink points.
        invalid = self.client.post('/api/sales', json={'customer_id': 1, 'redeemed_points': 10, 'items': [
            {'id': products['น้ำเปล่า']['id'], 'type': 'Water', 'price': 10, 'qty': 1}
        ]})
        self.assertEqual(invalid.status_code, 400)

    def test_debt_payment_records_selected_method(self):
        self.conn.execute('''
            INSERT INTO Sales (total_amount, discount, payment_method, payment_status, customer_id)
            VALUES (100, 0, 'Cash', 'Unpaid', 1)
        ''')
        sale_id = self.conn.execute('SELECT last_insert_rowid()').fetchone()[0]
        self.conn.commit()

        response = self.client.put(f'/api/sales/{sale_id}/pay', json={'payment_method': 'PromptPay'})
        self.assertEqual(response.status_code, 200)
        paid_sale = self.conn.execute('SELECT payment_status, payment_method FROM Sales WHERE id = ?', (sale_id,)).fetchone()
        self.assertEqual(paid_sale['payment_status'], 'Paid')
        self.assertEqual(paid_sale['payment_method'], 'PromptPay')


if __name__ == '__main__':
    unittest.main(verbosity=2)
