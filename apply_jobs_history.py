import json
import os

with open(r'd:\xerox\jobs_history.json', 'r', encoding='utf-8') as f:
    history = json.load(f)

# Wait, `jobs.html` from Git doesn't have the font-sizer and flatpickr patches applied natively, it has them appended via patch4 and patch5.
# If we re-apply these chunks, they assume the state of the file as it was modified.
# The safest way is to check out `jobs.html` from Git, apply ALL chunks sequentially, then run patch4, patch5, move_font_sizer.

# 1. Restore from Git
os.system("git restore d:/xerox/templates/jobs.html")

# 2. Read restored file
with open(r'd:\xerox\templates\jobs.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 3. Apply chunks
for tc in history:
    if tc['name'] == 'multi_replace_file_content':
        chunks = tc['args']['ReplacementChunks']
        for chunk in chunks:
            target = chunk['TargetContent']
            replacement = chunk['ReplacementContent']
            if target in content:
                content = content.replace(target, replacement)
            else:
                print("Could not find chunk:", target[:50])

# 4. Save
with open(r'd:\xerox\templates\jobs.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("Jobs history applied.")
