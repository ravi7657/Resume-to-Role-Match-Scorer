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

# Create a test app
test_app = Flask(__name__)

# Get config
avm_address = os.getenv("AVM_ADDRESS")
facilitator_url = os.getenv("FACILITATOR_URL")
x402_network = os.getenv("X402_NETWORK", ALGORAND_TESTNET_CAIP2)
x402_price = os.getenv("X402_PRICE", "0.01")

print("\nDEBUG: x402 Middleware Initialization")
print(f"AVM_ADDRESS: {avm_address}")
print(f"FACILITATOR_URL: {facilitator_url}")
print(f"X402_NETWORK: {x402_network}")

# Create facilitator
facilitator_config = FacilitatorConfig(url=facilitator_url)
facilitator = HTTPFacilitatorClientSync(facilitator_config)
print("✓ Facilitator created")

# Create server
server = x402ResourceServerSync(facilitator)
print("✓ Server created")

# Register scheme
server.register(x402_network, ExactAvmScheme())
print("✓ Scheme registered")

# Create routes
routes = {
    "POST /api/analyze": RouteConfig(
        accepts=[
            PaymentOption(
                scheme="exact",
                pay_to=avm_address,
                price=f"${x402_price}",
                network=x402_network,
                extra={"asset": USDC_TESTNET_ASA_ID},
            )
        ],
        description="Resume Role Matcher AI analysis",
        mime_type="application/json",
    )
}
print("✓ Routes configured")

# Try to attach middleware
print("\nAttaching payment_middleware...")
print(f"payment_middleware signature: {payment_middleware.__doc__}")

try:
    result = payment_middleware(
        test_app,
        routes=routes,
        server=server,
    )
    print(f"✓ payment_middleware returned: {result}")
    print(f"  type: {type(result)}")
except Exception as e:
    print(f"✗ ERROR: {e}")
    import traceback
    traceback.print_exc()

# Check if middleware was attached
print("\nChecking Flask app state:")
print(f"  before_request handlers: {test_app.before_request_funcs}")
print(f"  after_request handlers: {test_app.after_request_funcs}")
print(f"  error handlers: {test_app.error_handler_spec}")
print(f"  url_map rules: {list(test_app.url_map.iter_rules())}")
