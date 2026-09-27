import re

with open(r'd:\xerox\templates\reports.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Wrap the Profit & Loss card in a col-md-6 and add Cash Flow in another col-md-6
target_start = '        <!-- Profit & Loss Dashboard -->'
target_end = '        <div class="row g-3 mb-4">'

start_idx = content.find(target_start)
end_idx = content.find(target_end)

if start_idx != -1 and end_idx != -1:
    new_html = """        <!-- Financial Dashboards -->
        <div class="row g-4 mb-4">
            <!-- Profit & Loss Dashboard -->
            <div class="col-md-6">
                <div class="card border-0 shadow-sm h-100" style="border-top: 5px solid #0d6efd !important; border-radius: 10px;">
                    <div class="card-body p-4 d-flex flex-column">
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
                        
                        <hr class="mt-auto mb-4">

                        <div class="d-flex justify-content-between align-items-center">
                            <h4 class="fw-bold m-0 text-dark">กำไรสุทธิ (Net Profit)</h4>
                            <h2 class="fw-bold m-0" id="valNetProfit">0.00</h2>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Cash Flow Dashboard -->
            <div class="col-md-6">
                <div class="card border-0 shadow-sm h-100" style="border-top: 5px solid #198754 !important; border-radius: 10px;">
                    <div class="card-body p-4 d-flex flex-column">
                        <h5 class="fw-bold text-success mb-1"><span class="fs-4">💸</span> มุมมองกระแสเงินสด (Cash Flow)</h5>
                        <small class="text-muted d-block mb-4">สะท้อนการเข้า-ออกของเงิน ว่า "มีเงินเหลือในมือเท่าไหร่"</small>

                        <div class="d-flex justify-content-between mb-2">
                            <span class="text-secondary fw-bold">รับเงินสด (Cash In)</span>
                            <span class="fw-bold text-success fs-5" id="valCashFlowIn">0.00</span>
                        </div>
                        
                        <div class="d-flex justify-content-between mb-2">
                            <span class="text-secondary fw-bold">รับเงินโอน / ช่องทางอื่นๆ</span>
                            <span class="fw-bold text-success fs-5" id="valTransferIn">0.00</span>
                        </div>

                        <div class="d-flex justify-content-between mb-2">
                            <span class="text-secondary fw-bold">หัก: ซื้อสินค้าเข้าสต๊อก (Purchases)</span>
                            <span class="fw-bold text-danger fs-5" id="valPurchasesOut">-0.00</span>
                        </div>

                        <div class="d-flex justify-content-between mb-3">
                            <span class="text-secondary fw-bold">หัก: จ่ายบิลต่างๆ (Expenses)</span>
                            <span class="fw-bold text-danger fs-5" id="valExpensesOut">-0.00</span>
                        </div>
                        
                        <hr class="mt-auto mb-4">

                        <div class="d-flex justify-content-between align-items-center">
                            <h4 class="fw-bold m-0 text-dark">เงินสดคงเหลือสุทธิ (Net Cash)</h4>
                            <h2 class="fw-bold m-0" id="valNetCashFlow">0.00</h2>
                        </div>
                    </div>
                </div>
            </div>
        </div>
"""
    content = content[:start_idx] + new_html + content[end_idx:]

    # Update JS logic for Cash Flow
    js_update = """            
            // Cash Flow Calculation
            const cashIn = parseFloat(data.cash_total) || 0;
            const transferIn = (parseFloat(data.transfer_total) || 0) + (parseFloat(data.paid_unpaid_total) || 0);
            const purchases = parseFloat(data.total_purchases) || 0;
            const netCashFlow = cashIn + transferIn - purchases - expenses;

            document.getElementById('valCashFlowIn').innerText = fmt(cashIn);
            document.getElementById('valTransferIn').innerText = fmt(transferIn);
            document.getElementById('valPurchasesOut').innerText = purchases > 0 ? "-" + fmt(purchases) : "0.00";
            document.getElementById('valExpensesOut').innerText = expenses > 0 ? "-" + fmt(expenses) : "0.00";

            const cashEl = document.getElementById('valNetCashFlow');
            cashEl.innerText = fmt(netCashFlow);
            if(netCashFlow < 0) {
                cashEl.classList.remove('text-success');
                cashEl.classList.add('text-danger');
            } else {
                cashEl.classList.remove('text-danger');
                cashEl.classList.add('text-success');
            }
"""
    
    # insert before `const profitEl = document.getElementById('valNetProfit');`
    js_anchor = "            const profitEl = document.getElementById('valNetProfit');"
    if js_update not in content:
        content = content.replace(js_anchor, js_update + "\n" + js_anchor)

    with open(r'd:\xerox\templates\reports.html', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Updated reports.html with Cash Flow.")
else:
    print("Could not find insertion points.")
