#!/usr/bin/env python3
"""Check network configuration"""

import os
from dotenv import load_dotenv

load_dotenv()

print('Environment variables:')
print(f"X402_NETWORK: {os.getenv('X402_NETWORK')}")

# Import the constant
from x402.mechanisms.avm import ALGORAND_TESTNET_CAIP2, USDC_TESTNET_ASA_ID
print(f'ALGORAND_TESTNET_CAIP2 from SDK: {ALGORAND_TESTNET_CAIP2}')
print(f'USDC_TESTNET_ASA_ID: {USDC_TESTNET_ASA_ID}')

# Check .env file directly
print('\n.env file content (x402 related):')
with open('.env', 'r') as f:
    for line in f:
        if 'X402' in line or 'ALGORAND' in line or 'AVM' in line:
            print(f'  {line.strip()}')
