import os
import sqlite3
from datetime import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build

SERVICE_ACCOUNT_FILE = 'service_account.json'
SPREADSHEET_ID = '1YL4abwdPgFkzo6fOnj6BUH62jugj4HGe6w7u2ZHD9K0'
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

def ensure_sheet_tabs(service, spreadsheet_id, required_tabs):
    spreadsheet = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    existing_sheets = [s['properties']['title'] for s in spreadsheet.get('sheets', [])]
    
    requests = []
    for tab in required_tabs:
        if tab not in existing_sheets:
            requests.append({
                'addSheet': {
                    'properties': {
                        'title': tab
                    }
                }
            })
            
    if requests:
        service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={'requests': requests}
        ).execute()

def format_sheets(service, spreadsheet_id):
    spreadsheet = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    sheet_map = {s['properties']['title']: s['properties']['sheetId'] for s in spreadsheet.get('sheets', [])}
    
    requests = []
    
    # Freeze row 1 and format header for raw tabs
    for tab in ['Raw_Sales', 'Raw_Stock', 'Raw_Jobs', 'Raw_Debtors']:
        if tab in sheet_map:
            sid = sheet_map[tab]
            requests.append({
                'updateSheetProperties': {
                    'properties': {
                        'sheetId': sid,
                        'gridProperties': {'frozenRowCount': 1}
                    },
                    'fields': 'gridProperties.frozenRowCount'
                }
            })
            requests.append({
                'repeatCell': {
                    'range': {
                        'sheetId': sid,
                        'startRowIndex': 0,
                        'endRowIndex': 1
                    },
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
            
    # Format Dashboard
    if 'Dashboard' in sheet_map:
        sid = sheet_map['Dashboard']
        # Title row
        requests.append({
            'repeatCell': {
                'range': {'sheetId': sid, 'startRowIndex': 0, 'endRowIndex': 1, 'startColumnIndex': 0, 'endColumnIndex': 5},
                'cell': {
                    'userEnteredFormat': {
                        'backgroundColor': {'red': 0.1, 'green': 0.15, 'blue': 0.25},
                        'textFormat': {'bold': True, 'foregroundColor': {'red': 1, 'green': 1, 'blue': 1}, 'fontSize': 13}
                    }
                },
                'fields': 'userEnteredFormat(backgroundColor,textFormat)'
            }
        })
        # Key metrics header row (row index 3)
        requests.append({
            'repeatCell': {
                'range': {'sheetId': sid, 'startRowIndex': 3, 'endRowIndex': 4, 'startColumnIndex': 0, 'endColumnIndex': 4},
                'cell': {
                    'userEnteredFormat': {
                        'backgroundColor': {'red': 0.9, 'green': 0.93, 'blue': 0.98},
                        'textFormat': {'bold': True, 'foregroundColor': {'red': 0.1, 'green': 0.2, 'blue': 0.4}, 'fontSize': 11}
                    }
                },
                'fields': 'userEnteredFormat(backgroundColor,textFormat)'
            }
        })
        # Number formatting for metric values (rows 4 to 8, column B)
        requests.append({
            'repeatCell': {
                'range': {'sheetId': sid, 'startRowIndex': 4, 'endRowIndex': 9, 'startColumnIndex': 1, 'endColumnIndex': 2},
                'cell': {
                    'userEnteredFormat': {
                        'numberFormat': {'type': 'NUMBER', 'pattern': '#,##0.00'},
                        'textFormat': {'bold': True, 'fontSize': 12},
                        'horizontalAlignment': 'RIGHT'
                    }
                },
                'fields': 'userEnteredFormat(numberFormat,textFormat,horizontalAlignment)'
            }
        })

    if requests:
        try:
            service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body={'requests': requests}
            ).execute()
        except Exception as e:
            print("Formatting notice:", e, flush=True)

def sync_data(spreadsheet_id=SPREADSHEET_ID):
    print("Connecting to Google Sheets API...", flush=True)
    service = get_sheets_service()
    tabs = ['Dashboard', 'Raw_Sales', 'Raw_Stock', 'Raw_Jobs', 'Raw_Debtors']
    print("Checking sheet tabs...", flush=True)
    ensure_sheet_tabs(service, spreadsheet_id, tabs)
    print("Reading data from SQLite...", flush=True)
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    now_str = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
    
    # 1. Raw_Sales
    c.execute('''
        SELECT 
            s.id, 
            s.timestamp, 
            COALESCE(s.invoice_no, '-'), 
            COALESCE(c.name, 'ลูกค้าทั่วไป'),
            p.name, 
            p.type, 
            si.qty, 
            si.price,
            (si.qty * si.price) as total_price,
            p.cost,
            (si.qty * (si.price - p.cost)) as profit,
            s.payment_method, 
            s.payment_status
        FROM Sale_Items si
        JOIN Sales s ON si.sale_id = s.id
        JOIN Products_Services p ON si.product_id = p.id
        LEFT JOIN Customers c ON s.customer_id = c.id
        ORDER BY s.id DESC
    ''')
    sales_rows = c.fetchall()
    sales_data = [[
        'รหัสบิล', 'วัน-เวลา', 'เลขที่ใบเสร็จ', 'ลูกค้า', 'สินค้า/บริการ', 
        'ประเภท', 'จำนวน', 'ราคาขาย/หน่วย', 'ยอดรวม', 'ต้นทุน/หน่วย', 
        'กำไร', 'วิธีชำระ', 'สถานะบิล'
    ]]
    for r in sales_rows:
        sales_data.append([
            r[0], str(r[1]), r[2], r[3], r[4], 
            r[5], r[6], r[7], r[8], r[9], 
            r[10], r[11], r[12]
        ])

    # 2. Raw_Stock
    c.execute('''
        SELECT 
            id, 
            COALESCE(barcode, ''), 
            name, 
            type, 
            TRIM(COALESCE(brand,'') || ' ' || COALESCE(model,'') || ' ' || COALESCE(color,'')),
            cost, 
            price, 
            stock_qty, 
            reorder_level,
            CASE 
                WHEN type != 'Product' THEN 'บริการ'
                WHEN stock_qty <= 0 THEN 'สินค้าหมด'
                WHEN stock_qty <= reorder_level THEN 'ใกล้หมด'
                ELSE 'ปกติ'
            END as stock_status
        FROM Products_Services
        WHERE is_active = 1
        ORDER BY type, name
    ''')
    stock_rows = c.fetchall()
    stock_data = [[
        'รหัสสินค้า', 'บาร์โค้ด', 'ชื่อสินค้า/บริการ', 'หมวดหมู่', 'คุณลักษณะ', 
        'ต้นทุน', 'ราคาขาย', 'คงเหลือ', 'จุดสั่งซื้อ', 'สถานะสต็อก'
    ]]
    for r in stock_rows:
        stock_data.append([
            r[0], str(r[1]), r[2], r[3], r[4], 
            r[5], r[6], r[7], r[8], r[9]
        ])

    # 3. Raw_Jobs
    c.execute('''
        SELECT 
            id, 
            timestamp, 
            COALESCE(customer_name, '-'), 
            COALESCE(details, '-'), 
            qty, 
            deposit, 
            status
        FROM Job_Orders
        ORDER BY id DESC
    ''')
    job_rows = c.fetchall()
    job_data = [[
        'รหัสงาน', 'วันที่สั่ง', 'ชื่อลูกค้า', 'รายละเอียดงาน', 
        'จำนวน', 'เงินมัดจำ', 'สถานะงาน'
    ]]
    for r in job_rows:
        job_data.append([
            r[0], str(r[1]), r[2], r[3], r[4], r[5], r[6]
        ])

    # 4. Raw_Debtors
    c.execute('''
        SELECT 
            cc.id, 
            cc.timestamp, 
            c.name, 
            COALESCE(c.phone, '-'),
            COALESCE(s.invoice_no, '-'),
            cc.amount_due, 
            cc.amount_paid,
            (cc.amount_due - cc.amount_paid) as balance_due,
            cc.status
        FROM Customer_Credit cc
        JOIN Customers c ON cc.customer_id = c.id
        LEFT JOIN Sales s ON cc.sale_id = s.id
        ORDER BY cc.status ASC, cc.id DESC
    ''')
    debtor_rows = c.fetchall()
    debtor_data = [[
        'รหัสบันทึก', 'วันที่', 'ชื่อลูกค้า', 'เบอร์โทรศัพท์', 
        'เลขที่ใบเสร็จ', 'ยอดเต็ม', 'ชำระแล้ว', 'ยอดค้างชำระ', 'สถานะ'
    ]]
    for r in debtor_rows:
        debtor_data.append([
            r[0], str(r[1]), r[2], r[3], r[4], 
            r[5], r[6], r[7], r[8]
        ])

    # 5. Dashboard Setup
    dashboard_data = [
        ['PJ COPY SHOP - สรุปรายงานภาพรวมธุรกิจ (POS Dashboard)', '', '', '', ''],
        ['อัปเดตข้อมูลล่าสุด:', now_str, '', 'ซิงค์จากระบบ POS อัตโนมัติ', ''],
        ['', '', '', '', ''],
        ['📌 ดัชนีชี้วัดสำคัญ (Key Metrics)', 'ค่าปัจจุบัน', 'หน่วย', 'คำอธิบาย', ''],
        ['💰 ยอดขายรวมทั้งหมด (Total Sales)', '=IFERROR(SUM(Raw_Sales!I2:I), 0)', 'บาท', 'ยอดรวมจากรายการขายทั้งหมด', ''],
        ['📈 กำไรขั้นต้นรวม (Gross Profit)', '=IFERROR(SUM(Raw_Sales!K2:K), 0)', 'บาท', 'กำไรรวมก่อนหักค่าใช้จ่าย', ''],
        ['⚠️ ยอดลูกหนี้ค้างชำระรวม (Debtors)', '=IFERROR(SUM(Raw_Debtors!H2:H), 0)', 'บาท', 'ยอดเงินที่ลูกหนี้ยังค้างจ่าย', ''],
        ['📋 งานสั่งทำค้างส่ง (Pending Jobs)', '=COUNTIF(Raw_Jobs!G2:G, "<>เสร็จสิ้น") - 1', 'รายการ', 'งานที่ยังไม่เสร็จสิ้น', ''],
        ['🚨 สินค้าใกล้หมด / สินค้าหมด', '=COUNTIF(Raw_Stock!J2:J, "ใกล้หมด") + COUNTIF(Raw_Stock!J2:J, "สินค้าหมด")', 'รายการ', 'สินค้าที่ต้องสั่งซื้อเพิ่ม', ''],
        ['', '', '', '', ''],
        ['💡 วิธีดูรายงานผ่านมือถือ / ภายนอกร้าน:', '', '', '', ''],
        ['1. เปิด Google Sheets ผ่านแอปในมือถือได้ทุกที่ ทุกเวลา', '', '', '', ''],
        ['2. แผ่นงาน Raw_Sales: ใช้ดูประวัติการขาย และสร้าง Pivot Table / Filter ตามวันที่ที่ต้องการ', '', '', '', ''],
        ['3. แผ่นงาน Raw_Stock: เช็คจำนวนสต็อกก่อนสั่งซื้อของเข้าร้าน', '', '', '', ''],
        ['4. แผ่นงาน Raw_Debtors: เช็ครายชื่อและเบอร์โทรลูกค้าที่ค้างชำระ', '', '', '', ''],
        ['5. แผ่นงาน Raw_Jobs: เช็คสถานะงานสั่งทำที่ค้างส่งมอบ', '', '', '', '']
    ]

    conn.close()

    # Clear and update each sheet
    def update_tab(tab_name, data):
        # Clear existing
        service.spreadsheets().values().clear(
            spreadsheetId=spreadsheet_id,
            range=f"'{tab_name}'!A1:Z50000"
        ).execute()
        # Write new
        service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=f"'{tab_name}'!A1",
            valueInputOption='USER_ENTERED',
            body={'values': data}
        ).execute()

    print("Updating Raw_Sales...", flush=True)
    update_tab('Raw_Sales', sales_data)
    print("Updating Raw_Stock...", flush=True)
    update_tab('Raw_Stock', stock_data)
    print("Updating Raw_Jobs...", flush=True)
    update_tab('Raw_Jobs', job_data)
    print("Updating Raw_Debtors...", flush=True)
    update_tab('Raw_Debtors', debtor_data)
    print("Updating Dashboard...", flush=True)
    update_tab('Dashboard', dashboard_data)

    print("Applying styling and formatting...", flush=True)
    format_sheets(service, spreadsheet_id)

    return {
        'status': 'success',
        'sales_count': len(sales_data) - 1,
        'stock_count': len(stock_data) - 1,
        'job_count': len(job_data) - 1,
        'debtor_count': len(debtor_data) - 1,
        'updated_at': now_str
    }

if __name__ == '__main__':
    print("Starting sync to Google Sheets...")
    result = sync_data()
    print("Sync complete:", result)
