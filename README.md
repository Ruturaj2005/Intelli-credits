# Intelli-Credit — AI-Powered Corporate Credit Appraisal Engine

An end-to-end AI system that automates Credit Appraisal Memo (CAM) generation for Indian corporate lending using a 4-agent LangGraph pipeline powered by Claude claude-sonnet-4-20250514.

---

## Architecture Overview

```
                    ┌─────────────────────────────────────────┐
                    │         LangGraph StateGraph            │
                    │                                         │
 Documents ──►  ┌──┴──────────────┐   ┌──────────────────┐   │
                │ Ingestor Agent  │   │ Research Agent   │   │
 (PDFs)         │ PyMuPDF+LLM     │   │ Tavily+ReAct+LLM │   │
                └──────┬──────────┘   └────────┬─────────┘   │
                       │  (parallel)            │             │
                       └──────────┬─────────────┘             │
                                  │                           │
                         ┌────────▼────────┐                  │
                         │  Arbitration     │ (conflict check) │
                         └────────┬────────┘                  │
                                  │                           │
                         ┌────────▼────────┐                  │
                         │  Risk Scorer    │ Five Cs + SHAP   │
                         └────────┬────────┘                  │
                                  │                           │
                         ┌────────▼────────┐                  │
                         │  CAM Generator  │ .docx output     │
                         └─────────────────┘                  │
                    └─────────────────────────────────────────┘
                              │
                         FastAPI + WebSocket
                              │
                         React Frontend
```

| Agent | Purpose | Key Tools |
|---|---|---|
| **Ingestor** | Parse financials & **Screen for forgery** | PyMuPDF, `document_forgery_detector` |
| **Research** | Web research & **EPFO verification** | Tavily, `epfo_operations_tracker` |
| **Scorer** | 5Cs + **SHAP Narratives** | `shap_narrative_generator`, `qualitative_score_quantifier` |
| **CAM Generator** | Generate Word doc with **Judge's Walkthrough** | python-docx, Claude |

---

## v2.1 Advanced Features (The "Fraud & GenAI" Layer)

### 1. Document Forgery Detection
The pipeline now starts with a **Gateway Forgery Check**. It analyzes PDF metadata and pixel-level variance. If a document is flagged as "REJECT", the orchestrator halts the pipeline immediately to prevent fraud.

### 2. Director Network Risk Analysis (MCA v2)
Beyond basic company stats, we now map the "Director Network". This flags if any director is linked to entities currently in **NCLT proceedings**, shell companies, or GST-delisted ventures.

### 3. EPFO Operational Reality Check
Compares claimed revenue against actual EPFO provident fund filings. If a company claims ₹50Cr revenue but has only 2 employees, it is flagged as a **Ghost Company** (RF035).

### 4. SHAP-Powered "Judge's Walkthrough"
Instead of just showing numeric scores, GenAI now writes a narrative explanation of the math. It translates complex SHAP attributions into a natural language "Judge's Walkthrough" for credit committees.

### 5. MD&A NLP Sentiment
Analysis of "Management Discussion & Analysis" from Annual Reports to detect subtle linguistic cues of distress or "going concern" risks that aren't yet in the numbers.

---

## Differentiating Features

### 1. GSTR-2A vs GSTR-3B Reconciliation
Automatically compares self-declared sales (GSTR-3B) against auto-populated purchase data (GSTR-2A). A discrepancy >15% triggers a HIGH severity revenue inflation flag — a real Indian banking fraud detection technique.

### 2. Agent Arbitration
When the Ingestor finds strong financials but the Research Agent finds serious risk signals (or vice versa), a **CONFLICT DETECTED** step is shown in the pipeline. Claude is prompted to reconcile the signals and adjust risk weighting before the scorer runs.

### 3. Qualitative Credit Officer Override
Credit officer field notes (e.g. "factory at 40% capacity") are factored into Claude's scoring. A **before/after** comparison is shown on the Results page.

### 4. Full Explainability Trail
Every Five C score is clickable on the Results page → shows the exact reasoning chain from the AI scorer. SHAP-style attributions show each C's contribution vs a neutral baseline.

### 5. Live WebSocket Pipeline
Agent progress streams in real-time to the Pipeline view with a terminal-style log. Each agent's sub-tasks check off as they complete.

---

## Project Structure

