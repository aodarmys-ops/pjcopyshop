import os
import sqlite3
from datetime import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build

SERVICE_ACCOUNT_FILE = 'service_account.json'
SPREADSHEET_ID = '1AR2YDX190eTCFEvDyFkVcGM11TVZLL-R0WL1STf-2HM'
DB_FILE = 'xerox.db'

SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

def get_sheets_service():
    if not os.path.exists(SERVICE_ACCOUNT_FILE):
        raise FileNotFoundError(f"Missing {SERVICE_ACCOUNT_FILE}")
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES
    )
    return build('sheets', 'v4', credentials=creds)

def ensure_and_format_tabs_if_needed(service, spreadsheet_id, required_tabs):
    spreadsheet = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    existing_sheets = {s['properties']['title']: s['properties']['sheetId'] for s in spreadsheet.get('sheets', [])}
    
    missing_tabs = [t for t in required_tabs if t not in existing_sheets]
    if not missing_tabs:
        return # Skip entirely to save time!

    # Create missing tabs
    requests = [{'addSheet': {'properties': {'title': tab}}} for tab in missing_tabs]
    response = service.spreadsheets().batchUpdate(spreadsheetId=spreadsheet_id, body={'requests': requests}).execute()
    
    # Extract new sheet IDs
    for reply in response.get('replies', []):
        new_sheet = reply.get('addSheet', {}).get('properties', {})
        if 'title' in new_sheet and 'sheetId' in new_sheet:
            existing_sheets[new_sheet['title']] = new_sheet['sheetId']

    # Apply formatting only to raw tabs
    format_requests = []
    raw_tabs = ['Raw_Sales', 'Raw_Stock', 'Raw_Jobs', 'Raw_Debtors', 'Raw_Expenses', 'Raw_Adjustments', 'Raw_Purchases']
    for tab in missing_tabs:
        if tab in raw_tabs and tab in existing_sheets:
            sid = existing_sheets[tab]
            format_requests.append({
                'updateSheetProperties': {
                    'properties': {'sheetId': sid, 'gridProperties': {'frozenRowCount': 1}},
                    'fields': 'gridProperties.frozenRowCount'
                }
            })
            format_requests.append({
                'repeatCell': {
                    'range': {'sheetId': sid, 'startRowIndex': 0, 'endRowIndex': 1},
                    'cell': {
                        'userEnteredFormat': {
                            'backgroundColor': {'red': 0.15, 'green': 0.23, 'blue': 0.36},
                            'textFormat': {'bold': True, 'foregroundColor': {'red': 1, 'green': 1, 'blue': 1}, 'fontSize': 10},
                            'horizontalAlignment': 'CENTER'
                        }
                    },
                    'fields': 'userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)'
                }
            })
            
    if format_requests:
        try:
            service.spreadsheets().batchUpdate(spreadsheetId=spreadsheet_id, body={'requests': format_requests}).execute()
        except Exception as e:
            print("Formatting notice:", e, flush=True)

