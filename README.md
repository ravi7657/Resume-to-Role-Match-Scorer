# Resume Role Matcher 🎯

> **Blockchain-Verified Career Intelligence powered by Claude AI & Algorand**

## 🚀 Quick Start (30 seconds)

```bash
# 1. Add your Claude API key
cp .env.example .env
# Edit .env → set ANTHROPIC_API_KEY=sk-ant-...

# 2. Start the server
python run.py

# 3. Open browser
# → http://localhost:5000
```

## 🏗 Architecture

```
Upload Resume (PDF/DOCX/TXT)
        ↓
  Flask Backend (port 5000)
        ↓
  Claude Sonnet AI Analysis
  ├── Skills extraction & matching
  ├── Experience evaluation
  ├── Education assessment
  └── Semantic similarity
        ↓
  Deterministic Scoring Engine
  (Skill 40% + Experience 30% + Education 15% + Semantic 15%)
        ↓
  Results Dashboard (Chart.js visualizations)
        ↓
  Algorand Blockchain Attestation (0.5 ALGO)
  └── SHA-256 hash stored in Box Storage
  └── Tamper-evident, immutable record
```

## 📦 Tech Stack

| Layer | Technology |
|-------|-----------|
| Smart Contract | Algorand Python (algopy) |
| Blockchain | Algorand LocalNet (AlgoKit) |
| AI | Anthropic Claude Sonnet 4.5 |
| Backend | Python Flask |
| Resume Parsing | PyMuPDF + python-docx |
| Frontend | Vanilla HTML/CSS/JS + Chart.js |

## 🔑 Environment Variables

| Variable | Description |
|----------|-------------|
| `ANTHROPIC_API_KEY` | Claude API key (required for AI) |
| `ALGOD_TOKEN` | Algorand node token |
| `ALGOD_SERVER` | Algorand node URL |
| `CONTRACT_APP_ID` | Deployed contract ID (optional) |

## 🧪 Smart Contract Tests

```bash
poetry run python -m pytest tests/ -v
# 21/21 tests passing ✅
```

## 🌐 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/analyze` | Upload resume + JD → AI analysis |
| POST | `/api/attest` | Attest score on Algorand |
| GET | `/api/verify/<hash>` | Verify attestation on-chain |
| GET | `/api/history` | Recent analysis history |
| GET | `/api/health` | Health check |

## Built at Hackathon 2026 🏆
