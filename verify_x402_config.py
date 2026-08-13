#!/usr/bin/env python3
import os
from dotenv import load_dotenv

load_dotenv()

print('\n' + '='*70)
print('FINAL CONFIGURATION VERIFICATION')
print('='*70)

print('\nENVIRONMENT VARIABLES:')
print(f'  GEMINI_API_KEY: {"✓ Set" if os.getenv("GEMINI_API_KEY") else "✗ Not set"}')
print(f'  FACILITATOR_URL: {os.getenv("FACILITATOR_URL")}')
print(f'  AVM_ADDRESS: {os.getenv("AVM_ADDRESS")}')
print(f'  X402_NETWORK: {os.getenv("X402_NETWORK")}')
print(f'  X402_PRICE: {os.getenv("X402_PRICE")}')

print('\nX402-AVM SDK:')
try:
    from x402.mechanisms.avm import USDC_TESTNET_ASA_ID, ALGORAND_TESTNET_CAIP2
    print(f'  ALGORAND_TESTNET_CAIP2: {ALGORAND_TESTNET_CAIP2}')
    print(f'  USDC_TESTNET_ASA_ID: {USDC_TESTNET_ASA_ID}')
    print('  ✓ Official SDK imports OK')
except Exception as e:
    print(f'  ✗ ERROR: {e}')

print('\n' + '='*70)
print('READY FOR TESTING')
print('='*70 + '\n')
