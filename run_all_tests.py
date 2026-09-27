import json
import re
import csv
import requests
import time
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

    print(f"Loaded {len(events)} events. Starting tests...")

    passed = 0
    failed = 0
    results = []

    for idx, event in enumerate(events):
        event_id = event.get('event_id', f'unknown-{idx}')
        action = event.get('action', '')
        payload = event.get('payload', {})
        expected_status = event.get('expected_http_status', 200)
        dimension = event.get('dimension', '')
        entity = event.get('entity', '')

        match = re.search(r'\b(GET|POST|PUT|DELETE|PATCH)\b\s+(/[^\s]+)', action)
        if match:
            method = match.group(1)
            endpoint = match.group(2)
        else:
            print(f"[{event_id}] Invalid action format: {action}")
            results.append({
                "event_id": event_id, "dimension": dimension, "entity": entity, 
                "action": action, "expected_status": expected_status, 
                "actual_status": "ERROR", "result": "FAIL", "error": "Invalid action format"
            })
            failed += 1
            continue
            
        url = urljoin(BASE_URL, endpoint)
        
        try:
            if method.upper() == 'GET':
                resp = requests.get(url, params=payload, timeout=5)
            elif method.upper() == 'POST':
                resp = requests.post(url, json=payload, timeout=5)
            elif method.upper() == 'PUT':
                resp = requests.put(url, json=payload, timeout=5)
            elif method.upper() == 'DELETE':
                resp = requests.delete(url, json=payload, timeout=5)
            else:
                resp = requests.request(method, url, json=payload, timeout=5)
                
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
    print(f"Total: {len(events)} | Passed: {passed} | Failed: {failed}")
    
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
