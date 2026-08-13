#!/usr/bin/env python3
"""Inspect compiled routes"""

import os
import json
from dotenv import load_dotenv

load_dotenv()

from x402.http import FacilitatorConfig, HTTPFacilitatorClientSync, PaymentOption
from x402.http.x402_http_server import x402HTTPResourceServerSync
from x402.http.types import RouteConfig
from x402.mechanisms.avm.exact.server import ExactAvmScheme
from x402.mechanisms.avm import ALGORAND_TESTNET_CAIP2, USDC_TESTNET_ASA_ID
from x402.server import x402ResourceServerSync

print("\n" + "="*70)
print("INSPECTING COMPILED ROUTES")
print("="*70)

avm_address = os.getenv('AVM_ADDRESS')
facilitator_url = os.getenv('FACILITATOR_URL')
x402_network = os.getenv('X402_NETWORK', ALGORAND_TESTNET_CAIP2)
x402_price = os.getenv('X402_PRICE', '0.01')

facilitator = HTTPFacilitatorClientSync(FacilitatorConfig(url=facilitator_url))
server = x402ResourceServerSync(facilitator)
server.register(x402_network, ExactAvmScheme())

routes = {
    "POST /api/analyze": RouteConfig(
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

http_server = x402HTTPResourceServerSync(server, routes)

print(f"\nRoutes config: {http_server._routes_config}")

print(f"\nNumber of compiled routes: {len(http_server._compiled_routes)}")

for i, route in enumerate(http_server._compiled_routes):
    print(f"\nRoute {i}:")
    print(f"  Type: {type(route)}")
    print(f"  Dir: {[attr for attr in dir(route) if not attr.startswith('_')][:10]}")
    
    # Try to access route details
    if hasattr(route, 'pattern'):
        print(f"  pattern: {route.pattern}")
    if hasattr(route, 'method'):
        print(f"  method: {route.method}")
    if hasattr(route, 'route_pattern'):
        print(f"  route_pattern: {route.route_pattern}")
    if hasattr(route, 'path_pattern'):
        print(f"  path_pattern: {route.path_pattern}")

# Now test requires_payment
print("\n" + "-"*70)
print("TESTING REQUIRES_PAYMENT")
print("-"*70)

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
    ("POST /api/analyze", "POST"),
]:
    try:
        mock_adapter = MockAdapter(None)
        
        context = HTTPRequestContext(
            adapter=mock_adapter,
            path=test_path if not test_path.startswith("POST") else test_path.split(" ")[1],
            method=test_method if not test_path.startswith("POST") else "POST",
            payment_header=None,
        )
        
        requires = http_server.requires_payment(context)
        print(f"{test_method:6} {test_path:20} → requires_payment: {requires}")
    except Exception as e:
        print(f"{test_method:6} {test_path:20} → ERROR: {e}")

print("\n" + "="*70 + "\n")
