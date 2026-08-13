#!/usr/bin/env python3
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
print("TESTING PAYMENT MIDDLEWARE ATTACHMENT")
print("="*70)

app = Flask(__name__)

print("\n1. Before payment_middleware:")
print(f"   Original app.wsgi_app: {app.wsgi_app}")
print(f"   app.wsgi_app type: {type(app.wsgi_app).__name__}")

avm_address = os.getenv('AVM_ADDRESS')
facilitator_url = os.getenv('FACILITATOR_URL')
x402_network = os.getenv('X402_NETWORK', ALGORAND_TESTNET_CAIP2)
x402_price = os.getenv('X402_PRICE', '0.01')

facilitator = HTTPFacilitatorClientSync(FacilitatorConfig(url=facilitator_url))
server = x402ResourceServerSync(facilitator)
server.register(x402_network, ExactAvmScheme())

routes = {
    'POST /api/analyze': RouteConfig(
        accepts=[PaymentOption(
            scheme='exact',
            pay_to=avm_address,
            price=f'${x402_price}',
            network=x402_network,
            extra={'asset': USDC_TESTNET_ASA_ID},
        )],
        description='Resume Role Matcher AI analysis',
        mime_type='application/json',
    )
}

print("\n2. Calling payment_middleware(app, routes, server)...")
pm = payment_middleware(app, routes=routes, server=server)

print(f"\n3. After payment_middleware:")
print(f"   PaymentMiddleware returned: {pm}")
print(f"   app.wsgi_app: {app.wsgi_app}")
print(f"   app.wsgi_app type: {type(app.wsgi_app).__name__}")

# Check if they're different
original_type = "WSGIApplication"
new_type = type(app.wsgi_app).__name__

if "PaymentMiddleware" in str(app.wsgi_app) or new_type.find("method") >= 0:
    print(f"\n✓ MIDDLEWARE WAS ATTACHED")
    print(f"  app.wsgi_app was replaced with PaymentMiddleware._wsgi_middleware")
else:
    print(f"\n✗ MIDDLEWARE WAS NOT ATTACHED")
    print(f"  app.wsgi_app is still the original")

print("\n" + "="*70 + "\n")
