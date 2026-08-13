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

app = Flask(__name__)
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

pm = payment_middleware(app, routes=routes, server=server)

print('\nPaymentMiddleware instance info:')
print(f'Type: {type(pm)}')
print(f'\nPublic attributes/methods:')
attrs = [x for x in dir(pm) if not x.startswith('_')]
for attr in attrs:
    val = getattr(pm, attr)
    if callable(val):
        try:
            sig = str(inspect.signature(val)) if hasattr(inspect, 'signature') else '(...)'
        except:
            sig = '(...)'
        print(f'  {attr}{sig}')
    else:
        print(f'  {attr} = {type(val).__name__}')

print(f'\nFlask app state after payment_middleware call:')
print(f'  before_request handlers: {bool(app.before_request_funcs) and len(app.before_request_funcs) > 0}')
print(f'  Number of URL rules: {len(list(app.url_map.iter_rules()))}')

import inspect
print(f'\nLooking for init_app or attach methods...')
for method_name in ['init_app', 'attach', 'register']:
    if hasattr(pm, method_name):
        print(f'  Found: {method_name}')
        method = getattr(pm, method_name)
        print(f'    Signature: {inspect.signature(method)}')
