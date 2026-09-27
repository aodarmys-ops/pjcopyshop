import json
out = []
with open(r'C:\Users\NB34\.gemini\antigravity-ide\brain\92d42e92-1965-4bf6-b7aa-c5207d5b4272\.system_generated\logs\transcript_full.jsonl', 'r', encoding='utf-8') as f:
    for line in f:
        try:
            j = json.loads(line)
            if 'tool_calls' in j:
                for tc in j['tool_calls']:
                    if tc.get('name') == 'write_to_file' and 'jobs.html' in str(tc):
                        out.append(tc)
                    elif tc.get('name') == 'multi_replace_file_content' and 'jobs.html' in str(tc):
                        out.append(tc)
        except: pass

with open(r'd:\xerox\jobs_history.json', 'w', encoding='utf-8') as f:
    json.dump(out, f, indent=2)
