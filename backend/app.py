import os
import json
import hashlib
import sqlite3
import traceback
import re
from io import BytesIO
from pathlib import Path
from datetime import datetime

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv

# x402 Payment Gate - Official x402 SDK (Algorand TestNet USDC - SYNC)
try:
    from x402.http import (
        FacilitatorConfig,
        HTTPFacilitatorClientSync,
        PaymentOption,
    )
    from x402.http.middleware.flask import payment_middleware
    from x402.http.types import RouteConfig
    from x402.mechanisms.avm.exact.server import ExactAvmScheme
    from x402.mechanisms.avm import ALGORAND_TESTNET_CAIP2, USDC_TESTNET_ASA_ID
    from x402.server import x402ResourceServerSync
    X402_AVAILABLE = True
except ImportError as e:
    print(f"WARNING: x402 not available: {e}")
    X402_AVAILABLE = False

load_dotenv()

# ---------------------------------------------------------
# Flask
# ---------------------------------------------------------

app = Flask(__name__, static_folder="../frontend", static_url_path="")
CORS(app)

# ---------------------------------------------------------
# x402 Payment Gate Setup (REAL implementation)
# ---------------------------------------------------------

def setup_x402_payment():
    """
    Setup REAL x402 payment gating using official synchronous x402-avm middleware.
    
    Flow:
    1. POST /api/analyze without payment → HTTP 402 Payment Required
    2. x402 client creates/signs real Algorand TestNet USDC payment
    3. Payment proof sent in X-402-Payment header
    4. GoPlausible facilitator verifies and settles payment
    5. Flask executes /api/analyze → Gemini analysis
    6. Response returned to client
    """
    
    if not X402_AVAILABLE:
        print("⚠ x402 not available - payment gating DISABLED")
        return
    
    avm_address = os.getenv("AVM_ADDRESS", "").strip()
    facilitator_url = os.getenv(
        "FACILITATOR_URL",
        "https://facilitator.goplausible.xyz"
    )
    x402_network = os.getenv(
        "X402_NETWORK",
        ALGORAND_TESTNET_CAIP2
    )
    x402_price = os.getenv("X402_PRICE", "0.01")
    
    if not avm_address:
        print("⚠ AVM_ADDRESS not configured - payment gating DISABLED")
        return
    
    try:
        print("\n" + "="*70)
        print("INITIALIZING x402 REAL PAYMENT GATE (Algorand TestNet USDC)")
        print("="*70)
        
        # 1. Create Facilitator (synchronous)
        facilitator_config = FacilitatorConfig(url=facilitator_url)
        facilitator = HTTPFacilitatorClientSync(facilitator_config)
        
        print(f"\n✓ Facilitator configured")
        print(f"  URL: {facilitator_url}")
        
        # 2. Create synchronous x402 resource server
        server = x402ResourceServerSync(facilitator)
        
        print(f"\n✓ x402ResourceServerSync created")
        
        # 3. Register Algorand Exact AVM scheme for TestNet USDC
        server.register(x402_network, ExactAvmScheme())
        
        print(f"✓ Algorand Scheme registered")
        print(f"  Network: {x402_network}")
        print(f"  USDC ASA ID: {USDC_TESTNET_ASA_ID}")
        
        # 4. Configure protected route: POST /api/analyze
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
        
        print(f"\n✓ Route configuration created")
        print(f"  Protected Route: POST /api/analyze")
        print(f"  Price: ${x402_price} USDC")
        print(f"  Receiver: {avm_address}")
        
        # 5. Apply official synchronous middleware to Flask app
        # This intercepts requests to POST /api/analyze BEFORE the route handler
        pm = payment_middleware(
            app,
            routes=routes,
            server=server,
        )
        
        # Verify middleware is attached
        print(f"\n✓ Official x402 synchronous middleware attached to Flask app")
        print(f"  app.wsgi_app: {app.wsgi_app}")
        print(f"  Is PaymentMiddleware method: {app.wsgi_app.__self__.__class__.__name__ == 'PaymentMiddleware'}")
        print("✓ Payment gate is ACTIVE")
        print("\nPAYMENT FLOW:")
        print("  1. POST /api/analyze (no payment) → HTTP 402 Payment Required")
        print("  2. X-402-Payment header in response with payment requirements")
        print("  3. x402 client signs real Algorand TestNet USDC payment")
        print("  4. Retry with payment proof in X-402-Payment header")
        print("  5. GoPlausible verifies/settles payment")
        print("  6. Flask executes /api/analyze")
        print("  7. Gemini analyzes resume")
        print("  8. JSON response returned (HTTP 200)")
        print("="*70 + "\n")
        
    except Exception as e:
        print(f"✗ ERROR initializing x402: {e}")
        traceback.print_exc()
        return

