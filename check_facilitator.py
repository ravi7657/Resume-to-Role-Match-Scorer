#!/usr/bin/env python3
"""Check facilitator support"""

import os
from dotenv import load_dotenv

load_dotenv()

from x402.http import FacilitatorConfig, HTTPFacilitatorClientSync

print("\n" + "="*70)
print("CHECKING FACILITATOR SUPPORT")
print("="*70)

facilitator_url = os.getenv('FACILITATOR_URL')
facilitator_config = FacilitatorConfig(url=facilitator_url)
facilitator = HTTPFacilitatorClientSync(facilitator_config)

print(f"\nFacilitator: {facilitator_url}")

try:
    # Try to get supported schemes
    print("\nAttempting to fetch facilitator support...")
    
    # Check if there's a method to get support info
    if hasattr(facilitator, 'get_support'):
        support = facilitator.get_support()
        print(f"Support: {support}")
    elif hasattr(facilitator, 'support'):
        print(f"Support: {facilitator.support}")
    
    # List public methods
    print("\nPublic methods:")
    for method in dir(facilitator):
        if not method.startswith('_'):
            print(f"  {method}")
            
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*70 + "\n")
