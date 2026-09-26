import json

files = ['d:\\xerox\\templates\\jobs.html', 'd:\\xerox\\templates\\inventory.html']

for target_file in files:
    content = ""
    with open(r'C:\Users\NB34\.gemini\antigravity-ide\brain\92d42e92-1965-4bf6-b7aa-c5207d5b4272\.system_generated\logs\transcript_full.jsonl', 'r', encoding='utf-8') as f:
        for line in f:
            try:
                j = json.loads(line)
                if 'tool_calls' in j:
                    for tc in j['tool_calls']:
                        if tc.get('name') == 'write_to_file' and tc.get('args', {}).get('TargetFile', '').lower() == target_file.lower():
                            content = tc['args']['CodeContent']
                        elif tc.get('name') in ('multi_replace_file_content', 'replace_file_content') and tc.get('args', {}).get('TargetFile', '').lower() == target_file.lower():
                            chunks = tc['args'].get('ReplacementChunks', [])
                            if tc.get('name') == 'replace_file_content':
                                chunks = [tc['args']]
                            
                            # Extremely basic mock apply (assuming exact match replacements)
                            for chunk in chunks:
                                tc_val = chunk['TargetContent']
                                rc_val = chunk['ReplacementContent']
                                content = content.replace(tc_val, rc_val)
            except Exception as e: pass

    with open(target_file + '.recovered', 'w', encoding='utf-8') as f:
        f.write(content)

print("Recovery complete.")