# Initialize x402 on startup
setup_x402_payment()

# ---------------------------------------------------------
# Database
# ---------------------------------------------------------

DB_PATH = Path(__file__).parent / "results.db"


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS analyses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                resume_hash TEXT NOT NULL,
                role_id TEXT,
                overall_score INTEGER,
                result_json TEXT,
                attested_txn TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)


init_db()

# ---------------------------------------------------------
# Resume Parsing
# ---------------------------------------------------------

def parse_resume_text(file_bytes: bytes, filename: str) -> str:
    fname = filename.lower()

    try:
        if fname.endswith(".pdf"):
            import pymupdf as fitz

            doc = fitz.open(stream=file_bytes, filetype="pdf")

            text = "\n".join(
                page.get_text()
                for page in doc
            )

            doc.close()
            return text

        elif fname.endswith(".docx"):
            import docx

            doc = docx.Document(BytesIO(file_bytes))

            parts = []

            for para in doc.paragraphs:
                if para.text.strip():
                    parts.append(para.text)

            return "\n".join(parts)

        else:
            return file_bytes.decode("utf-8", errors="ignore")

    except Exception:
        return file_bytes.decode("utf-8", errors="ignore")


# ---------------------------------------------------------
# Gemini AI Analysis
# ---------------------------------------------------------

