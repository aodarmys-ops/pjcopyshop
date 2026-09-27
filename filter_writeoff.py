import re

with open(r'd:\xerox\app.py', 'r', encoding='utf-8') as f:
    app_content = f.read()

# Update get_writeoff_history in app.py
old_endpoint = """@app.route('/api/inventory/writeoff', methods=['GET'])
def get_writeoff_history():
    conn = get_db_connection()
    history = conn.execute('''
        SELECT w.id, w.qty, w.reason, w.timestamp, p.name, p.barcode
        FROM Stock_WriteOffs w
        JOIN Products_Services p ON w.product_id = p.id
        ORDER BY w.timestamp DESC
    ''').fetchall()
    conn.close()
    return jsonify([dict(ix) for ix in history])"""

new_endpoint = """@app.route('/api/inventory/writeoff', methods=['GET'])
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
    return jsonify([dict(ix) for ix in history])"""

if old_endpoint in app_content:
    app_content = app_content.replace(old_endpoint, new_endpoint)
    with open(r'd:\xerox\app.py', 'w', encoding='utf-8') as f:
        f.write(app_content)
    print("Updated app.py")


with open(r'd:\xerox\templates\inventory.html', 'r', encoding='utf-8') as f:
    inv_content = f.read()

# Update HTML for Writeoff History Modal to include filters
old_html = """                <div class="modal-body">
                    <div class="table-responsive">
                        <table class="table table-hover align-middle">"""

new_html = """                <div class="modal-body">
                    <div class="row align-items-end mb-3">
                        <div class="col-md-4 mb-2 mb-md-0">
                            <label class="form-label text-muted small fw-bold">ตั้งแต่วันที่</label>
                            <input type="date" id="woStartDate" class="form-control rounded-pill">
                        </div>
                        <div class="col-md-4 mb-2 mb-md-0">
                            <label class="form-label text-muted small fw-bold">ถึงวันที่</label>
                            <input type="date" id="woEndDate" class="form-control rounded-pill">
                        </div>
                        <div class="col-md-4 d-flex gap-2">
                            <button class="btn btn-primary w-100 rounded-pill fw-bold" onclick="showWriteoffHistory()">🔍 กรอง</button>
                            <button class="btn btn-outline-secondary w-100 rounded-pill fw-bold" onclick="clearWriteoffFilter()">❌ ล้าง</button>
                        </div>
                    </div>
                    <div class="table-responsive">
                        <table class="table table-hover align-middle">"""

if old_html in inv_content:
    inv_content = inv_content.replace(old_html, new_html)

# Update Javascript logic in inventory.html
old_js = """        async function showWriteoffHistory() {
            const res = await fetch('/api/inventory/writeoff');
            const data = await res.json();
            const tbody = document.getElementById('woHistoryTable');"""

new_js = """        async function showWriteoffHistory() {
            const startDate = document.getElementById('woStartDate') ? document.getElementById('woStartDate').value : '';
            const endDate = document.getElementById('woEndDate') ? document.getElementById('woEndDate').value : '';
            
            let url = '/api/inventory/writeoff';
            if (startDate && endDate) {
                url += `?start_date=${startDate}&end_date=${endDate}`;
            }

            const res = await fetch(url);
            const data = await res.json();
            const tbody = document.getElementById('woHistoryTable');"""

if old_js in inv_content:
    inv_content = inv_content.replace(old_js, new_js)

# Add clearWriteoffFilter function
clear_fn = """        function clearWriteoffFilter() {
            document.getElementById('woStartDate').value = '';
            document.getElementById('woEndDate').value = '';
            showWriteoffHistory();
        }"""

if clear_fn not in inv_content:
    inv_content = inv_content.replace('        async function showWriteoffHistory() {', clear_fn + '\n\n        async function showWriteoffHistory() {')

with open(r'd:\xerox\templates\inventory.html', 'w', encoding='utf-8') as f:
    f.write(inv_content)
print("Updated inventory.html")
