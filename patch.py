import os
import glob
import re

html_files = glob.glob(r'd:\xerox\templates\*.html')

head_injection = """
    <!-- Global UI Additions -->
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/flatpickr/dist/flatpickr.min.css">
    <script src="https://cdn.jsdelivr.net/npm/flatpickr"></script>
    <script src="https://npmcdn.com/flatpickr/dist/l10n/th.js"></script>
    <style>
        .font-sizer {
            position: fixed;
            bottom: 20px;
            right: 20px;
            background: #fff;
            padding: 5px;
            border-radius: 20px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.2);
            z-index: 9999;
            display: flex;
            gap: 5px;
        }
        .font-sizer button {
            border: none;
            background: #f8f9fa;
            border-radius: 50%;
            width: 36px;
            height: 36px;
            font-weight: bold;
            cursor: pointer;
            transition: 0.2s;
        }
        .font-sizer button:hover { background: #e9ecef; }
    </style>
"""

body_injection = """
    <!-- Global UI Scripts -->
    <div class="font-sizer">
        <button onclick="changeFontSize(-1)" title="ลดขนาดตัวอักษร">A-</button>
        <button onclick="changeFontSize(0)" title="ขนาดปกติ">A</button>
        <button onclick="changeFontSize(1)" title="เพิ่มขนาดตัวอักษร">A+</button>
    </div>
    <script>
        // Font Size Logic
        const sizes = ['0.85rem', '1rem', '1.15rem', '1.3rem'];
        let currentSizeIdx = parseInt(localStorage.getItem('fontSizeIdx')) || 1;
        
        function applyFontSize() {
            document.documentElement.style.fontSize = sizes[currentSizeIdx];
        }
        
        function changeFontSize(step) {
            if (step === 0) {
                currentSizeIdx = 1;
            } else {
                currentSizeIdx += step;
                if (currentSizeIdx < 0) currentSizeIdx = 0;
                if (currentSizeIdx >= sizes.length) currentSizeIdx = sizes.length - 1;
            }
            localStorage.setItem('fontSizeIdx', currentSizeIdx);
            applyFontSize();
        }
        
        applyFontSize();

        // Flatpickr (Thai Calendar)
        document.addEventListener('DOMContentLoaded', function() {
            flatpickr("input[type=date]", {
                locale: "th",
                dateFormat: "Y-m-d", // keep underlying value Y-m-d for backend
                altInput: true,
                altFormat: "d/m/Y", // display format Day/Month/Year
                onChange: function(selectedDates, dateStr, instance) {
                    // Adjust year to Buddhist Era (BE) in the alt input
                    if (selectedDates.length > 0 && instance.altInput) {
                        const date = selectedDates[0];
                        const day = String(date.getDate()).padStart(2, '0');
                        const month = String(date.getMonth() + 1).padStart(2, '0');
                        const beYear = date.getFullYear() + 543;
                        instance.altInput.value = `${day}/${month}/${beYear}`;
                    }
                },
                onReady: function(selectedDates, dateStr, instance) {
                    if (selectedDates.length > 0 && instance.altInput) {
                        const date = selectedDates[0];
                        const day = String(date.getDate()).padStart(2, '0');
                        const month = String(date.getMonth() + 1).padStart(2, '0');
                        const beYear = date.getFullYear() + 543;
                        instance.altInput.value = `${day}/${month}/${beYear}`;
                    }
                }
            });
        });
        
        // Currency Formatter
        function formatMoney(num) {
            return Number(num).toLocaleString('th-TH', {minimumFractionDigits: 2, maximumFractionDigits: 2});
        }
    </script>
"""

for file_path in html_files:
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Inject Head (if not already there)
    if '<script src="https://cdn.jsdelivr.net/npm/flatpickr"></script>' not in content:
        content = content.replace('</head>', head_injection + '\n</head>')

    # 2. Inject Body (if not already there)
    if 'class="font-sizer"' not in content:
        content = content.replace('</body>', body_injection + '\n</body>')

    # 3. Replace ฿ symbol and .toFixed(2) in template strings
    # We want to change things like ฿${x.toFixed(2)} to ${formatMoney(x)}
    
    # Simple static text replacements
    content = content.replace('฿0.00', '0.00')
    content = content.replace('฿', '')
    
    # Replace .toFixed(2) with .toLocaleString for money specifically in JS interpolations.
    # Since we removed ฿, let's just do a blanket regex to format numbers to 2 decimal places with commas.
    # Actually, a regex that finds ${ ... .toFixed(2)} and changes to ${formatMoney(...)}
    content = re.sub(r'\$\{([^}]+?)\.toFixed\(2\)\}', r'${formatMoney(\1)}', content)
    
    # And there are some places like `total.toFixed(2)` that are used to set input values or HTML directly outside of template literals.
    # E.g. `document.getElementById('totalAmount').innerText = '฿' + total.toFixed(2);`
    content = re.sub(r"'฿' \+ ([^;]+)\.toFixed\(2\)", r"formatMoney(\1)", content)
    content = re.sub(r'"฿" \+ ([^;]+)\.toFixed\(2\)', r"formatMoney(\1)", content)
    
    # Replace native toLocaleString('th-TH') where it was just formatting date maybe?
    # Leave toLocaleString alone, just ensure no ฿ is prepended.
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

print("Patch complete.")