def analyze_with_gemini(
    resume_text: str,
    job_description: str,
    role_id: str
) -> dict:

    from google import genai
    from google.genai import types

    api_key = os.getenv("GEMINI_API_KEY", "")

    if not api_key:
        print("WARNING: GEMINI_API_KEY not found - using fallback analysis")
        return fallback_analysis(resume_text, job_description)

    client = genai.Client(api_key=api_key)

    prompt = f"""
You are an expert technical recruiter and ATS resume analyst.

Analyze the candidate resume against the job description for:

ROLE:
{role_id}

RESUME:
{resume_text[:7000]}

JOB DESCRIPTION:
{job_description[:5000]}

Return ONLY valid JSON.

Use exactly this structure:

{{
  "matched_skills": ["Python", "SQL"],
  "missing_skills": ["Docker", "AWS"],
  "partial_skills": ["Machine Learning"],

  "experience_years_required": 2,
  "experience_years_found": 1,
  "experience_score": 70,

  "education_required": "Bachelor's degree",
  "education_found": "B.Tech",
  "education_score": 90,

  "skill_score": 80,
  "semantic_score": 75,
  "overall_score": 78,

  "strengths": [
    "Strong Python skills",
    "Relevant academic projects"
  ],

  "gaps": [
    "Limited cloud experience"
  ],

  "recommendations": [
    "Add AWS projects",
    "Highlight measurable project outcomes"
  ],

  "summary": "Short professional summary of candidate-job alignment.",

  "hire_recommendation": "Highly Recommended"
}}

Rules:
- Scores must be integers from 0 to 100.
- Do not invent experience.
- Base the analysis only on the supplied resume and job description.
- Return ONLY valid JSON, no markdown, no extra text.
"""

    try:
        response = client.models.generate_content(
            model="gemini-3.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )

        text = response.text.strip()

        # Remove markdown fences if present
        text = re.sub(r"^```json\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
        text = text.strip()

        result = json.loads(text)

        # Validate required fields
        required_fields = [
            "matched_skills", "missing_skills", "partial_skills",
            "experience_years_required", "experience_years_found", "experience_score",
            "education_required", "education_found", "education_score",
            "skill_score", "semantic_score", "overall_score",
            "strengths", "gaps", "recommendations",
            "summary", "hire_recommendation"
        ]

        for field in required_fields:
            if field not in result:
                print(f"WARNING: Missing field in Gemini response: {field}")
                # Use fallback if critical fields missing
                return fallback_analysis(resume_text, job_description)

        print("Gemini AI analysis successful")
        return result

    except json.JSONDecodeError as json_err:
        print(f"JSON parsing error from Gemini: {json_err}")
        print(f"Raw response text: {text[:500]}")
        return fallback_analysis(resume_text, job_description)

    except Exception as e:
        print(f"Gemini API error: {type(e).__name__}: {e}")
        traceback.print_exc()
        return fallback_analysis(resume_text, job_description)


# ---------------------------------------------------------
# Fallback Analysis
# ---------------------------------------------------------

def fallback_analysis(resume_text: str, jd: str) -> dict:

    resume_lower = resume_text.lower()
    jd_lower = jd.lower()

    stop_words = {
        "the", "a", "an", "and", "or", "in", "of", "to",
        "for", "with", "is", "are", "be", "will", "we",
        "you", "our", "have", "has", "can", "this", "that",
        "as", "at", "by", "on", "from", "your", "their",
        "its", "it", "not", "but", "if"
    }

    words = re.findall(
        r"\b[a-zA-Z][a-zA-Z+#.]{2,}\b",
        jd_lower
    )

    jd_words = set(
        w for w in words
        if w not in stop_words
    )

    matched = [
        w for w in jd_words
        if w in resume_lower
    ]

    missing = [
        w for w in jd_words
        if w not in resume_lower
    ]

    skill_score = min(
        100,
        int(
            len(matched) /
            max(len(jd_words), 1) *
            100
        )
    )

    overall = int(
        skill_score * 0.5 +
        60 * 0.3 +
        70 * 0.2
    )

    return {
        "matched_skills": matched[:12],
        "missing_skills": missing[:8],
        "partial_skills": [],

        "experience_years_required": None,
        "experience_years_found": None,
        "experience_score": 60,

        "education_required": "Not specified",
        "education_found": "Not specified",
        "education_score": 70,

        "skill_score": skill_score,
        "semantic_score": max(40, skill_score - 10),
        "overall_score": overall,

        "strengths": [
            "Resume successfully parsed",
            "Relevant keywords identified"
        ],

        "gaps": missing[:3],

        "recommendations": [
            "Add more role-specific skills",
            "Include measurable project outcomes"
        ],

        "summary": (
            f"Keyword-based analysis found "
            f"{len(matched)} relevant matches."
        ),

        "hire_recommendation": "Needs Review"
    }


# ---------------------------------------------------------
# Blockchain
# ---------------------------------------------------------

def attest_on_chain(
    resume_hash_hex: str,
    role_id: str,
    score: int
) -> dict:

    app_id = int(
        os.getenv("CONTRACT_APP_ID", "0")
    )

    if app_id == 0:
        return {
            "status": "skipped",
            "reason": "Blockchain contract not deployed"
        }

    try:
        import algokit_utils

        algorand = (
            algokit_utils.AlgorandClient
            .from_environment()
        )

        deployer = (
            algorand.account
            .from_environment("DEPLOYER")
        )

        from smart_contracts.artifacts.resume_verifier.resume_verifier_client import (
            ResumeVerifierClient,
            RegisterAttestationArgs
        )

        client = ResumeVerifierClient(
            algorand=algorand,
            app_id=app_id,
            default_sender=deployer.address,
            default_signer=deployer.signer
        )

        resume_hash_bytes = bytes.fromhex(
            resume_hash_hex
        )

        hash_tuple = tuple(resume_hash_bytes)

        payment_txn = (
            algorand.create_transaction.payment(
                algokit_utils.PaymentParams(
                    sender=deployer.address,
                    receiver=deployer.address,
                    amount=algokit_utils.AlgoAmount(
                        micro_algo=500_000
                    )
                )
            )
        )

        result = client.send.register_attestation(
            args=RegisterAttestationArgs(
                resume_hash=hash_tuple,
                role_id=role_id[:64],
                match_score=score,
                payment=payment_txn
            )
        )

        return {
            "status": "attested",
            "txn_id": result.tx_id,
            "app_id": app_id,
            "round": result.confirmed_round
        }

    except Exception as e:
        print("Blockchain error:", e)

        return {
            "status": "error",
            "reason": str(e)
        }


# ---------------------------------------------------------
# Routes
# ---------------------------------------------------------

@app.route("/")
def index():
    return send_from_directory(
        "../frontend",
        "index.html"
    )


@app.route("/api/health")
def health():

    return jsonify({
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat()
    })


# ---------------------------------------------------------
# Analyze Resume
# ---------------------------------------------------------

@app.route("/api/analyze", methods=["POST"])
def analyze():

    try:

        resume_file = request.files.get(
            "resume"
        )

        job_description = request.form.get(
            "job_description",
            ""
        )

        role_id = request.form.get(
            "role_id",
            "general"
        ).strip()[:64]

        if not resume_file:
            return jsonify({
                "error": "No resume file provided"
            }), 400

        if not job_description.strip():
            return jsonify({
                "error": "No job description provided"
            }), 400

        file_bytes = resume_file.read()

        filename = (
            resume_file.filename
            or "resume.txt"
        )

        # Parse resume
        resume_text = parse_resume_text(
            file_bytes,
            filename
        )

        if not resume_text.strip():
            return jsonify({
                "error": "Could not extract text from resume"
            }), 400

        # SHA-256 hash
        resume_hash = hashlib.sha256(
            file_bytes
        ).hexdigest()

        # Gemini analysis
        analysis = analyze_with_gemini(
            resume_text,
            job_description,
            role_id
        )

        overall_score = int(
            analysis.get(
                "overall_score",
                50
            )
        )

        # Store database record
        with get_db() as conn:

            conn.execute(
                """
                INSERT INTO analyses
                (
                    resume_hash,
                    role_id,
                    overall_score,
                    result_json
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    resume_hash,
                    role_id,
                    overall_score,
                    json.dumps(analysis)
                )
            )

        # IMPORTANT:
        # Return both the original AI structure
        # and the exact structure expected by frontend.

        return jsonify({

            "resume_hash": resume_hash,

            "role_id": role_id,

            "overall_score": overall_score,

            "scores": {
                "skills": int(
                    analysis.get(
                        "skill_score",
                        0
                    )
                ),

                "experience": int(
                    analysis.get(
                        "experience_score",
                        0
                    )
                ),

                "education": int(
                    analysis.get(
                        "education_score",
                        0
                    )
                ),

                "semantic": int(
                    analysis.get(
                        "semantic_score",
                        0
                    )
                )
            },

            "matched_skills": analysis.get(
                "matched_skills",
                []
            ),

            "missing_skills": analysis.get(
                "missing_skills",
                []
            ),

            "partial_skills": analysis.get(
                "partial_skills",
                []
            ),

            "strengths": analysis.get(
                "strengths",
                []
            ),

            "gaps": analysis.get(
                "gaps",
                []
            ),

            "recommendations": analysis.get(
                "recommendations",
                []
            ),

            "summary": analysis.get(
                "summary",
                "Analysis completed."
            ),

            "recommendation": analysis.get(
                "hire_recommendation",
                "Needs Review"
            ),

            "analysis": analysis,

            "resume_text_preview": (
                resume_text[:300] + "..."
                if len(resume_text) > 300
                else resume_text
            )
        })

    except Exception as e:

        traceback.print_exc()

        return jsonify({
            "error": str(e)
        }), 500


# ---------------------------------------------------------
# Blockchain Attestation
# ---------------------------------------------------------

@app.route("/api/attest", methods=["POST"])
def attest():

    try:

        data = request.get_json() or {}

        resume_hash = data.get(
            "resume_hash",
            ""
        )

        role_id = data.get(
            "role_id",
            "general"
        )

        score = int(
            data.get("score", 0)
        )

        if (
            not resume_hash
            or len(resume_hash) != 64
        ):
            return jsonify({
                "error": "Invalid resume hash"
            }), 400

        result = attest_on_chain(
            resume_hash,
            role_id,
            score
        )

        if result.get("status") == "attested":

            with get_db() as conn:

                conn.execute(
                    """
                    UPDATE analyses
                    SET attested_txn=?
                    WHERE resume_hash=?
                    """,
                    (
                        result.get("txn_id"),
                        resume_hash
                    )
                )

        return jsonify(result)

    except Exception as e:

        traceback.print_exc()

        return jsonify({
            "error": str(e)
        }), 500


# ---------------------------------------------------------
# Verify
# ---------------------------------------------------------

@app.route(
    "/api/verify/<resume_hash>",
    methods=["GET"]
)
def verify(resume_hash):

    app_id = int(
        os.getenv(
            "CONTRACT_APP_ID",
            "0"
        )
    )

    if app_id == 0:

        return jsonify({
            "verified": False,
            "reason": "Contract not deployed"
        })

    return jsonify({
        "verified": False,
        "reason": "Local blockchain verification mode"
    })


# ---------------------------------------------------------
# History
# ---------------------------------------------------------

@app.route(
    "/api/history",
    methods=["GET"]
)
def history():

    with get_db() as conn:

        rows = conn.execute(
            """
            SELECT
                id,
                resume_hash,
                role_id,
                overall_score,
                attested_txn,
                created_at
            FROM analyses
            ORDER BY id DESC
            LIMIT 10
            """
        ).fetchall()

    return jsonify([
        dict(row)
        for row in rows
    ])


# ---------------------------------------------------------
# Main
# ---------------------------------------------------------

if __name__ == "__main__":

    print(
        "🚀 Resume Role Matcher "
        "backend starting on "
        "http://localhost:5000"
    )

    app.run(
        debug=False,
        port=5000,
        host="0.0.0.0"
    )