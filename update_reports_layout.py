import re

with open(r'd:\xerox\templates\reports.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace the 6-box Dashboard Stats with 2-side layout
old_dashboard_start = '        <!-- Dashboard Stats -->'
old_dashboard_end = '        <!-- Tables -->'

# Find the slice
start_idx = content.find(old_dashboard_start)
end_idx = content.find(old_dashboard_end)

if start_idx != -1 and end_idx != -1:
    new_dashboard = """        <!-- Financial Statements (2 Sides) -->
        <div class="row g-4 mb-4">
            <!-- Left Side: Income -->
            <div class="col-md-6">
                <div class="glass-card h-100 border-top border-5 border-success">
                    <h5 class="fw-bold text-success mb-3">📈 ฝั่งรายรับ (Income)</h5>
                    <div class="d-flex justify-content-between mb-2">
                        <span class="text-muted fw-bold">รับเงินสด (Cash)</span>
                        <span class="fw-bold text-dark fs-5" id="valCash">0.00</span>
                    </div>
                    <div class="d-flex justify-content-between mb-2">
                        <span class="text-muted fw-bold">รับเงินโอน (Transfer)</span>
                        <span class="fw-bold text-info fs-5" id="valTransfer">0.00</span>
                    </div>
                    <div class="d-flex justify-content-between mb-2">
                        <span class="text-muted fw-bold">ยอดขายเฉพาะเครื่องดื่มชง</span>
                        <span class="fw-bold text-warning text-dark fs-5" id="valBrewed">0.00</span>
                    </div>
                    <hr>
                    <div class="d-flex justify-content-between align-items-center mt-3">
                        <h5 class="fw-bold text-muted m-0">รวมยอดขาย (Total Revenue)</h5>
                        <h3 class="fw-bold text-success m-0" id="valRevenue">0.00</h3>
                    </div>
                </div>
            </div>

            <!-- Right Side: Expenses -->
            <div class="col-md-6">
                <div class="glass-card h-100 border-top border-5 border-danger d-flex flex-column">
                    <h5 class="fw-bold text-danger mb-3">📉 ฝั่งรายจ่าย (Expenses)</h5>
                    <div class="d-flex justify-content-between mb-2 flex-grow-1">
                        <span class="text-muted fw-bold">ต้นทุนสินค้า / ค่าใช้จ่ายเบ็ดเตล็ด</span>
                        <span class="fw-bold text-danger fs-5" id="valExpensesDetail">0.00</span>
                    </div>
                    <hr class="mt-auto">
                    <div class="d-flex justify-content-between align-items-center mt-3">
                        <h5 class="fw-bold text-muted m-0">รวมรายจ่าย (Total Expenses)</h5>
                        <h3 class="fw-bold text-danger m-0" id="valExpenses">0.00</h3>
                    </div>
                </div>
            </div>
        </div>

        <!-- Net Profit -->
        <div class="row mb-4">
            <div class="col-12">
                <div class="glass-card text-center border-bottom border-5 border-primary p-4 shadow-sm">
                    <h4 class="text-muted fw-bold mb-3">💰 กำไรสุทธิ (Net Profit)</h4>
                    <div class="stat-value text-primary fw-bold" id="valNetProfit" style="font-size: 3.5rem;">0.00</div>
                </div>
            </div>
        </div>

"""
    content = content[:start_idx] + new_dashboard + content[end_idx:]
    
    # We need to make sure valExpenses updates valExpensesDetail as well for visual symmetry
    js_update = """
            document.getElementById('valExpenses').innerText = formatMoney(data.total_expenses);
            document.getElementById('valExpensesDetail').innerText = formatMoney(data.total_expenses);
    """
    if "document.getElementById('valExpensesDetail').innerText" not in content:
        content = content.replace("document.getElementById('valExpenses').innerText = formatMoney(data.total_expenses);", js_update)

    with open(r'd:\xerox\templates\reports.html', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Updated reports dashboard layout.")
else:
    print("Could not find dashboard section.")
