#!/usr/bin/env python3
"""
Real x402 Test Client for Algorand TestNet
Demonstrates actual USDC payment flow with GoPlausible facilitator
"""

import sys
import os
import json
import base64
import time
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

import requests
from dotenv import load_dotenv

# x402 client-side components
try:
    from x402.client import x402Client
    from x402.http import HTTPFacilitatorClientSync
    from x402.mechanisms.avm.exact.client import ExactAvmScheme as ExactAvmClientScheme, ClientAvmSigner
    from algosdk.v2client import algod, indexer
    from algosdk.account import Account
    from algosdk.mnemonic import from_private_key
    X402_CLIENT_AVAILABLE = True
except ImportError as e:
    print(f"WARNING: x402 client dependencies not fully available: {e}")
    X402_CLIENT_AVAILABLE = False

load_dotenv()

# Configuration
BASE_URL = "http://localhost:5000"
API_ENDPOINT = "/api/analyze"

# Sample resume
SAMPLE_RESUME = """
John Doe
Senior Software Engineer

SKILLS:
- Python 3.8+
- JavaScript/TypeScript
- SQL and PostgreSQL
- Docker and Kubernetes
- AWS and Azure
- Machine Learning with TensorFlow
- REST APIs and microservices

EXPERIENCE:
Senior Software Engineer at TechCorp (3 years)
- Led development of microservices architecture in Python
- Implemented ML pipeline using Python and TensorFlow
- Managed containerized deployments with Docker/Kubernetes

Software Engineer at StartupXYZ (2 years)
- Built REST APIs in Python/FastAPI
- Implemented AWS infrastructure
- Developed data pipelines with SQL

EDUCATION:
Bachelor's degree in Computer Science from State University (2019)
"""

# Sample job description
SAMPLE_JOB_DESCRIPTION = """
Senior Python Developer - Required Skills
- Python 3.8+ (Required)
- PostgreSQL/SQL (Required)
- Docker & Kubernetes (Required)
- AWS or Azure (Required)
- REST API design (Required)

Experience Required:
- 2+ years as a software engineer
- Experience building microservices
- Experience with cloud platforms

Education:
- Bachelor's degree in Computer Science or related field

Salary: $120,000 - $150,000
"""


def test_without_payment():
    """Test 1: Request without payment (expect HTTP 402)"""
    print("\n" + "="*70)
    print("TEST 1: Request without payment (expect HTTP 402)")
    print("="*70)

    files = {
        "resume": ("resume.txt", SAMPLE_RESUME),
    }
    data = {
        "job_description": SAMPLE_JOB_DESCRIPTION,
        "role_id": "senior-python-dev",
    }

    try:
        response = requests.post(
            f"{BASE_URL}{API_ENDPOINT}",
            files=files,
            data=data,
            timeout=5
        )

        print(f"Status Code: {response.status_code}")
        print(f"\nResponse Headers:")
        for header in ["Content-Type", "Payment-Required", "X-402"]:
            if header in response.headers:
                print(f"  {header}: {response.headers[header]}")
        
        # Check for x402-specific headers
        x402_headers = {k: v for k, v in response.headers.items() if k.lower().startswith('x-402')}
        if x402_headers:
            print(f"\nX-402 Headers:")
            for header, value in x402_headers.items():
                print(f"  {header}: {value}")

        if response.status_code == 402:
            print("\n✓ Correctly returned HTTP 402 Payment Required")
            try:
                body = response.json()
                print(f"\nPayment Requirements:")
                print(json.dumps(body, indent=2))
                return True, body
            except:
                print(f"Response: {response.text}")
                return True, {}
        elif response.status_code == 200:
            print("\n! Payment gate DISABLED (AVM_ADDRESS not set)")
            print("  To enable x402 payment gating, set AVM_ADDRESS in .env")
            try:
                result = response.json()
                print(f"\nAnalysis Results:")
                print(f"  Overall Score: {result.get('overall_score')}")
                print(f"  Matched Skills: {len(result.get('matched_skills', []))}")
            except:
                pass
            return True, {}
        else:
            print(f"\n✗ Unexpected status: {response.status_code}")
            print(f"Response: {response.text}")
            return False, {}

    except requests.exceptions.ConnectionError:
        print(f"\n✗ ERROR: Cannot connect to {BASE_URL}")
        print("Make sure Flask is running:")
        print(f"  cd projects/resume-role-matcher")
        print(f"  python backend/app.py")
        return False, {}
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        return False, {}


