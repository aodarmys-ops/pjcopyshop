import glob
import re

html_files = glob.glob(r'd:\xerox\templates\*.html')

for file_path in html_files:
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Replace top/left with top/right in the font-sizer CSS block
    new_content = re.sub(r'(\.font-sizer\s*{[^}]*?top:\s*20px;\s*)left:\s*20px;', r'\1right: 20px;', content)
    # Also catch bottom/right if they were restored from git again just in case
    new_content = re.sub(r'(\.font-sizer\s*{[^}]*?)bottom:\s*20px;\s*right:\s*20px;', r'\1top: 20px;\n            right: 20px;', new_content)

    if new_content != content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)

print("Font sizer moved to top right.")
