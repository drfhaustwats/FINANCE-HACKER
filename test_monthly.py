#!/usr/bin/env python3
import requests
import json

# Get backend URL
def get_backend_url():
    with open('/app/frontend/.env', 'r') as f:
        for line in f:
            if line.startswith('REACT_APP_BACKEND_URL='):
                return line.strip().split('=')[1].strip('"\'')
    return None

BACKEND_URL = get_backend_url()
API_URL = f"{BACKEND_URL}/api"

# Test monthly report endpoint
print("Testing monthly report endpoint...")
response = requests.get(f"{API_URL}/analytics/monthly-report?year=2024")
if response.status_code == 200:
    data = response.json()
    print(f"SUCCESS: Got {len(data)} months of data")
    print(json.dumps(data, indent=2))
else:
    print(f"FAILED: Status {response.status_code}")
    print(response.text)