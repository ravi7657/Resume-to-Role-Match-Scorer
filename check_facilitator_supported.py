#!/usr/bin/env python3
"""Check what the facilitator supports"""

import os
from dotenv import load_dotenv

load_dotenv()

from x402.http import FacilitatorConfig, HTTPFacilitatorClientSync

print("\n" + "="*70)
print("CHECKING FACILITATOR SUPPORTED SCHEMES")
print("="*70)

facilitator_url = os.getenv('FACILITATOR_URL')
facilitator_config = FacilitatorConfig(url=facilitator_url)
facilitator = HTTPFacilitatorClientSync(facilitator_config)

print(f"\nFacilitator: {facilitator_url}")

try:
    supported = facilitator.get_supported()
    print(f"\nget_supported() returned:")
    print(f"  Type: {type(supported)}")
    print(f"  Value: {supported}")
    
    if hasattr(supported, '__dict__'):
        print(f"\n  Attributes:")
        for attr, val in supported.__dict__.items():
            print(f"    {attr}: {val}")
    
except Exception as e:
    print(f"ERROR calling get_supported(): {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*70 + "\n")
