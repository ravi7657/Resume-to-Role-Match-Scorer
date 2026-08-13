#!/usr/bin/env python3
"""Test app directly without running server"""

import os
import sys
from pathlib import Path

# Set up paths
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))
os.chdir(str(ROOT / "backend"))

# Import the app
print("Importing app from backend.app...")
from backend.app import app

print(f"\nApp created: {app}")
print(f"app.wsgi_app: {app.wsgi_app}")
print(f"app.wsgi_app type: {type(app.wsgi_app).__name__}")

# Test with Werkzeug test client
print("\n" + "="*70)
print("TESTING WITH WERKZEUG TEST CLIENT")
print("="*70)

from werkzeug.test import Client
from werkzeug.wrappers import Response

client = Client(app, Response)

print("\nMaking POST /api/analyze request...")
try:
    response = client.post(
        '/api/analyze',
        data={
            'resume': (b'John Doe\nPython Developer', 'resume.txt'),
            'job_description': 'Senior Python Developer',
            'role_id': 'python-dev',
        }
    )
    
    print(f"\nResponse:")
    print(f"  Status: {response.status}")
    print(f"  Status Code: {response.status_code}")
    print(f"  Body (first 100 chars): {response.get_data(as_text=True)[:100]}")
    
    if response.status_code == 402:
        print("\n✓ MIDDLEWARE WORKING - Returns 402")
    elif response.status_code == 200:
        print("\n✗ MIDDLEWARE NOT WORKING - Returns 200 (route handler executed)")
    else:
        print(f"\n? UNEXPECTED STATUS: {response.status_code}")
        
except Exception as e:
    print(f"\nERROR: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*70 + "\n")
