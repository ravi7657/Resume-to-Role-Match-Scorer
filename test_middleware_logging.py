#!/usr/bin/env python3
"""Test middleware with logging"""

import os
import sys
from dotenv import load_dotenv

load_dotenv()

from flask import Flask
from x402.http import FacilitatorConfig, HTTPFacilitatorClientSync, PaymentOption
from x402.http.middleware.flask import payment_middleware, PaymentMiddleware
from x402.http.types import RouteConfig
from x402.mechanisms.avm.exact.server import ExactAvmScheme
from x402.mechanisms.avm import ALGORAND_TESTNET_CAIP2, USDC_TESTNET_ASA_ID
from x402.server import x402ResourceServerSync

print("\n" + "="*70)
print("TESTING MIDDLEWARE WITH DEBUG LOGGING")
print("="*70)

# Monkey-patch PaymentMiddleware to add logging
original_wsgi_middleware = PaymentMiddleware._wsgi_middleware

def logged_wsgi_middleware(self, environ, start_response):
    print(f"\n[MIDDLEWARE] Called!")
    print(f"[MIDDLEWARE] PATH: {environ.get('PATH_INFO')}")
    print(f"[MIDDLEWARE] METHOD: {environ.get('REQUEST_METHOD')}")
    
    try:
        from flask import request
        with self._app.request_context(environ):
            print(f"[MIDDLEWARE] Flask request.path: {request.path}")
            print(f"[MIDDLEWARE] Flask request.method: {request.method}")
            
            # Check if requires_payment
            from x402.http.types import HTTPRequestContext
            from x402.http.middleware.flask import FlaskAdapter
            
            adapter = FlaskAdapter(request)
            context = HTTPRequestContext(
                adapter=adapter,
                path=request.path,
                method=request.method,
                payment_header=(
                    adapter.get_header("payment-signature") or adapter.get_header("x-payment")
                ),
            )
            
            requires = self._http_server.requires_payment(context)
            print(f"[MIDDLEWARE] requires_payment: {requires}")
            
    except Exception as e:
        print(f"[MIDDLEWARE] Error checking payment: {e}")
        import traceback
        traceback.print_exc()
    
    # Call original
    return original_wsgi_middleware(self, environ, start_response)

PaymentMiddleware._wsgi_middleware = logged_wsgi_middleware

# Now create the app
app = Flask(__name__)

@app.route("/api/analyze", methods=["POST"])
def analyze():
    print("[ROUTE] /api/analyze handler called")
    return {"result": "ok"}, 200

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

print("\nAttaching middleware...")
payment_middleware(app, routes=routes, server=server)

print("Making test request...")

# Make a test request
from werkzeug.test import Client
from werkzeug.wrappers import Response

client = Client(app, Response)

response = client.post("/api/analyze", data={
    'job_description': 'Python Developer',
})

print(f"\nTest request response:")
print(f"  Status: {response.status_code}")
print(f"  Body: {response.get_data(as_text=True)[:200]}")

print("\n" + "="*70 + "\n")
