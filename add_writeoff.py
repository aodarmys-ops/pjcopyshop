import re

with open(r'd:\xerox\templates\inventory.html', 'r', encoding='utf-8') as f:
    content = f.read()

modals = """
    <!-- WriteOff Modal -->
    <div class="modal fade" id="writeoffModal" tabindex="-1">
        <div class="modal-dialog">
            <div class="modal-content glass-card border-0">
                <div class="modal-header border-0">
                    <h5 class="modal-title fw-bold">✂️ ตัดชำรุด/เสียหาย</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body">
                    <p><strong>สินค้า:</strong> <span id="woProductName"></span></p>
                    <p><strong>คงเหลือปัจจุบัน:</strong> <span id="woCurrentStock" class="fw-bold text-primary"></span> ชิ้น</p>
                    <hr>
                    <div class="mb-3">
                        <label class="form-label">จำนวนที่ต้องการตัดออก</label>
                        <input type="number" id="woQty" class="form-control" min="1" value="1">
                    </div>
                    <div class="mb-3">
                        <label class="form-label">สาเหตุ</label>
                        <select id="woReason" class="form-select">
                            <option value="ชำรุด/เสียหาย">ชำรุด/เสียหาย</option>
                            <option value="สูญหาย">สูญหาย</option>
                            <option value="เบิกใช้ภายในร้าน">เบิกใช้ภายในร้าน</option>
                            <option value="อื่นๆ">อื่นๆ</option>
                        </select>
                    </div>
                    <input type="hidden" id="woProductId">
                </div>
                <div class="modal-footer border-0">
                    <button type="button" class="btn btn-secondary rounded-pill" data-bs-dismiss="modal">ยกเลิก</button>
                    <button type="button" class="btn btn-warning rounded-pill fw-bold" onclick="submitWriteoff()">ยืนยันการตัดสต๊อก</button>
                </div>
            </div>
        </div>
    </div>

    <!-- WriteOff History Modal -->
    <div class="modal fade" id="writeoffHistoryModal" tabindex="-1">
        <div class="modal-dialog modal-lg">
            <div class="modal-content glass-card border-0">
                <div class="modal-header border-0">
                    <h5 class="modal-title fw-bold">📜 ประวัติตัดชำรุด / เบิกใช้</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body">
                    <div class="table-responsive">
                        <table class="table table-hover align-middle">
                            <thead class="table-light">
                                <tr>
                                    <th>วันเวลา</th>
                                    <th>สินค้า</th>
                                    <th>จำนวน</th>
                                    <th>สาเหตุ</th>
                                </tr>
                            </thead>
                            <tbody id="woHistoryTable">
                                <!-- Data -->
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>
    </div>
"""

js_code = """
        // WriteOff Functions
        let writeoffModal = null;
        let writeoffHistoryModal = null;

        document.addEventListener('DOMContentLoaded', () => {
            writeoffModal = new bootstrap.Modal(document.getElementById('writeoffModal'));
            writeoffHistoryModal = new bootstrap.Modal(document.getElementById('writeoffHistoryModal'));
        });

        function openWriteoffModal(id, name, stock) {
            document.getElementById('woProductId').value = id;
            document.getElementById('woProductName').innerText = name;
            document.getElementById('woCurrentStock').innerText = stock;
            document.getElementById('woQty').value = 1;
            document.getElementById('woQty').max = stock;
            writeoffModal.show();
        }

        async function submitWriteoff() {
            const id = document.getElementById('woProductId').value;
            const qty = parseInt(document.getElementById('woQty').value);
            const reason = document.getElementById('woReason').value;
            const max = parseInt(document.getElementById('woCurrentStock').innerText);

            if (isNaN(qty) || qty <= 0 || qty > max) {
                alert('กรุณากรอกจำนวนให้ถูกต้องและไม่เกินสต๊อกที่มีอยู่');
                return;
            }

            if(confirm(`คุณแน่ใจหรือไม่ว่าต้องการตัดสต๊อก ${qty} ชิ้น ด้วยสาเหตุ "${reason}"?`)) {
                const res = await fetch('/api/inventory/writeoff', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ product_id: id, qty: qty, reason: reason })
                });

                if(res.ok) {
                    alert('ตัดสต๊อกสำเร็จ!');
                    writeoffModal.hide();
                    fetchProducts();
                } else {
                    alert('เกิดข้อผิดพลาดในการตัดสต๊อก');
                }
            }
        }

        async function showWriteoffHistory() {
            const res = await fetch('/api/inventory/writeoff');
            const data = await res.json();
            const tbody = document.getElementById('woHistoryTable');
            tbody.innerHTML = '';
            
            if(data.length === 0) {
                tbody.innerHTML = '<tr><td colspan="4" class="text-center text-muted">ยังไม่มีประวัติ</td></tr>';
            } else {
                data.forEach(item => {
                    // Use global formatThaiDate if available (added by patch4.py)
                    const d = typeof formatThaiDate === 'function' ? formatThaiDate(item.timestamp) : new Date(item.timestamp).toLocaleString('th-TH');
                    tbody.innerHTML += `
                        <tr>
                            <td><small class="text-muted">${d}</small></td>
                            <td class="fw-bold">${item.name} <br><small class="text-muted">${item.barcode || ''}</small></td>
                            <td class="text-danger fw-bold">-${item.qty}</td>
                            <td><span class="badge bg-secondary">${item.reason}</span></td>
                        </tr>
                    `;
                });
            }
            writeoffHistoryModal.show();
        }
"""

if "id=\"writeoffModal\"" not in content:
    content = content.replace("</body>", modals + "\n</body>")
if "function openWriteoffModal" not in content:
    content = content.replace("</script>\n\n    <!-- Global UI Scripts -->", js_code + "\n</script>\n\n    <!-- Global UI Scripts -->")

with open(r'd:\xerox\templates\inventory.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("Added WriteOff UI")
