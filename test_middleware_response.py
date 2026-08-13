#!/usr/bin/env python3
"""Test x402 payment middleware - verify 402 response"""

import requests

print("\n" + "="*70)
print("TESTING x402 PAYMENT MIDDLEWARE")
print("="*70)

# Test 1: POST /api/analyze without payment (should return 402)
print("\n1. Testing POST /api/analyze WITHOUT payment...")
print("   Expected: HTTP 402 Payment Required")

# Use form data to match Flask route expectations
files = {
    'resume': ('test_resume.txt', b'John Doe\nPython Developer\n10 years experience'),
}
data = {
    'job_description': 'Senior Python Developer needed',
    'role_id': 'python-dev',
}

try:
    response = requests.post(
        'http://localhost:5000/api/analyze',
        files=files,
        data=data,
        headers={},
        allow_redirects=False,
    )
    
    print(f"\n   Status Code: {response.status_code}")
    print(f"   Response Headers:")
    for key, value in response.headers.items():
        if key.lower().startswith('x-') or key.lower() == 'payment':
            print(f"     {key}: {value[:100]}")
    
    print(f"\n   Response Body:")
    print(f"   {response.text[:200]}")
    
    if response.status_code == 402:
        print(f"\n✓ MIDDLEWARE WORKING - Returned HTTP 402")
        print("  Payment gate intercepted the request!")
    elif response.status_code == 400:
        print(f"\n✗ MIDDLEWARE NOT WORKING")
        print(f"  Returned HTTP 400 (route handler error)")
        print(f"  Middleware should have intercepted before route handler")
    else:
        print(f"\n? UNEXPECTED STATUS CODE: {response.status_code}")
        
except Exception as e:
    print(f"✗ ERROR: {e}")

print("\n" + "="*70 + "\n")