```
intelli-credit/
├── backend/
│   ├── main.py                  # FastAPI app + WebSocket + endpoints
│   ├── requirements.txt
│   ├── agents/
│   │   ├── orchestrator.py      # LangGraph StateGraph
│   │   ├── ingestor_agent.py    # Agent 1: Document parsing + GST check
│   │   ├── research_agent.py    # Agent 2: Web research (ReAct)
│   │   ├── scorer_agent.py      # Agent 3: Five Cs scoring
│   │   └── cam_generator.py     # Agent 4: Word doc generation
|   ├── tools/
│   │   ├── pdf_parser.py        # PyMuPDF + pdfplumber
│   │   ├── gst_analyser.py      # GSTR reconciliation logic
│   │   ├── web_search.py        # Tavily wrapper
│   │   ├── document_forgery_detector.py  # NEW: PDF Tampering check
│   │   ├── mca_network_analyzer.py     # NEW: Director graph risk
│   │   ├── cibil_velocity_analyzer.py  # NEW: Credit enquiry spikes
│   │   ├── epfo_operations_tracker.py  # NEW: Ghost company detection
│   │   ├── mda_sentiment_analyzer.py   # NEW: MD&A NLP
│   │   ├── qualitative_score_quantifier.py # NEW: Note-to-Score logic
│   │   └── shap_narrative_generator.py # NEW: GenAI Walkthrough
│   ├── models/
│   │   └── schemas.py           # Pydantic models
│   └── utils/
│       └── prompts.py           # All LLM prompts
└── frontend/
    ├── package.json
    ├── vite.config.js
    ├── tailwind.config.js
    └── src/
        ├── App.jsx
        ├── index.css
        ├── pages/
        │   ├── Dashboard.jsx    # KPI metrics + recent applications
        │   ├── NewAppraisal.jsx # Document upload form
        │   ├── Pipeline.jsx     # Live agent pipeline view
        │   └── Results.jsx      # Full CAM results with charts
        └── components/
            ├── AgentBlock.jsx   # Agent status card with checklist
            ├── FiveCsRadar.jsx  # Pentagon radar chart (Recharts)
            ├── RedFlagCard.jsx  # Risk flag display
            └── TerminalLog.jsx  # Terminal-style log stream
```

---

## Setup & Running

### Prerequisites
- Python 3.11+
- Node.js 18+
- Anthropic API key
- Tavily API key

### Backend Setup

```bash
cd backend

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp ../.env.example .env
# Edit .env and add your API keys:
# ANTHROPIC_API_KEY=sk-ant-...
# TAVILY_API_KEY=tvly-...

# Start the backend
uvicorn main:app --reload --port 8000
```

Backend runs at: `http://localhost:8000`  
API docs: `http://localhost:8000/docs`

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start dev server
npm run dev
```

Frontend runs at: `http://localhost:5173`

---

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/appraisal/start` | Upload docs + start pipeline |
| `GET` | `/api/appraisal/{job_id}/status` | Poll agent status + logs |
| `GET` | `/api/appraisal/{job_id}/results` | Full results JSON |
| `GET` | `/api/appraisal/{job_id}/download` | Download CAM .docx |
| `WS` | `/ws/{job_id}` | Live log stream via WebSocket |
| `GET` | `/api/dashboard/summary` | Dashboard KPI aggregates |

---

## Environment Variables

| Variable | Description | Default |
|---|---|---|
| `ANTHROPIC_API_KEY` | Anthropic Claude API key | Required |
| `TAVILY_API_KEY` | Tavily search API key | Required |
| `MAX_FILE_SIZE_MB` | Max upload size per file | 50 |
| `SQLITE_DB_PATH` | SQLite database path | `./intelli_credit.db` |
| `UPLOAD_DIR` | File upload directory | `./uploads` |
| `CORS_ORIGINS` | Allowed CORS origins | `http://localhost:5173` |

---

## Five Cs Scoring Model

| C | Weight | Key Inputs |
|---|---|---|
| Character | 25% | Promoter integrity score, litigation findings |
| Capacity | 30% | DSCR, revenue CAGR, EBITDA margins |
| Capital | 20% | Net worth, Debt-to-Equity ratio |
| Collateral | 15% | Collateral type & value vs loan amount |
| Conditions | 10% | Sector outlook, regulatory environment |

**Decision thresholds:**
- Weighted total > 70 → **APPROVE**
- Weighted total 50–70 → **CONDITIONAL APPROVE** (with covenants)
- Weighted total < 50 → **REJECT**
- Any HIGH severity fraud/litigation → **AUTO-REJECT** regardless of score

---

## Tech Stack

**Backend:** Python 3.11 · FastAPI · LangGraph · LangChain · Claude claude-sonnet-4-20250514 · Tavily · PyMuPDF · pdfplumber · python-docx · pandas · numpy · SHAP · aiosqlite · WebSockets

**Frontend:** React 18 · Vite · Tailwind CSS · Recharts · Axios · react-dropzone · react-router-dom

---

## Design System

| Token | Value | Usage |
|---|---|---|
| `--bg` | `#020608` | Page background |
| `--surface` | `#0a0f12` | Cards |
| `--accent` | `#00d4aa` | Approved / positive |
| `--danger` | `#ef476f` | Rejected / high risk |
| `--warning` | `#ffd166` | Conditional / caution |
| `--muted` | `#4a6070` | Secondary text |

**Fonts:** Syne (headings) · DM Mono (numbers/code) · Inter (body)
