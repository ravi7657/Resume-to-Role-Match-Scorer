#!/usr/bin/env python3
"""Send test request and print response details"""

import requests
import json

print("\n" + "="*70)
print("SENDING TEST REQUEST TO LIVE SERVER")
print("="*70)

files = {
    'resume': ('test_resume.txt', b'John Doe\nPython Developer\n10 years'),
}
data = {
    'job_description': 'Senior Python Developer',
    'role_id': 'python-dev',
}

print("\nRequest details:")
print(f"  URL: POST http://localhost:5000/api/analyze")
print(f"  Files: {list(files.keys())}")
print(f"  Form Data: {list(data.keys())}")

try:
    response = requests.post(
        'http://localhost:5000/api/analyze',
        files=files,
        data=data,
        timeout=10,
    )
    
    print(f"\nResponse details:")
    print(f"  Status Code: {response.status_code}")
    print(f"  Status Text: {response.reason}")
    print(f"\n  Headers:")
    for key in sorted(response.headers.keys()):
        if key.lower() in ['content-type', 'x-402-payment', 'payment', 'www-authenticate']:
            print(f"    {key}: {response.headers[key][:100]}")
    
    print(f"\n  Body (first 300 chars):")
    print(f"    {response.text[:300]}")
    
    # Check if it's JSON
    try:
        resp_json = response.json()
        if 'error' in resp_json:
            print(f"\n  ERROR: {resp_json['error']}")
        elif 'analysis' in resp_json:
            print(f"\n  SUCCESS: Analysis returned (Gemini analysis executed)")
    except:
        pass
        
except Exception as e:
    print(f"ERROR: {e}")

print("\n" + "="*70 + "\n")
