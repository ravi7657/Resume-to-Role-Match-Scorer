#!/usr/bin/env python3
"""Debug x402 route matching"""

import os
from dotenv import load_dotenv

load_dotenv()

from flask import Flask
from x402.http import FacilitatorConfig, HTTPFacilitatorClientSync, PaymentOption
from x402.http.middleware.flask import payment_middleware
from x402.http.types import RouteConfig
from x402.mechanisms.avm.exact.server import ExactAvmScheme
from x402.mechanisms.avm import ALGORAND_TESTNET_CAIP2, USDC_TESTNET_ASA_ID
from x402.server import x402ResourceServerSync

print("\n" + "="*70)
print("DEBUGGING x402 ROUTE MATCHING")
print("="*70)

app = Flask(__name__)

avm_address = os.getenv('AVM_ADDRESS')
facilitator_url = os.getenv('FACILITATOR_URL')
x402_network = os.getenv('X402_NETWORK', ALGORAND_TESTNET_CAIP2)
x402_price = os.getenv('X402_PRICE', '0.01')

facilitator = HTTPFacilitatorClientSync(FacilitatorConfig(url=facilitator_url))
server = x402ResourceServerSync(facilitator)
server.register(x402_network, ExactAvmScheme())

# Try different route patterns
patterns = [
    "POST /api/analyze",
    "/api/analyze",
    "POST /api/analyze/*",
    "/api/analyze*",
]

for pattern in patterns:
    print(f"\nTesting route pattern: '{pattern}'")
    
    app_test = Flask(__name__)
    
    routes = {
        pattern: RouteConfig(
            accepts=[PaymentOption(
                scheme='exact',
                pay_to=avm_address,
                price=f'${x402_price}',
                network=x402_network,
                extra={'asset': USDC_TESTNET_ASA_ID},
            )],
            description='Test',
            mime_type='application/json',
        )
    }
    
    try:
        from x402.http.x402_http_server import x402HTTPResourceServerSync
        
        http_server = x402HTTPResourceServerSync(server, routes)
        
        # Check if the route is recognized
        print(f"  Routes registered in http_server:")
        print(f"  {list(http_server._routes.keys())}")
        
        # Test requires_payment with different paths
        from x402.http.types import HTTPRequestContext
        
        class MockRequest:
            def __init__(self, path, method):
                self.path = path
                self.method = method
        
        class MockAdapter:
            def __init__(self, request):
                self.request = request
            
            def get_header(self, name):
                return None
        
        for test_path, test_method in [
            ("/api/analyze", "POST"),
            ("/api/analyze", "GET"),
            ("/api/health", "POST"),
        ]:
            mock_req = MockRequest(test_path, test_method)
            mock_adapter = MockAdapter(mock_req)
            
            context = HTTPRequestContext(
                adapter=mock_adapter,
                path=test_path,
                method=test_method,
                payment_header=None,
            )
            
            requires = http_server.requires_payment(context)
            print(f"    {test_method} {test_path}: requires_payment={requires}")
        
    except Exception as e:
        print(f"  ERROR: {e}")
        import traceback
        traceback.print_exc()

print("\n" + "="*70 + "\n")
