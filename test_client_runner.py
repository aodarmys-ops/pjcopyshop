import json
import csv
import re
import app

def run_tests():
    print("Running tests against REAL database (xerox.db)...")

    # --- Session Management (จำสถานะการ Login) ---
    client = app.app.test_client()

    INPUT_FILE = "test_data_events.json"
    REPORT_FILE = "test_results_report.csv"
    
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        events = json.load(f)

    passed = 0
    failed = 0
    skipped = 0
    results = []

    print(f"Starting {len(events)} tests using Flask Test Client...")

    for idx, event in enumerate(events):
        event_id = event.get('event_id', f'unknown-{idx}')
        action = event.get('action', '')
        payload = event.get('payload', {})
        expected_status = event.get('expected_http_status', 200)
        dimension = event.get('dimension', '')
        entity = event.get('entity', '')

        # --- Action Mapper & Filter (ข้ามเคสที่เป็นคำอธิบาย Workflow) ---
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

        try:
            if method == 'GET':
                resp = client.get(endpoint, query_string=payload)
            elif method == 'POST':
                resp = client.post(endpoint, json=payload)
            elif method == 'PUT':
                resp = client.put(endpoint, json=payload)
            elif method == 'DELETE':
                resp = client.delete(endpoint, json=payload)
            else:
                resp = client.open(endpoint, method=method, json=payload)
            
            actual_status = resp.status_code
            error_msg = ""
        except Exception as e:
            actual_status = 500
            error_msg = str(e)

        is_pass = (actual_status == expected_status)
        if is_pass:
            passed += 1
            result_str = "PASS"
        else:
            failed += 1
            result_str = "FAIL"

        results.append({
            "event_id": event_id, "dimension": dimension, "entity": entity,
            "action": action, "expected_status": expected_status,
            "actual_status": actual_status, "result": result_str, "error": error_msg
        })

    print(f"\nTest Execution Completed!")
    print(f"Total: {len(events)} | Passed: {passed} | Failed: {failed} | Skipped: {skipped}")
    
    with open(REPORT_FILE, 'w', encoding='utf-8', newline='') as csvfile:
        fieldnames = ["event_id", "dimension", "entity", "action", "expected_status", "actual_status", "result", "error"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for res in results:
            writer.writerow(res)

    print(f"Report saved to {REPORT_FILE}")

if __name__ == '__main__':
    run_tests()
