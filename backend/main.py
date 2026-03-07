"""
FastAPI application — Intelli-Credit Backend
Handles file uploads, orchestrates the multi-agent pipeline,
persists state in SQLite, and streams live logs via WebSocket.
"""
from __future__ import annotations

import asyncio
import json
import os
import shutil
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiosqlite
from dotenv import load_dotenv
from fastapi import (
    BackgroundTasks,
    FastAPI,
    File,
    Form,
    HTTPException,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

load_dotenv()

from agents.orchestrator import run_orchestrator
from models.schemas import (
    AppraisalResultsResponse,
    AppraisalStartResponse,
    AppraisalStatusResponse,
)

# ─── Config ───────────────────────────────────────────────────────────────────

DB_PATH = os.getenv("SQLITE_DB_PATH", "./intelli_credit.db")
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "./uploads"))
MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "50"))
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# ─── DB Helpers ───────────────────────────────────────────────────────────────

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                job_id      TEXT PRIMARY KEY,
                status      TEXT NOT NULL DEFAULT 'QUEUED',
                company_name TEXT,
                sector      TEXT,
                state_json  TEXT,
                created_at  TEXT,
                updated_at  TEXT
            )
        """)
        await db.commit()


async def save_job(job_id: str, state: Dict[str, Any]):
    async with aiosqlite.connect(DB_PATH) as db:
        now = datetime.now().isoformat()
        await db.execute(
            """INSERT INTO jobs (job_id, status, company_name, sector, state_json, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(job_id) DO UPDATE SET
                   status=excluded.status,
                   state_json=excluded.state_json,
                   updated_at=excluded.updated_at
            """,
            (
                job_id,
                state.get("status", "QUEUED"),
                state.get("company_name", ""),
                state.get("sector", ""),
                json.dumps(state),
                now,
                now,
            ),
        )
        await db.commit()


async def load_job(job_id: str) -> Optional[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT state_json FROM jobs WHERE job_id = ?", (job_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return json.loads(row[0])
    return None


async def list_recent_jobs(limit: int = 20) -> List[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT job_id, status, company_name, sector, created_at, updated_at "
            "FROM jobs ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ) as cursor:
            rows = await cursor.fetchall()
            return [
                {
                    "job_id": r[0],
                    "status": r[1],
                    "company_name": r[2],
                    "sector": r[3],
                    "created_at": r[4],
                    "updated_at": r[5],
                }
                for r in rows
            ]


# ─── WebSocket Manager ────────────────────────────────────────────────────────

class ConnectionManager:
    """Manages active WebSocket connections keyed by job_id."""

    def __init__(self):
        self._connections: Dict[str, WebSocket] = {}

    async def connect(self, job_id: str, ws: WebSocket):
        await ws.accept()
        self._connections[job_id] = ws

    def disconnect(self, job_id: str):
        self._connections.pop(job_id, None)

    async def send_json(self, job_id: str, payload: Dict[str, Any]):
        ws = self._connections.get(job_id)
        if ws:
            try:
                await ws.send_json(payload)
            except Exception:
                self.disconnect(job_id)


manager = ConnectionManager()


# ─── Lifespan ─────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


# ─── App ──────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Intelli-Credit API",
    description="AI-powered Corporate Credit Appraisal Engine",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS + ["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Background Task ──────────────────────────────────────────────────────────

async def _run_pipeline(job_id: str, initial_state: Dict[str, Any]):
    """Background task: run the orchestrator and persist updates."""

    async def on_update(state: Dict[str, Any]):
        await save_job(job_id, state)
        # Broadcast to WebSocket if connected
        await manager.send_json(job_id, {"type": "update", "payload": {
            "status": state.get("status"),
            "agent_statuses": state.get("agent_statuses", {}),
            "conflict_detected": state.get("conflict_detected", False),
            "logs": state.get("logs", [])[-20:],  # Last 20 log entries
        }})

    try:
        final_state = await run_orchestrator(initial_state, on_update=on_update)
        await save_job(job_id, final_state)
        await manager.send_json(job_id, {"type": "complete", "payload": {
            "status": final_state.get("status"),
            "recommendation": final_state.get("final_recommendation", {}).get("recommendation"),
        }})
    except Exception as exc:
        error_state = {**initial_state, "status": "FAILED", "error_message": str(exc)}
        await save_job(job_id, error_state)
        await manager.send_json(job_id, {"type": "error", "payload": {"message": str(exc)}})


# ─── Endpoints ────────────────────────────────────────────────────────────────

@app.post("/api/appraisal/start", response_model=AppraisalStartResponse)
async def start_appraisal(
    background_tasks: BackgroundTasks,
    company_name: str = Form(...),
    sector: str = Form(...),
    loan_amount: float = Form(0.0),
    qualitative_notes: str = Form(""),
    annual_report: Optional[UploadFile] = File(None),
    gst_returns: Optional[UploadFile] = File(None),
    bank_statements: Optional[UploadFile] = File(None),
    itr: Optional[UploadFile] = File(None),
    legal_documents: Optional[UploadFile] = File(None),
    mca_filings: Optional[UploadFile] = File(None),
):
    """
    Accept multipart form with up to 6 document uploads.
    Kick off the appraisal pipeline as a background task.
    """
    job_id = str(uuid.uuid4())
    job_dir = UPLOAD_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    # ── Save uploaded files ───────────────────────────────────────────────────
    upload_mapping = {
        "annual_report": annual_report,
        "gst_returns": gst_returns,
        "bank_statements": bank_statements,
        "itr": itr,
        "legal_documents": legal_documents,
        "mca_filings": mca_filings,
    }

    documents: List[Dict[str, Any]] = []

    for doc_type, upload_file in upload_mapping.items():
        if upload_file is None or upload_file.filename == "":
            continue

        # Validate file size
        content = await upload_file.read()
        size_mb = len(content) / (1024 * 1024)
        if size_mb > MAX_FILE_SIZE_MB:
            raise HTTPException(
                status_code=413,
                detail=f"{upload_file.filename} exceeds {MAX_FILE_SIZE_MB}MB limit.",
            )

        # Save to disk
        safe_name = upload_file.filename.replace("/", "_").replace("\\", "_")
        file_path = job_dir / safe_name
        with open(file_path, "wb") as f:
            f.write(content)

        # Parse document
        if upload_file.filename.lower().endswith(".pdf"):
            from tools.pdf_parser import parse_financial_document
            parsed = parse_financial_document(str(file_path), doc_type)
        else:
            # For Excel/CSV/other, store raw path reference
            parsed = {
                "file_path": str(file_path),
                "file_name": safe_name,
                "doc_type": doc_type,
                "text": f"[Non-PDF file: {safe_name} — manual extraction required]",
                "tables_text": "",
                "page_count": 0,
                "error": None,
            }

        documents.append(parsed)

    # ── Build initial state ───────────────────────────────────────────────────
    initial_state: Dict[str, Any] = {
        "job_id": job_id,
        "company_name": company_name.strip(),
        "sector": sector.strip(),
        "loan_amount_requested": loan_amount,
        "qualitative_notes": qualitative_notes.strip(),
        "documents": documents,
        "extracted_financials": {},
        "fraud_flags": [],
        "research_findings": {},
        "five_cs_scores": {},
        "final_recommendation": {},
        "arbitration_result": {},
        "pre_override_scores": {},
        "override_applied": False,
        "cam_path": "",
        "logs": [
            {
                "timestamp": datetime.now().strftime("%H:%M:%S"),
                "agent": "SYSTEM",
                "message": f"Job {job_id} created. {len(documents)} document(s) uploaded.",
                "level": "INFO",
            }
        ],
        "status": "QUEUED",
        "conflict_detected": False,
        "agent_statuses": {
            "ingestor": "PENDING",
            "research": "PENDING",
            "scorer": "PENDING",
            "cam_generator": "PENDING",
        },
        "started_at": datetime.now().isoformat(),
        "completed_at": None,
        "error_message": "",
    }

    await save_job(job_id, initial_state)
    background_tasks.add_task(_run_pipeline, job_id, initial_state)

    return AppraisalStartResponse(
        job_id=job_id,
        message=f"Appraisal for '{company_name}' queued. {len(documents)} document(s) received.",
    )


@app.get("/api/appraisal/{job_id}/status", response_model=AppraisalStatusResponse)
async def get_status(job_id: str):
    state = await load_job(job_id)
    if not state:
        raise HTTPException(status_code=404, detail="Job not found.")

    return AppraisalStatusResponse(
        job_id=job_id,
        status=state.get("status", "UNKNOWN"),
        agent_statuses=state.get("agent_statuses", {}),
        logs=state.get("logs", []),
        conflict_detected=state.get("conflict_detected", False),
        started_at=state.get("started_at"),
        completed_at=state.get("completed_at"),
        error_message=state.get("error_message", ""),
    )


@app.get("/api/appraisal/{job_id}/results", response_model=AppraisalResultsResponse)
async def get_results(job_id: str):
    state = await load_job(job_id)
    if not state:
        raise HTTPException(status_code=404, detail="Job not found.")
    if state.get("status") not in ("COMPLETED", "FAILED"):
        raise HTTPException(status_code=202, detail="Appraisal still in progress.")

    return AppraisalResultsResponse(
        job_id=job_id,
        company_name=state.get("company_name", ""),
        sector=state.get("sector", ""),
        loan_amount_requested=state.get("loan_amount_requested", 0),
        extracted_financials=state.get("extracted_financials", {}),
        research_findings=state.get("research_findings", {}),
        five_cs_scores=state.get("five_cs_scores", {}),
        final_recommendation=state.get("final_recommendation", {}),
        arbitration_result=state.get("arbitration_result", {}),
        pre_override_scores=state.get("pre_override_scores", {}),
        override_applied=state.get("override_applied", False),
        fraud_flags=state.get("fraud_flags", []),
        cam_path=state.get("cam_path", ""),
        # New dynamic weighting fields
        dynamic_weight_config=state.get("dynamic_weight_config", {}),
        risk_profile=state.get("risk_profile", ""),
        red_flag_evaluation=state.get("red_flag_evaluation", {}),
        for_analysis=state.get("for_analysis", {}),
        working_capital_analysis=state.get("working_capital_analysis", {}),
        started_at=state.get("started_at"),
        completed_at=state.get("completed_at"),
    )


@app.get("/api/appraisal/{job_id}/download")
async def download_cam(job_id: str):
    state = await load_job(job_id)
    if not state:
        raise HTTPException(status_code=404, detail="Job not found.")

    cam_path = state.get("cam_path", "")
    if not cam_path or not Path(cam_path).exists():
        raise HTTPException(status_code=404, detail="CAM document not yet generated.")

    filename = Path(cam_path).name
    return FileResponse(
        path=cam_path,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=filename,
    )


@app.get("/api/dashboard/summary")
async def dashboard_summary():
    """Return aggregated stats for the Dashboard page."""
    jobs = await list_recent_jobs(limit=100)

    today = datetime.now().date().isoformat()
    today_jobs = [j for j in jobs if (j.get("created_at") or "").startswith(today)]

    completed_jobs = [j for j in jobs if j.get("status") == "COMPLETED"]
    approvals = 0
    total_minutes = 0
    for j in completed_jobs:
        state = await load_job(j["job_id"])
        if state:
            rec = state.get("final_recommendation", {}).get("recommendation", "")
            if "APPROVE" in rec:
                approvals += 1
            started = state.get("started_at")
            completed = state.get("completed_at")
            if started and completed:
                try:
                    t0 = datetime.fromisoformat(started)
                    t1 = datetime.fromisoformat(completed)
                    total_minutes += (t1 - t0).total_seconds() / 60
                except Exception:
                    pass

    avg_minutes = round(total_minutes / len(completed_jobs), 1) if completed_jobs else 0
    approval_rate = round((approvals / len(completed_jobs)) * 100, 1) if completed_jobs else 0

    return {
        "cases_today": len(today_jobs),
        "avg_turnaround_min": avg_minutes,
        "approval_rate_pct": approval_rate,
        "pending_reviews": len([j for j in jobs if j.get("status") == "RUNNING"]),
        "recent_applications": await _enrich_recent(jobs[:10]),
    }


async def _enrich_recent(jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    enriched = []
    for j in jobs:
        state = await load_job(j["job_id"])
        if not state:
            enriched.append(j)
            continue
        rec = state.get("final_recommendation", {})
        scores = state.get("five_cs_scores", {})
        started = state.get("started_at")
        completed = state.get("completed_at")
        turnaround = ""
        if started and completed:
            try:
                t0 = datetime.fromisoformat(started)
                t1 = datetime.fromisoformat(completed)
                delta = t1 - t0
                mins, secs = divmod(int(delta.total_seconds()), 60)
                turnaround = f"{mins}m {secs}s"
            except Exception:
                pass
        # Get risk profile and red flag info
        risk_profile = state.get("risk_profile", "")
        red_flags = state.get("red_flag_evaluation", {})
        flag_count = red_flags.get("total_flag_count", 0) if red_flags else 0

        enriched.append({
            **j,
            "recommendation": rec.get("recommendation", "—"),
            "weighted_score": scores.get("weighted_total", 0),
            "turnaround": turnaround,
            "risk_profile": risk_profile,
            "red_flag_count": flag_count,
            "escalation_required": rec.get("escalation_required", False),
        })
    return enriched


# ─── Recent Jobs List ─────────────────────────────────────────────────────────

@app.get("/api/jobs")
async def list_jobs(limit: int = 20):
    return await list_recent_jobs(limit=min(limit, 100))


# ─── WebSocket ────────────────────────────────────────────────────────────────

@app.websocket("/ws/{job_id}")
async def websocket_endpoint(websocket: WebSocket, job_id: str):
    """
    Stream live log updates to the frontend Pipeline page.
    Sends last known state on connect, then pushes updates as agents run.
    """
    await manager.connect(job_id, websocket)
    try:
        # Send current state immediately on connect
        state = await load_job(job_id)
        if state:
            await websocket.send_json({
                "type": "snapshot",
                "payload": {
                    "status": state.get("status"),
                    "agent_statuses": state.get("agent_statuses", {}),
                    "conflict_detected": state.get("conflict_detected", False),
                    "logs": state.get("logs", [])[-50:],
                },
            })

        # Keep alive — the pipeline pushes updates via manager.send_json
        while True:
            try:
                await asyncio.wait_for(websocket.receive_text(), timeout=30)
            except asyncio.TimeoutError:
                # Send ping to keep connection alive
                await websocket.send_json({"type": "ping"})
    except WebSocketDisconnect:
        manager.disconnect(job_id)
    except Exception:
        manager.disconnect(job_id)


# ─── Health ───────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "service": "intelli-credit-api"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
