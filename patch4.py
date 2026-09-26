import glob
import re

html_files = glob.glob(r'd:\xerox\templates\*.html')

new_body_script = """
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

        // Custom Thai Date Formatter for text (DD/MM/YYYY)
        function formatThaiDate(dateString) {
            if (!dateString) return '';
            const d = new Date(dateString);
            if (isNaN(d)) return dateString;
            const day = String(d.getDate()).padStart(2, '0');
            const month = String(d.getMonth() + 1).padStart(2, '0');
            const year = d.getFullYear() + 543;
            const hours = String(d.getHours()).padStart(2, '0');
            const minutes = String(d.getMinutes()).padStart(2, '0');
            return `${day}/${month}/${year} ${hours}:${minutes}`;
        }

        // Flatpickr (Thai Calendar + Buddhist Era Header)
        document.addEventListener('DOMContentLoaded', function() {
            const thaiFormatter = function(date, format, locale) {
                const d = String(date.getDate()).padStart(2, '0');
                const m = String(date.getMonth() + 1).padStart(2, '0');
                const y = date.getFullYear() + 543;
                return `${d}/${m}/${y}`;
            };
            
            function updateYearToBE(instance) {
                if (instance.yearElements && instance.yearElements.length > 0) {
                    const yearInput = instance.yearElements[0];
                    const currentVal = parseInt(yearInput.value);
                    if (currentVal < 2500) { // If it's CE, change to BE
                        yearInput.value = currentVal + 543;
                    }
                }
                if (instance.currentYearElement) {
                    const currentVal = parseInt(instance.currentYearElement.value);
                    if (currentVal < 2500) {
                        instance.currentYearElement.value = currentVal + 543;
                    }
                }
            }

            flatpickr("input[type=date]", {
                locale: "th",
                dateFormat: "Y-m-d", 
                altInput: true,
                altFormat: "d/m/Y", 
                formatDate: thaiFormatter,
                onReady: function(selectedDates, dateStr, instance) { updateYearToBE(instance); },
                onOpen: function(selectedDates, dateStr, instance) { updateYearToBE(instance); },
                onYearChange: function(selectedDates, dateStr, instance) { updateYearToBE(instance); },
                onMonthChange: function(selectedDates, dateStr, instance) { updateYearToBE(instance); },
                onPreCalendarPosition: function(selectedDates, dateStr, instance) { updateYearToBE(instance); },
                onChange: function(selectedDates, dateStr, instance) {
                    updateYearToBE(instance);
                }
            });
        });
        
        // Currency Formatter
        function formatMoney(num) {
            return Number(num).toLocaleString('th-TH', {minimumFractionDigits: 2, maximumFractionDigits: 2});
        }
    </script>
"""

head_injection = """
    <!-- Global UI Additions -->
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/flatpickr/dist/flatpickr.min.css">
    <script src="https://cdn.jsdelivr.net/npm/flatpickr"></script>
    <script src="https://npmcdn.com/flatpickr/dist/l10n/th.js"></script>
    <style>
        .font-sizer {
            position: fixed;
            top: 20px;
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

for file_path in html_files:
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Inject Head
    if '<script src="https://cdn.jsdelivr.net/npm/flatpickr"></script>' not in content:
        content = content.replace('</head>', head_injection + '\n</head>')

    # 2. Inject Body
    if 'class="font-sizer"' not in content:
        content = content.replace('</body>', new_body_script + '\n</body>')

    # 3. Text formatting 
    content = content.replace('฿0.00', '0.00')
    content = content.replace('฿', '')
    
    # Currency
    content = re.sub(r'\$\{([^}]+?)\.toFixed\(2\)\}', r'${formatMoney(\1)}', content)
    content = re.sub(r"'฿' \+ ([^;]+)\.toFixed\(2\)", r"formatMoney(\1)", content)
    content = re.sub(r'"฿" \+ ([^;]+)\.toFixed\(2\)', r"formatMoney(\1)", content)
    
    # Date formatting (only matching the pattern I found in POS/Reports)
    content = re.sub(r"new Date\(([^)]+)\)\.toLocaleString\('th-TH'\)", r"formatThaiDate(\1)", content)

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

print("Patch 4 complete.")
