#!/usr/bin/env python3
from x402.http.middleware.flask import payment_middleware, PaymentMiddleware
import os
from dotenv import load_dotenv

load_dotenv()

from flask import Flask
from x402.http import FacilitatorConfig, HTTPFacilitatorClientSync, PaymentOption
from x402.http.types import RouteConfig
from x402.mechanisms.avm.exact.server import ExactAvmScheme
from x402.mechanisms.avm import ALGORAND_TESTNET_CAIP2, USDC_TESTNET_ASA_ID
from x402.server import x402ResourceServerSync

app = Flask(__name__)
print(f'Initial app.wsgi_app: {type(app.wsgi_app)}')

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

print(f'\nCalling payment_middleware(app, routes, server)...')
pm = payment_middleware(app, routes=routes, server=server)

print(f'After payment_middleware call:')
print(f'  app.wsgi_app type: {type(app.wsgi_app)}')
print(f'  PaymentMiddleware instance: {type(pm)}')

print(f'\nChecking if app was wrapped:')
print(f'  pm has _wsgi_middleware: {hasattr(pm, "_wsgi_middleware")}')

print()
print('Trying to manually wrap app.wsgi_app with pm._wsgi_middleware():')
try:
    wsgi_middleware = pm._wsgi_middleware()
    print(f'  Got middleware: {type(wsgi_middleware)}')
    
    # Try to wrap the app's WSGI application
    original_wsgi = app.wsgi_app
    app.wsgi_app = wsgi_middleware(original_wsgi)
    
    print(f'  Wrapped app.wsgi_app')
    print(f'  New app.wsgi_app type: {type(app.wsgi_app)}')
    print(f'  ✓ Successfully attached middleware!')
    
except Exception as e:
    print(f'  ✗ Error: {e}')
    import traceback
    traceback.print_exc()
