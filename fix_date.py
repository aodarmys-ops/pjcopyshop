import glob

html_files = glob.glob(r'd:\xerox\templates\*.html')

old_formatter = """            const thaiFormatter = function(date, format, locale) {
                const d = String(date.getDate()).padStart(2, '0');
                const m = String(date.getMonth() + 1).padStart(2, '0');
                const y = date.getFullYear() + 543;
                return `${d}/${m}/${y}`;
            };"""

new_formatter = """            const thaiFormatter = function(date, format, locale) {
                const d = String(date.getDate()).padStart(2, '0');
                const m = String(date.getMonth() + 1).padStart(2, '0');
                if (format === "Y-m-d") {
                    return `${date.getFullYear()}-${m}-${d}`;
                }
                const y = date.getFullYear() + 543;
                return `${d}/${m}/${y}`;
            };"""

for file in html_files:
    with open(file, 'r', encoding='utf-8') as f:
        content = f.read()
    if old_formatter in content:
        content = content.replace(old_formatter, new_formatter)
        with open(file, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Patched {file}")