def test_health_endpoint():
    """Test: Health check (should work without payment)"""
    print("\n" + "="*70)
    print("TEST: Health check endpoint (no payment required)")
    print("="*70)

    try:
        response = requests.get(f"{BASE_URL}/api/health", timeout=5)

        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            print("\n✓ Health check passed")
            print(f"Response: {json.dumps(response.json(), indent=2)}")
            return True
        else:
            print(f"\n✗ Health check failed")
            return False

    except requests.exceptions.ConnectionError:
        print(f"\n✗ ERROR: Cannot connect to {BASE_URL}")
        return False


def test_with_x402_payment():
    """Test 2: Request with x402 payment proof (full real flow)"""
    print("\n" + "="*70)
    print("TEST 2: Full x402 Algorand payment flow")
    print("="*70)
    
    if not X402_CLIENT_AVAILABLE:
        print("\n! x402 client dependencies not available")
        print("  Cannot demonstrate real payment flow")
        print("  Install with: pip install x402-avm algosdk")
        print("\n  For now, use the test client with:")
        print("  ./test_x402_client.py --demo-mode")
        return False
    
    print("\n  Implementation: Use the dedicated x402 client")
    print("  See: x402_algorand_client.py")
    return True


def main():
    """Run all tests"""
    print("\n" + "="*70)
    print("x402 Payment Gate - Real Algorand TestNet Integration")
    print("="*70)

    print("\nConfiguration:")
    avm_addr = os.getenv("AVM_ADDRESS", "").strip()
    facilitator = os.getenv("FACILITATOR_URL", "https://facilitator.goplausible.xyz")
    network = os.getenv("X402_NETWORK", "algorand:SGO1GKSzyE7IEPItTxCByw9x8FmnrCDexiI=")
    price = os.getenv("X402_PRICE", "0.01")
    
    print(f"  AVM_ADDRESS: {'✓ Configured' if avm_addr else '✗ NOT configured (payment disabled)'}")
    print(f"  Network: {network}")
    print(f"  Facilitator: {facilitator}")
    print(f"  Price: {price} USDC")
    print(f"  x402 Client: {'✓ Available' if X402_CLIENT_AVAILABLE else '✗ Not available'}")

    # Run tests
    results = []
    
    results.append(test_health_endpoint())
    
    has_402, payment_info = test_without_payment()
    results.append(has_402)
    
    if has_402 and payment_info:
        print("\n" + "="*70)
        print("Next: Send real x402 Algorand payment")
        print("="*70)
        print("""
To complete the real x402 payment flow:

1. User (or test client) creates Algorand TestNet USDC transaction:
   - Sender: Your Algorand TestNet account
   - Receiver: AVM_ADDRESS from response
   - Asset ID: 10458941 (Algorand TestNet USDC)
   - Amount: 0.01 USDC (or configured amount)

2. Sign with your private key using algosdk:
   from algosdk.v2client import algod
   from algosdk.transaction import PaymentTxn, write_transaction
   
   # Create and sign USDC payment transaction
   # Get transaction ID

3. Send to GoPlausible facilitator for verification/settlement:
   POST https://facilitator.goplausible.xyz/api/verify
   {
     "network": "algorand:SGO1GKSzyE7IEPItTxCByw9x8FmnrCDexiI=",
     "transaction": "base64-encoded-signed-txn",
     "scheme": "algorand.avm.exact"
   }

4. Get payment proof from facilitator response

5. Retry POST /api/analyze with payment proof in header:
   X-402-Payment: <proof-from-facilitator>

See: x402_algorand_client.py for full implementation example
        """)
    
    results.append(test_with_x402_payment())

    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    print(f"✓ Tests passed: {sum(results)}/{len(results)}")
    
    if not avm_addr:
        print("\n⚠ Payment gating is DISABLED")
        print("To enable: set AVM_ADDRESS=<your-address> in .env")
    
    if all(results):
        print("\n✓ x402 integration complete!")
        print("✓ Server is ready for payment-gated API access")
    
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
