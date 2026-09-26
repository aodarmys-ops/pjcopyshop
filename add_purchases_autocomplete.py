import re

with open(r'd:\xerox\templates\purchases.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace HTML
old_html = """                    <div class="mb-3">
                        <label class="form-label text-muted small fw-bold">สแกนบาร์โค้ด หรือ พิมพ์ชื่อสินค้า</label>
                        <form id="searchForm" class="d-flex">
                            <input type="text" class="form-control" id="barcodeInput" placeholder="สแกน หรือ ค้นหา..." autocomplete="off">
                            <button type="submit" class="btn btn-primary ms-2 rounded-pill px-4">ค้นหา</button>
                        </form>
                    </div>"""

new_html = """                    <div class="mb-3 position-relative">
                        <label class="form-label text-muted small fw-bold">สแกนบาร์โค้ด หรือ พิมพ์ชื่อสินค้า</label>
                        <form id="searchForm" class="d-flex">
                            <input type="text" class="form-control" id="barcodeInput" placeholder="สแกน หรือ ค้นหา..." autocomplete="off">
                            <button type="submit" class="btn btn-primary ms-2 rounded-pill px-4 d-none">ค้นหา</button>
                        </form>
                        <ul id="purchaseAutocomplete" class="list-group position-absolute w-100 shadow mt-1" style="z-index: 1000; display: none; max-height: 250px; overflow-y: auto; cursor: pointer;"></ul>
                    </div>"""

content = content.replace(old_html, new_html)

# Replace JS
old_js = """        document.getElementById('searchForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const q = document.getElementById('barcodeInput').value.trim();
            if (!q) return;

            const res = await fetch(`/api/products/search?q=${q}`);
            const products = await res.json();
            
            if (products.length === 1) {
                addToCart(products[0]);
            } else if (products.length > 1) {
                // If multiple matches (like typing "Paper"), just add the first one for simplicity, 
                // in a real app you'd show a modal to select.
                addToCart(products[0]); 
            } else {
                alert("ไม่พบสินค้า!");
            }
            
            document.getElementById('barcodeInput').value = '';
            document.getElementById('barcodeInput').focus();
        });"""

new_js = """        const bInput = document.getElementById('barcodeInput');
        const acList = document.getElementById('purchaseAutocomplete');

        bInput.addEventListener('input', async (e) => {
            const q = e.target.value.trim();
            if(!q) {
                acList.style.display = 'none';
                return;
            }
            const res = await fetch(`/api/products/search?q=${encodeURIComponent(q)}`);
            const products = await res.json();
            
            acList.innerHTML = '';
            if(products.length > 0) {
                products.forEach(p => {
                    let li = document.createElement('li');
                    li.className = 'list-group-item list-group-item-action cursor-pointer';
                    li.innerHTML = `<strong>${p.name}</strong> <small class="text-muted ms-1">[${p.barcode || 'ไม่มีบาร์โค้ด'}]</small>`;
                    li.onclick = () => {
                        addToCart(p);
                        bInput.value = '';
                        acList.style.display = 'none';
                        bInput.focus();
                    };
                    acList.appendChild(li);
                });
                acList.style.display = 'block';
            } else {
                acList.style.display = 'none';
            }
        });

        document.addEventListener('click', (e) => {
            if(!bInput.contains(e.target) && !acList.contains(e.target)) {
                acList.style.display = 'none';
            }
        });

        document.getElementById('searchForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const q = bInput.value.trim();
            if (!q) return;

            const res = await fetch(`/api/products/search?q=${encodeURIComponent(q)}`);
            const products = await res.json();
            
            if (products.length === 1) {
                addToCart(products[0]);
                bInput.value = '';
                acList.style.display = 'none';
                bInput.focus();
            } else if (products.length > 1) {
                bInput.dispatchEvent(new Event('input'));
            } else {
                alert("ไม่พบสินค้า!");
            }
        });"""

content = content.replace(old_js, new_js)

with open(r'd:\xerox\templates\purchases.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("Added autocomplete to purchases")
