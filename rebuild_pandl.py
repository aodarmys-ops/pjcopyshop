import os
import re

with open(r'd:\xerox\templates\reports.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace the dashboard section
start_marker = '        <!-- Financial Statements (2 Sides) -->'
end_marker = '        <!-- Tables -->'
start_idx = content.find(start_marker)
end_idx = content.find(end_marker)

if start_idx == -1 or end_idx == -1:
    print("Could not find new dashboard markers. Searching for old markers...")
    start_marker = '        <!-- Dashboard Stats -->'
    start_idx = content.find(start_marker)
    if start_idx == -1 or end_idx == -1:
        print("Error: Could not find dashboard section.")
        exit(1)

new_dashboard = """        <!-- Profit & Loss Dashboard -->
        <div class="card mb-4 border-0 shadow-sm" style="border-top: 5px solid #0d6efd !important; border-radius: 10px;">
            <div class="card-body p-4">
                <h5 class="fw-bold text-primary mb-1"><span class="fs-4">📈</span> มุมมองกำไรขาดทุน (Profit & Loss)</h5>
                <small class="text-muted d-block mb-4">สะท้อนผลประกอบการว่า "ธุรกิจมีกำไรหรือไม่" (ตามหลักบัญชี)</small>

                <div class="d-flex justify-content-between mb-2">
                    <span class="text-secondary fw-bold">ยอดขายรวม (New Sales)</span>
                    <span class="fw-bold text-success fs-5" id="valRevenue">0.00</span>
                </div>
                
                <div class="d-flex justify-content-between mb-2">
                    <span class="text-secondary fw-bold">หัก: ต้นทุนสินค้าขาย (Cost of Goods)</span>
                    <span class="fw-bold text-danger fs-5" id="valCostOfGoods">-0.00</span>
                </div>

                <div class="d-flex justify-content-between mb-3">
                    <span class="text-secondary fw-bold">หัก: รายจ่ายดำเนินงาน (Expenses)</span>
                    <span class="fw-bold text-danger fs-5" id="valExpenses">-0.00</span>
                </div>
                
                <hr class="mb-4">

                <div class="d-flex justify-content-between align-items-center">
                    <h4 class="fw-bold m-0 text-dark">กำไรสุทธิ (Net Profit)</h4>
                    <h2 class="fw-bold m-0" id="valNetProfit">0.00</h2>
                </div>
            </div>
        </div>

        <div class="row g-3 mb-4">
            <div class="col-md-4">
                <div class="card border-0 shadow-sm rounded-4 text-center p-3 h-100" style="border-bottom: 4px solid #333 !important;">
                    <small class="text-muted fw-bold mb-2">รับเงินสด</small>
                    <h4 class="fw-bold m-0" id="valCash">0.00</h4>
                </div>
            </div>
            <div class="col-md-4">
                <div class="card border-0 shadow-sm rounded-4 text-center p-3 h-100" style="border-bottom: 4px solid #0dcaf0 !important;">
                    <small class="text-muted fw-bold mb-2">รับเงินโอน</small>
                    <h4 class="fw-bold m-0 text-info" id="valTransfer">0.00</h4>
                </div>
            </div>
            <div class="col-md-4">
                <div class="card border-0 shadow-sm rounded-4 text-center p-3 h-100" style="border-bottom: 4px solid #0d6efd !important;">
                    <small class="text-muted fw-bold mb-2">รับชำระผ่านเครดิต</small>
                    <h4 class="fw-bold m-0 text-primary" id="valCredit">0.00</h4>
                </div>
            </div>
        </div>

"""
content = content[:start_idx] + new_dashboard + content[end_idx:]

# Update JS to fill the new layout
js_old = """            document.getElementById('valRevenue').innerText = fmt(data.total_revenue);
            document.getElementById('valExpenses').innerText = fmt(data.total_expenses);
            document.getElementById('valExpensesDetail').innerText = fmt(data.total_expenses);
            document.getElementById('valCash').innerText = fmt(data.cash_total);
            document.getElementById('valTransfer').innerText = fmt(data.transfer_total);
            document.getElementById('valBrewed').innerText = fmt(data.brewed_total);
            
            const profitEl = document.getElementById('valNetProfit');
            profitEl.innerText = fmt(data.net_profit);
            if(data.net_profit < 0) {
                profitEl.classList.remove('text-primary');
                profitEl.classList.add('text-danger');
            }"""

js_fallback = """            document.getElementById('valRevenue').innerText = fmt(data.total_revenue);
            document.getElementById('valExpenses').innerText = fmt(data.total_expenses);
            document.getElementById('valCash').innerText = fmt(data.cash_total);
            document.getElementById('valTransfer').innerText = fmt(data.transfer_total);
            document.getElementById('valBrewed').innerText = fmt(data.brewed_total);
            
            const profitEl = document.getElementById('valNetProfit');
            profitEl.innerText = fmt(data.net_profit);
            if(data.net_profit < 0) {
                profitEl.classList.remove('text-primary');
                profitEl.classList.add('text-danger');
            }"""

js_new = """            const revenue = parseFloat(data.total_revenue) || 0;
            const cost = parseFloat(data.total_cost) || 0;
            const expenses = parseFloat(data.total_expenses) || 0;
            const netProfit = revenue - cost - expenses;

            // Note: The user requested NO ฿ symbol and use fmt() which uses commas and 2 decimals.
            // We prepend with '-' manually for negative visualizations where appropriate.
            document.getElementById('valRevenue').innerText = fmt(revenue);
            document.getElementById('valCostOfGoods').innerText = cost > 0 ? "-" + fmt(cost) : "0.00";
            document.getElementById('valExpenses').innerText = expenses > 0 ? "-" + fmt(expenses) : "0.00";
            
            document.getElementById('valCash').innerText = fmt(data.cash_total);
            document.getElementById('valTransfer').innerText = fmt(data.transfer_total);
            document.getElementById('valCredit').innerText = fmt(data.credit_total || 0);
            
            const profitEl = document.getElementById('valNetProfit');
            profitEl.innerText = fmt(netProfit);
            if(netProfit < 0) {
                profitEl.classList.remove('text-success');
                profitEl.classList.add('text-danger');
            } else {
                profitEl.classList.remove('text-danger');
                profitEl.classList.add('text-success');
            }"""

if js_old in content:
    content = content.replace(js_old, js_new)
elif js_fallback in content:
    content = content.replace(js_fallback, js_new)
else:
    # We will regex replace it
    pattern = re.compile(r"document\.getElementById\('valRevenue'\)\.innerText = fmt\(data\.total_revenue\);.*?\}", re.DOTALL)
    content = pattern.sub(js_new, content)

with open(r'd:\xerox\templates\reports.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated reports.html to Profit & Loss layout.")
