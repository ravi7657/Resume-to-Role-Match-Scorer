#!/usr/bin/env python
"""
run.py — Start the Resume Role Matcher server
Usage:
    python run.py
    # or
    algokit deploy && python run.py
"""
import os
import sys
import subprocess
from pathlib import Path

ROOT = Path(__file__).parent

def check_env():
    env_file = ROOT / ".env"
    if not env_file.exists():
        example = ROOT / ".env.example"
        if example.exists():
            import shutil
            shutil.copy(example, env_file)
            print("⚠  Created .env from .env.example — please add your ANTHROPIC_API_KEY")
        else:
            env_file.write_text("ANTHROPIC_API_KEY=\n")

def try_deploy_contract():
    """Attempt to deploy the smart contract if CONTRACT_APP_ID is not set."""
    from dotenv import load_dotenv
    load_dotenv()
    if os.getenv("CONTRACT_APP_ID", "0") != "0":
        print(f"✅ Contract deployed at app_id={os.getenv('CONTRACT_APP_ID')}")
        return
    print("ℹ  CONTRACT_APP_ID not set — skipping blockchain attestation (demo mode)")

def main():
    check_env()
    try_deploy_contract()

    print("\n" + "═" * 60)
    print("  🚀 Resume Role Matcher")
    print("  📍 http://localhost:5000")
    print("═" * 60 + "\n")

    backend_dir = ROOT / "backend"
    sys.path.insert(0, str(ROOT))
    os.chdir(backend_dir)

    from backend.app import app
    app.run(debug=False, port=5000, host="0.0.0.0")

if __name__ == "__main__":
    main()
