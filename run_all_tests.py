import json
import csv
import re
import requests
from urllib.parse import urljoin

BASE_URL = "http://127.0.0.1:5000"
INPUT_FILE = "test_data_events.json"
REPORT_FILE = "test_results_report.csv"

def run_tests():
    print(f"Loading test cases from {INPUT_FILE}...")
    try:
        with open(INPUT_FILE, 'r', encoding='utf-8') as f:
            events = json.load(f)
    except Exception as e:
        print(f"Error loading {INPUT_FILE}: {e}")
        return

    print(f"Loaded {len(events)} events. Starting tests against REAL APP at {BASE_URL}...")

    # ใช้ requests.Session() เพื่อให้ระบบจำ Cookie/Login State ข้ามเคสได้
    session = requests.Session()

    # --- Login ก่อนเริ่มเทสเพื่อให้เข้าถึง API ได้ ---
    print("Logging in as Admin...")
    login_url = urljoin(BASE_URL, '/login')
    session.post(login_url, data={'pin': '1234'}, allow_redirects=False)
    print("Login sequence completed. Session authenticated.")

    passed = 0
    failed = 0
    skipped = 0
    results = []

    for idx, event in enumerate(events):
        event_id = event.get('event_id', f'unknown-{idx}')
        action = event.get('action', '')
        payload = event.get('payload', {})
        expected_status = event.get('expected_http_status', 200)
        dimension = event.get('dimension', '')
        entity = event.get('entity', '')

        # ตรวจสอบว่า Action เป็น HTTP หรือเป็นแค่คำอธิบาย
        match = re.search(r'\b(GET|POST|PUT|DELETE|PATCH)\b\s+(/[^\s]+)', action)
        if not match:
            results.append({
                "event_id": event_id, "dimension": dimension, "entity": entity, 
                "action": action, "expected_status": expected_status, 
                "actual_status": "SKIPPED", "result": "SKIP", "error": "Manual Workflow Test (No API endpoint)"
            })
            skipped += 1
            continue
            
        method = match.group(1)
        endpoint = match.group(2)
        url = urljoin(BASE_URL, endpoint)
        
        try:
            if method.upper() == 'GET':
                resp = session.get(url, params=payload, timeout=5, allow_redirects=False)
            elif method.upper() == 'POST':
                resp = session.post(url, json=payload, timeout=5, allow_redirects=False)
            elif method.upper() == 'PUT':
                resp = session.put(url, json=payload, timeout=5, allow_redirects=False)
            elif method.upper() == 'DELETE':
                resp = session.delete(url, json=payload, timeout=5, allow_redirects=False)
            else:
                resp = session.request(method, url, json=payload, timeout=5, allow_redirects=False)
                
            actual_status = resp.status_code
            error_msg = ""
        except requests.exceptions.RequestException as e:
            actual_status = 0
            error_msg = str(e)

        is_pass = (actual_status == expected_status)
        if is_pass:
            passed += 1
            result_str = "PASS"
        else:
            failed += 1
            result_str = "FAIL"

        results.append({
            "event_id": event_id,
            "dimension": dimension,
            "entity": entity,
            "action": action,
            "expected_status": expected_status,
            "actual_status": actual_status,
            "result": result_str,
            "error": error_msg
        })
        
        if (idx + 1) % 100 == 0:
            print(f"Processed {idx + 1}/{len(events)} tests...")
            
    print(f"\nTest Execution Completed!")
    print(f"Total: {len(events)} | Passed: {passed} | Failed: {failed} | Skipped: {skipped}")
    
    print(f"Writing report to {REPORT_FILE}...")
    with open(REPORT_FILE, 'w', encoding='utf-8', newline='') as csvfile:
        fieldnames = ["event_id", "dimension", "entity", "action", "expected_status", "actual_status", "result", "error"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for res in results:
            writer.writerow(res)
            
    print("Done!")

if __name__ == '__main__':
    run_tests()