def sync_data(spreadsheet_id=SPREADSHEET_ID):
    print("Connecting to Google Sheets API...", flush=True)
    service = get_sheets_service()
    
    tabs = ['Dashboard', 'Raw_Sales', 'Raw_Stock', 'Raw_Jobs', 'Raw_Debtors', 'Raw_Expenses', 'Raw_Adjustments', 'Raw_Purchases']
    ensure_and_format_tabs_if_needed(service, spreadsheet_id, tabs)
    
    print("Reading data from SQLite...", flush=True)
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    now_str = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
    
    # 1. Raw_Sales
    c.execute('''
        SELECT 
            s.id, s.timestamp, COALESCE(s.invoice_no, '-'), COALESCE(c.name, 'ลูกค้าทั่วไป'),
            p.name, p.type, si.qty, si.price, (si.qty * si.price) as total_price,
            si.cost_price, (si.qty * (si.price - si.cost_price)) as profit, s.payment_method, s.split_cash, s.split_transfer, s.payment_status
        FROM Sale_Items si
        JOIN Sales s ON si.sale_id = s.id
        JOIN Products_Services p ON si.product_id = p.id
        LEFT JOIN Customers c ON s.customer_id = c.id
        WHERE s.timestamp >= datetime('now', '-90 days')
        ORDER BY s.id DESC
    ''')
    sales_rows = c.fetchall()
    sales_data = [['รหัสบิล', 'วัน-เวลา', 'เลขที่ใบเสร็จ', 'ลูกค้า', 'สินค้า/บริการ', 'ประเภท', 'จำนวน', 'ราคาขาย/หน่วย', 'ยอดรวม', 'ต้นทุน/หน่วย', 'กำไร', 'วิธีชำระ', 'เงินสด (Split)', 'เงินโอน (Split)', 'สถานะบิล']]
    for r in sales_rows: sales_data.append([r[0], str(r[1]), r[2], r[3], r[4], r[5], r[6], r[7], r[8], r[9], r[10], r[11], r[12], r[13], r[14]])

    # 2. Raw_Stock
    c.execute('''
        SELECT id, COALESCE(barcode, ''), name, type, TRIM(COALESCE(brand,'') || ' ' || COALESCE(model,'') || ' ' || COALESCE(color,'')),
               cost, price, stock_qty, reorder_level,
               CASE WHEN type != 'Product' THEN 'บริการ' WHEN stock_qty <= 0 THEN 'สินค้าหมด' WHEN stock_qty <= reorder_level THEN 'ใกล้หมด' ELSE 'ปกติ' END,
               COALESCE(base_unit, 'ชิ้น'), COALESCE(purchase_unit, ''), COALESCE(conversion_rate, 1)
        FROM Products_Services WHERE is_active = 1 ORDER BY type, name
    ''')
    stock_rows = c.fetchall()
    stock_data = [['รหัสสินค้า', 'บาร์โค้ด', 'ชื่อสินค้า/บริการ', 'หมวดหมู่', 'คุณลักษณะ', 'ต้นทุน', 'ราคาขาย', 'คงเหลือ', 'จุดสั่งซื้อ', 'สถานะสต็อก', 'หน่วยนับ(Base)', 'หน่วยซื้อ', 'ตัวคูณ']]
    for r in stock_rows: stock_data.append([r[0], str(r[1]), r[2], r[3], r[4], r[5], r[6], r[7], r[8], r[9], r[10], r[11], r[12]])

    # 3. Raw_Jobs
    c.execute("SELECT id, timestamp, COALESCE(customer_name, '-'), COALESCE(details, '-'), qty, price, deposit, status, due_date FROM Job_Orders WHERE timestamp >= datetime('now', '-90 days') OR status NOT IN ('Completed', 'เสร็จแล้ว', 'ส่งมอบแล้ว', 'ยกเลิก') ORDER BY id DESC")
    job_rows = c.fetchall()
    job_data = [['รหัสงาน', 'วันที่สั่ง', 'ชื่อลูกค้า', 'รายละเอียดงาน', 'จำนวน', 'ราคาประเมิน', 'เงินมัดจำ', 'สถานะงาน', 'กำหนดส่ง']]
    for r in job_rows: job_data.append([r[0], str(r[1]), r[2], r[3], r[4], r[5], r[6], r[7], str(r[8] or '-')])

    # 4. Raw_Debtors
    c.execute('''
        SELECT cc.id, cc.timestamp, c.name, COALESCE(c.phone, '-'), COALESCE(s.invoice_no, '-'), cc.amount_due, cc.amount_paid, (cc.amount_due - cc.amount_paid), cc.status
        FROM Customer_Credit cc JOIN Customers c ON cc.customer_id = c.id LEFT JOIN Sales s ON cc.sale_id = s.id ORDER BY cc.status ASC, cc.id DESC
    ''')
    debtor_rows = c.fetchall()
    debtor_data = [['รหัสบันทึก', 'วันที่', 'ชื่อลูกค้า', 'เบอร์โทรศัพท์', 'เลขที่ใบเสร็จ', 'ยอดเต็ม', 'ชำระแล้ว', 'ยอดค้างชำระ', 'สถานะ']]
    for r in debtor_rows: debtor_data.append([r[0], str(r[1]), r[2], r[3], r[4], r[5], r[6], r[7], r[8]])

    # 5. Raw_Expenses (NEW)
    c.execute("SELECT id, timestamp, description, amount, expense_type, payment_method FROM Expenses WHERE timestamp >= datetime('now', '-90 days') ORDER BY timestamp DESC")
    exp_rows = c.fetchall()
    exp_data = [['รหัส', 'วันที่', 'รายละเอียด', 'ยอดเงิน', 'ประเภท', 'วิธีชำระ']]
    for r in exp_rows: exp_data.append([r[0], str(r[1]), r[2], r[3], r[4], r[5]])

    # 6. Raw_Adjustments (NEW)
    c.execute('''
        SELECT sc.id, sc.count_date, p.name, c.system_qty, c.counted_qty, c.variance, p.cost, (c.variance * p.cost)
        FROM Stock_Count_Items c
        JOIN Stock_Counts sc ON c.count_id = sc.id
        JOIN Products_Services p ON c.product_id = p.id
        WHERE c.variance != 0 AND sc.count_date >= datetime('now', '-90 days') ORDER BY sc.count_date DESC
    ''')
    adj_rows = c.fetchall()
    adj_data = [['รหัสอ้างอิง', 'วันที่', 'ชื่อสินค้า', 'สต๊อกระบบ', 'นับจริง', 'ส่วนต่าง', 'ต้นทุน/ชิ้น', 'ยอดเงินปรับปรุง']]
    for r in adj_rows: adj_data.append([r[0], str(r[1]), r[2], r[3], r[4], r[5], r[6], r[7]])

    # 7. Raw_Purchases (NEW)
    c.execute("SELECT id, timestamp, supplier_name, total_amount, payment_method FROM Purchases WHERE timestamp >= datetime('now', '-90 days') ORDER BY timestamp DESC")
    pur_rows = c.fetchall()
    pur_data = [['รหัส', 'วันที่', 'ซัพพลายเออร์', 'ยอดเงิน', 'วิธีชำระ']]
    for r in pur_rows: pur_data.append([r[0], str(r[1]), r[2], r[3], r[4]])

    conn.close()

    print("Updating tabs (Batch Mode)...", flush=True)
    
    # 1. เคลียร์ข้อมูลทุกชีตพร้อมกันใน 1 คำขอ
    clear_ranges = [
        "'Raw_Sales'!A1:Z50000", "'Raw_Stock'!A1:Z50000", "'Raw_Jobs'!A1:Z50000", 
        "'Raw_Debtors'!A1:Z50000", "'Raw_Expenses'!A1:Z50000", "'Raw_Adjustments'!A1:Z50000", "'Raw_Purchases'!A1:Z50000"
    ]
    service.spreadsheets().values().batchClear(
        spreadsheetId=spreadsheet_id, 
        body={'ranges': clear_ranges}
    ).execute()
    
    # 2. อัปเดตข้อมูลทุกชีตพร้อมกันใน 1 คำขอ
    data_to_update = [
        {'range': "'Raw_Sales'!A1", 'values': sales_data},
        {'range': "'Raw_Stock'!A1", 'values': stock_data},
        {'range': "'Raw_Jobs'!A1", 'values': job_data},
        {'range': "'Raw_Debtors'!A1", 'values': debtor_data},
        {'range': "'Raw_Expenses'!A1", 'values': exp_data},
        {'range': "'Raw_Adjustments'!A1", 'values': adj_data},
        {'range': "'Raw_Purchases'!A1", 'values': pur_data}
    ]
    service.spreadsheets().values().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body={
            'valueInputOption': 'USER_ENTERED',
            'data': data_to_update
        }
    ).execute()

    # Removed duplicate format_sheets call to speed up sync
    return {
        'status': 'success',
        'updated_at': now_str
    }

if __name__ == '__main__':
    print("Starting sync to Google Sheets...")
    result = sync_data()
    print("Sync complete:", result)