#!/usr/bin/env python3
"""Introspect x402HTTPResourceServerSync"""

import os
from dotenv import load_dotenv

load_dotenv()

from x402.http import FacilitatorConfig, HTTPFacilitatorClientSync, PaymentOption
from x402.http.x402_http_server import x402HTTPResourceServerSync
from x402.http.types import RouteConfig
from x402.mechanisms.avm.exact.server import ExactAvmScheme
from x402.mechanisms.avm import ALGORAND_TESTNET_CAIP2, USDC_TESTNET_ASA_ID
from x402.server import x402ResourceServerSync

print("\n" + "="*70)
print("INSPECTING x402HTTPResourceServerSync")
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

print("\nAttributes of x402HTTPResourceServerSync:")
attrs = [attr for attr in dir(http_server) if not attr.startswith('__')]
for attr in attrs[:20]:
    try:
        val = getattr(http_server, attr)
        if not callable(val):
            print(f"  {attr}: {type(val).__name__}")
            if attr == 'routes':
                print(f"    value: {val}")
    except:
        pass

print("\n" + "="*70 + "\n")
