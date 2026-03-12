"""
FastAPI application — Intelli-Credit Backend
Handles file uploads, orchestrates the multi-agent pipeline,
persists state in MongoDB, and streams live logs via WebSocket.
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

from motor.motor_asyncio import AsyncIOMotorClient
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
    ConfidenceLevel,
    DetectedDocument,
    UploadAndClassifyResponse,
    ConfirmedClassification,
    ConfirmClassificationRequest,
    ConfirmClassificationResponse,
    AlternativeClassification,
    DocumentSchemaMapping,
    SchemaSelectionRequest,
    SchemaSelectionResponse,
)
from modules.entity_onboarding import (
    EntityProfile,
    EntityProfileResponse,
    LoanApplication,
    LoanApplicationResponse,
    generate_entity_id,
    generate_application_id,
    get_required_documents,
    validate_entity_profile,
)
from tools.document_intelligence.document_classifier import (
    DocumentType,
    classify_document_type,
)
from tools.schema_mapper import (
    SchemaTemplate,
    SchemaMapper,
    SCHEMA_REGISTRY,
)

# ─── Config ───────────────────────────────────────────────────────────────────

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017/intelli_credit")
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "./uploads"))
MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "50"))
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# ─── MongoDB Client ───────────────────────────────────────────────────────────

mongo_client: Optional[AsyncIOMotorClient] = None
db = None


def get_db():
    """Get MongoDB database instance."""
    return db


# ─── DB Helpers ───────────────────────────────────────────────────────────────

async def init_db():
    """Initialize MongoDB connection and create indexes."""
    global mongo_client, db
    mongo_client = AsyncIOMotorClient(MONGODB_URI)
    db = mongo_client.get_database()  # Uses database from URI
    
    # Create indexes for better query performance
    await db.jobs.create_index("job_id", unique=True)
    await db.jobs.create_index([("created_at", -1)])
    await db.jobs.create_index("status")


async def close_db():
    """Close MongoDB connection."""
    if mongo_client:
        mongo_client.close()


async def save_job(job_id: str, state: Dict[str, Any]):
    """Save or update job state in MongoDB."""
    database = get_db()
    now = datetime.now().isoformat()
    
    job_data = {
        "job_id": job_id,
        "status": state.get("status", "QUEUED"),
        "company_name": state.get("company_name", ""),
        "sector": state.get("sector", ""),
        "state": state,
        "updated_at": now,
    }
    
    # Check if job exists
    existing = await database.jobs.find_one({"job_id": job_id})
    
    if existing:
        # Update existing job
        await database.jobs.update_one(
            {"job_id": job_id},
            {"$set": job_data}
        )
    else:
        # Insert new job
        job_data["created_at"] = now
        await database.jobs.insert_one(job_data)


async def load_job(job_id: str) -> Optional[Dict[str, Any]]:
    """Load job state from MongoDB."""
    database = get_db()
    job = await database.jobs.find_one({"job_id": job_id})
    
    if job:
        return job.get("state")
    return None


async def list_recent_jobs(limit: int = 20) -> List[Dict[str, Any]]:
    """Get list of recent jobs from MongoDB."""
    database = get_db()
    cursor = database.jobs.find().sort("created_at", -1).limit(limit)
    
    jobs = []
    async for job in cursor:
        jobs.append({
            "job_id": job.get("job_id"),
            "status": job.get("status"),
            "company_name": job.get("company_name"),
            "sector": job.get("sector"),
            "created_at": job.get("created_at"),
            "updated_at": job.get("updated_at"),
        })
    
    return jobs


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
    """Application lifespan manager - startup and shutdown."""
    await init_db()
    yield
    await close_db()

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
    """
    Background task: run the orchestrator and persist updates.
    
    Enhanced to support entity onboarding - loads entity_profile and loan_application
    from MongoDB if application_id is provided in initial_state.
    """
    
    # ─── Load Entity Profile & Loan Application (if available) ────────────────
    application_id = initial_state.get("application_id")
    if application_id:
        database = get_db()
        
        # Load loan application
        application_doc = await database.loan_applications.find_one({"application_id": application_id})
        if application_doc:
            initial_state["loan_application"] = application_doc.get("loan_application", {})
            initial_state["required_documents"] = application_doc.get("required_documents", [])
            
            # Load linked entity profile
            entity_id = application_doc.get("entity_id")
            if entity_id:
                entity_doc = await database.entity_profiles.find_one({"entity_id": entity_id})
                if entity_doc:
                    initial_state["entity_profile"] = entity_doc.get("profile", {})
                    
                    # Override/merge company_name and sector from entity profile if not set
                    if not initial_state.get("company_name"):
                        initial_state["company_name"] = entity_doc.get("profile", {}).get("company_name", "")
                    if not initial_state.get("sector"):
                        initial_state["sector"] = entity_doc.get("profile", {}).get("sector", "")
                    
                    # Add additional entity context for agents  
                    initial_state["cin"] = entity_doc.get("profile", {}).get("cin")
                    initial_state["pan"] = entity_doc.get("profile", {}).get("pan")
                    initial_state["annual_turnover"] = entity_doc.get("profile", {}).get("annual_turnover")

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

# ═══════════════════════════════════════════════════════════════════════════════
# ENTITY ONBOARDING ENDPOINTS (NEW)
# ═══════════════════════════════════════════════════════════════════════════════

@app.post("/api/onboarding/entity", response_model=EntityProfileResponse)
async def create_entity_profile(profile: EntityProfile):
    """
    Step 1: Create entity profile with CIN/PAN validation.
    Generates unique entity_id and saves to MongoDB.
    """
    # Generate unique entity ID
    entity_id = generate_entity_id()
    
    # Validate entity profile
    validations = validate_entity_profile(profile)
    
    # Check if validation passed
    validation_status = "validated"
    if any("invalid" in v.lower() for v in validations.values()):
        validation_status = "validation_failed"
    
    # Prepare document for MongoDB
    entity_data = {
        "entity_id": entity_id,
        "profile": profile.model_dump(),
        "validations": validations,
        "created_at": datetime.now().isoformat(),
        "status": validation_status,
    }
    
    # Save to MongoDB
    database = get_db()
    try:
        await database.entity_profiles.insert_one(entity_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    
    return EntityProfileResponse(
        entity_id=entity_id,
        status=validation_status,
        message="Entity profile created successfully" if validation_status == "validated" 
                else "Entity profile created with validation warnings",
        validations=validations
    )


@app.post("/api/onboarding/loan-application", response_model=LoanApplicationResponse)
async def create_loan_application(
    entity_id: str = Form(...),
    loan_type: str = Form(...),
    loan_amount: float = Form(...),
    loan_tenure_months: int = Form(...),
    expected_interest_rate: Optional[float] = Form(None),
    purpose: str = Form(...),
    collateral_offered: Optional[str] = Form(None),
    existing_banking_relationship: Optional[bool] = Form(False),
):
    """
    Step 2: Create loan application linked to entity profile.
    Returns context-aware required documents list based on loan_type.
    """
    # Validate entity exists
    database = get_db()
    entity = await database.entity_profiles.find_one({"entity_id": entity_id})
    
    if not entity:
        raise HTTPException(status_code=404, detail=f"Entity profile not found: {entity_id}")
    
    # Create loan application model
    try:
        loan_app = LoanApplication(
            loan_type=loan_type,
            loan_amount=loan_amount,
            loan_tenure_months=loan_tenure_months,
            expected_interest_rate=expected_interest_rate,
            purpose=purpose,
            collateral_offered=collateral_offered,
            existing_banking_relationship=existing_banking_relationship,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=f"Validation error: {str(e)}")
    
    # Generate application ID
    application_id = generate_application_id()
    
    # Get required documents based on loan type
    from modules.entity_onboarding import LoanType
    loan_type_enum = LoanType(loan_type)
    required_docs = get_required_documents(loan_type_enum)
    
    # Prepare application document
    application_data = {
        "application_id": application_id,
        "entity_id": entity_id,
        "loan_application": loan_app.model_dump(),
        "required_documents": required_docs,
        "status": "pending_documents",
        "created_at": datetime.now().isoformat(),
    }
    
    # Save to MongoDB
    try:
        await database.loan_applications.insert_one(application_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    
    return LoanApplicationResponse(
        application_id=application_id,
        entity_id=entity_id,
        status="pending_documents",
        message="Loan application submitted successfully",
        next_step="document_upload",
        required_documents=required_docs
    )


@app.get("/api/onboarding/entity/{entity_id}")
async def get_entity_profile(entity_id: str):
    """Retrieve entity profile by ID"""
    database = get_db()
    entity = await database.entity_profiles.find_one({"entity_id": entity_id})
    
    if not entity:
        raise HTTPException(status_code=404, detail=f"Entity profile not found: {entity_id}")
    
    # Remove MongoDB _id field
    entity.pop("_id", None)
    return entity


@app.get("/api/onboarding/application/{application_id}")
async def get_loan_application(application_id: str):
    """Retrieve loan application by ID"""
    database = get_db()
    application = await database.loan_applications.find_one({"application_id": application_id})
    
    if not application:
        raise HTTPException(status_code=404, detail=f"Loan application not found: {application_id}")
    
    # Remove MongoDB _id field
    application.pop("_id", None)
    return application


# ═══════════════════════════════════════════════════════════════════════════════
# DOCUMENT CLASSIFICATION REVIEW ENDPOINTS (HUMAN-IN-THE-LOOP)
# ═══════════════════════════════════════════════════════════════════════════════

@app.post("/api/documents/upload-and-classify", response_model=UploadAndClassifyResponse)
async def upload_and_classify_documents(
    application_id: str = Form(...),
    files: List[UploadFile] = File(...),
):
    """
    Upload documents and classify them using AI with confidence scoring.
    Returns classification results for user review before pipeline execution.
    
    This implements the human-in-the-loop workflow for the hackathon.
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded")
    
    # Create upload directory for this application
    app_upload_dir = UPLOAD_DIR / application_id
    app_upload_dir.mkdir(parents=True, exist_ok=True)
    
    detected_documents = []
    auto_accept_count = 0
    review_required_count = 0
    
    for idx, upload_file in enumerate(files):
        if not upload_file.filename:
            continue
        
        # Validate file size
        content = await upload_file.read()
        size_mb = len(content) / (1024 * 1024)
        if size_mb > MAX_FILE_SIZE_MB:
            raise HTTPException(
                status_code=413,
                detail=f"{upload_file.filename} exceeds {MAX_FILE_SIZE_MB}MB limit.",
            )
        
        # Save file to disk
        safe_name = upload_file.filename.replace("/", "_").replace("\\", "_")
        file_path = app_upload_dir / safe_name
        with open(file_path, "wb") as f:
            f.write(content)
        
        # Generate file ID
        file_id = f"DOC_{application_id}_{idx+1:03d}"
        
        # Extract text for classification (simplified - in production would use PDF parser)
        try:
            if upload_file.filename.lower().endswith(".pdf"):
                # Import here to avoid circular dependency
                from tools.pdf_parser import extract_text_from_pdf
                
                text = extract_text_from_pdf(str(file_path))
            else:
                text = content.decode('utf-8', errors='ignore')
        except Exception as e:
            logger.warning(f"Failed to extract text from {upload_file.filename}: {e}")
            text = ""
        
        # Classify document using extended classifier
        try:
            doc_type, confidence, reasoning, alternatives = classify_document_type(
                text=text,
                filename=upload_file.filename,
                tables=None,
                metadata=None
            )
            
            # Determine confidence level
            if confidence >= 0.70:
                confidence_label = ConfidenceLevel.HIGH
                requires_review = False
                auto_accept_count += 1
            elif confidence >= 0.50:
                confidence_label = ConfidenceLevel.MEDIUM
                requires_review = True
                review_required_count += 1
            else:
                confidence_label = ConfidenceLevel.LOW
                requires_review = True
                review_required_count += 1
            
            # Format alternatives
            alternative_classifications = [
                AlternativeClassification(type=alt_type.value, confidence=alt_conf)
                for alt_type, alt_conf in alternatives
            ]
            
            detected_doc = DetectedDocument(
                file_id=file_id,
                file_name=upload_file.filename,
                file_size=len(content),
                auto_classification=doc_type.value if doc_type else "UNKNOWN",
                confidence=round(confidence, 3),
                confidence_label=confidence_label,
                user_override_allowed=True,
                classification_reasoning=reasoning,
                alternative_classifications=alternative_classifications,
                requires_review=requires_review
            )
            
            detected_documents.append(detected_doc)
            
            logger.info(
                f"Classified {upload_file.filename} as {doc_type.value if doc_type else 'UNKNOWN'} "
                f"with confidence {confidence:.2f}"
            )
            
        except Exception as e:
            logger.error(f"Classification error for {upload_file.filename}: {e}")
            # Fallback to UNKNOWN
            detected_doc = DetectedDocument(
                file_id=file_id,
                file_name=upload_file.filename,
                file_size=len(content),
                auto_classification="UNKNOWN",
                confidence=0.35,
                confidence_label=ConfidenceLevel.LOW,
                user_override_allowed=True,
                classification_reasoning="Classification failed - manual review required",
                alternative_classifications=[],
                requires_review=True
            )
            detected_documents.append(detected_doc)
            review_required_count += 1
    
    # Determine if user review is required
    requires_user_review = review_required_count > 0
    
    # Save file ID to filename mapping for later retrieval
    mapping_file = app_upload_dir / ".file_mapping.json"
    file_mapping = {
        doc.file_id: doc.file_name
        for doc in detected_documents
    }
    with open(mapping_file, "w") as f:
        json.dump(file_mapping, f, indent=2)
    
    return UploadAndClassifyResponse(
        application_id=application_id,
        detected_documents=detected_documents,
        requires_user_review=requires_user_review,
        auto_accept_count=auto_accept_count,
        review_required_count=review_required_count
    )


@app.post("/api/documents/confirm-classification", response_model=ConfirmClassificationResponse)
async def confirm_document_classification(
    request: ConfirmClassificationRequest,
    background_tasks: BackgroundTasks,
):
    """
    Confirm document classifications and start the appraisal pipeline.
    
    This endpoint receives user-confirmed classifications (with potential overrides)
    and triggers the background pipeline execution.
    """
    application_id = request.application_id
    
    # Load application data
    database = get_db()
    application = await database.loan_applications.find_one({"application_id": application_id})
    
    if not application:
        raise HTTPException(status_code=404, detail=f"Application not found: {application_id}")
    
    # Load entity profile
    entity_id = application.get("entity_id")
    entity = None
    if entity_id:
        entity = await database.entity_profiles.find_one({"entity_id": entity_id})
    
    # Generate job ID for pipeline
    job_id = str(uuid.uuid4())
    
    # Build document classifications mapping
    document_classifications = {}
    for classification in request.classifications:
        document_classifications[classification.file_id] = {
            "confirmed_type": classification.confirmed_type,
            "user_modified": classification.user_modified,
            "user_comment": classification.user_comment,
            "confirmed_at": datetime.now().isoformat()
        }
    
    # Load uploaded files from disk
    app_upload_dir = UPLOAD_DIR / application_id
    if not app_upload_dir.exists():
        raise HTTPException(status_code=404, detail="No documents found for this application")
    
    # Load file ID to filename mapping
    mapping_file = app_upload_dir / ".file_mapping.json"
    file_mapping = {}
    if mapping_file.exists():
        with open(mapping_file, "r") as f:
            file_mapping = json.load(f)
    
    documents = []
    for classification in request.classifications:
        file_id = classification.file_id
        confirmed_type = classification.confirmed_type
        
        # Get filename from mapping
        filename = file_mapping.get(file_id)
        if not filename:
            logger.warning(f"No filename found for file_id {file_id}, skipping")
            continue
        
        file_path = app_upload_dir / filename
        if not file_path.exists():
            logger.warning(f"File not found: {file_path}")
            continue
        
        # Parse document using standard pipeline
        try:
            from tools.pdf_parser import parse_with_intelligence
            
            parsed = parse_with_intelligence(
                str(file_path),
                confirmed_type.lower(),  # Use confirmed type
                use_advanced_pipeline=True
            )
            
            # Add classification metadata
            parsed["confirmed_classification"] = confirmed_type
            parsed["file_id"] = file_id
            parsed["filename"] = filename  # Add filename for reference
            
            documents.append(parsed)
            
        except Exception as e:
            logger.error(f"Failed to parse {file_path}: {e}")
            continue
    
    # Build initial state for pipeline
    initial_state = {
        "job_id": job_id,
        "application_id": application_id,
        "company_name": entity.get("profile", {}).get("company_name", "") if entity else "",
        "sector": entity.get("profile", {}).get("sector", "") if entity else "",
        "loan_amount_requested": application.get("loan_application", {}).get("loan_amount", 0.0),
        "documents": documents,
        "document_classifications": document_classifications,  # Store confirmed classifications
        "selected_schemas": application.get("selected_schemas", {}),  # Schema selections from /api/schemas/select
        "qualitative_inputs": request.qualitative_inputs or {},  # Store qualitative due diligence inputs
        "entity_profile": entity.get("profile", {}) if entity else {},
        "loan_application": application.get("loan_application", {}),
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
                "message": f"Classifications confirmed. {len(documents)} document(s) ready for analysis.",
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
    
    # Save job state
    await save_job(job_id, initial_state)
    
    # Start pipeline in background
    background_tasks.add_task(_run_pipeline, job_id, initial_state)
    
    return ConfirmClassificationResponse(
        status="pipeline_started",
        job_id=job_id,
        websocket_url=f"/ws/{job_id}"
    )


# ═══════════════════════════════════════════════════════════════════════════════
# SCHEMA CONFIGURATION ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/api/schemas/list")
async def list_schemas():
    """
    Get all available schema templates.
    Returns complete template definitions with fields and metadata.
    """
    return {
        "schemas": [
            {
                "template_id": template.template_id,
                "template_name": template.template_name,
                "description": template.description,
                "applicable_document_types": template.applicable_document_types,
                "field_count": len(template.fields),
                "fields": [
                    {
                        "field_name": field.field_name,
                        "field_label": field.field_label,
                        "data_type": field.data_type,
                        "required": field.required,
                        "description": field.description,
                        "extraction_hints": field.extraction_hints,
                    }
                    for field in template.fields
                ],
                "version": template.version,
            }
            for template in SCHEMA_REGISTRY.values()
        ]
    }


@app.get("/api/schemas/recommend")
async def recommend_schemas(document_type: str):
    """
    Get recommended schema templates for a specific document type.
    Returns schemas in priority order.
    
    Query Parameters:
        document_type: The DocumentType enum value (e.g., "ALM", "FINANCIAL_STATEMENT")
    """
    recommendations = SchemaMapper.get_recommended_schema(document_type)
    
    return {
        "document_type": document_type,
        "recommendations": [
            {
                "template_id": template.template_id,
                "template_name": template.template_name,
                "description": template.description,
                "field_count": len(template.fields),
                "applicable_document_types": template.applicable_document_types,
                "fields": [
                    {
                        "field_name": field.field_name,
                        "field_label": field.field_label,
                        "data_type": field.data_type,
                        "required": field.required,
                        "description": field.description,
                        "extraction_hints": field.extraction_hints,
                    }
                    for field in template.fields
                ],
            }
            for template in recommendations
        ],
    }


@app.post("/api/schemas/select", response_model=SchemaSelectionResponse)
async def select_schemas(request: SchemaSelectionRequest):
    """
    Save user's schema selections for their documents.
    This configures which schema template to use for extracting data from each document.
    
    The selected schemas are stored in the application record and will be used
    during the extraction phase of the pipeline.
    """
    application_id = request.application_id
    
    # Load application
    database = get_db()
    application = await database.loan_applications.find_one({"application_id": application_id})
    
    if not application:
        raise HTTPException(status_code=404, detail=f"Application not found: {application_id}")
    
    # Build schema configuration mapping
    schema_config = {}
    for mapping in request.document_schema_mapping:
        # Validate schema exists
        if mapping.selected_schema_id not in SCHEMA_REGISTRY:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid schema ID: {mapping.selected_schema_id}"
            )
        
        schema_config[mapping.file_id] = {
            "schema_id": mapping.selected_schema_id,
            "schema_name": SCHEMA_REGISTRY[mapping.selected_schema_id].template_name,
            "custom_hints": mapping.custom_hints or {},
            "configured_at": datetime.now().isoformat()
        }
    
    # Save to application document
    await database.loan_applications.update_one(
        {"application_id": application_id},
        {
            "$set": {
                "selected_schemas": schema_config,
                "schemas_configured_at": datetime.now().isoformat()
            }
        }
    )
    
    return SchemaSelectionResponse(
        status="schemas_configured",
        application_id=application_id,
        schemas_count=len(schema_config)
    )


# ═══════════════════════════════════════════════════════════════════════════════
# EXISTING APPRAISAL ENDPOINTS (UPDATED TO SUPPORT ENTITY ONBOARDING)
# ═══════════════════════════════════════════════════════════════════════════════

@app.post("/api/appraisal/start", response_model=AppraisalStartResponse)
async def start_appraisal(
    background_tasks: BackgroundTasks,
    application_id: Optional[str] = Form(None),  # NEW: Link to entity onboarding
    company_name: str = Form(...),
    sector: str = Form(...),
    loan_amount: float = Form(0.0),
    qualitative_notes: str = Form(""),
    qualitative_inputs: str = Form("{}"),
    annual_report: Optional[UploadFile] = File(None),
    gst_returns: Optional[UploadFile] = File(None),
    bank_statements: Optional[UploadFile] = File(None),
    itr: Optional[UploadFile] = File(None),
    legal_documents: Optional[UploadFile] = File(None),
    mca_filings: Optional[UploadFile] = File(None),
    rating_report: Optional[UploadFile] = File(None),
    cibil_report: Optional[UploadFile] = File(None),
    shareholding: Optional[UploadFile] = File(None),
    sanction_letters: Optional[UploadFile] = File(None),
    audited_financials: Optional[UploadFile] = File(None),
):
    """
    Accept multipart form with up to 11 document uploads and qualitative assessments.
    Kick off the appraisal pipeline as a background task.
    """
    job_id = str(uuid.uuid4())
    job_dir = UPLOAD_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    # Parse qualitative inputs
    try:
        qualitative_data = json.loads(qualitative_inputs) if qualitative_inputs else {}
    except json.JSONDecodeError:
        qualitative_data = {}

    # ── Save uploaded files ───────────────────────────────────────────────────
    upload_mapping = {
        "annual_report": annual_report,
        "gst_returns": gst_returns,
        "bank_statements": bank_statements,
        "itr": itr,
        "legal_documents": legal_documents,
        "mca_filings": mca_filings,
        "rating_report": rating_report,
        "cibil_report": cibil_report,
        "shareholding": shareholding,
        "sanction_letters": sanction_letters,
        "audited_financials": audited_financials,
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

        # Parse document using Advanced Document Intelligence Pipeline
        if upload_file.filename.lower().endswith(".pdf"):
            from tools.pdf_parser import parse_with_intelligence
            
            logger.info(f"Processing {safe_name} with advanced document intelligence pipeline")
            parsed = parse_with_intelligence(
                str(file_path), 
                doc_type,
                use_advanced_pipeline=True
            )
            
            # ── Confidence Threshold Gating ──────────────────────────────────
            overall_conf = parsed.get("overall_confidence", 1.0)
            reliability = parsed.get("reliability_score", "UNKNOWN")
            
            # Determine document status based on confidence
            if overall_conf >= 0.7:
                parsed["extraction_status"] = "ACCEPTED"
                parsed["confidence_warning"] = None
                logger.info(f"✓ {safe_name}: High confidence ({overall_conf:.1%}, {reliability})")
            
            elif 0.5 <= overall_conf < 0.7:
                parsed["extraction_status"] = "ACCEPTED_WITH_WARNING"
                parsed["confidence_warning"] = (
                    f"This document has moderate extraction confidence ({overall_conf:.0%}). "
                    f"Some financial metrics may require manual verification."
                )
                logger.warning(
                    f"⚠ {safe_name}: Moderate confidence ({overall_conf:.1%}, {reliability}) - "
                    f"accepted with warning"
                )
                
                # Send WebSocket notification
                if connection_id:
                    await manager.send_json(
                        connection_id,
                        {
                            "type": "document_quality_warning",
                            "document": safe_name,
                            "confidence": round(overall_conf, 3),
                            "reliability": reliability,
                            "message": "Moderate quality - manual verification recommended"
                        }
                    )
            
            else:  # confidence < 0.5
                parsed["extraction_status"] = "REQUIRES_REVIEW"
                parsed["confidence_warning"] = (
                    f"This document has low extraction confidence ({overall_conf:.0%}). "
                    f"Manual data entry is strongly recommended."
                )
                parsed["requires_manual_review"] = True
                
                logger.error(
                    f"✗ {safe_name}: Low confidence ({overall_conf:.1%}, {reliability}) - "
                    f"flagged for manual review"
                )
                
                # Send WebSocket alert
                if connection_id:
                    await manager.send_json(
                        connection_id,
                        {
                            "type": "document_quality_alert",
                            "document": safe_name,
                            "confidence": round(overall_conf, 3),
                            "reliability": reliability,
                            "message": "Low quality detected - manual review required",
                            "warnings": parsed.get("validation", {}).get("warnings", [])
                        }
                    )
            
            # Log validation issues if present
            validation = parsed.get("validation", {})
            if validation.get("flags"):
                logger.warning(
                    f"Validation flags for {safe_name}: "
                    f"{len(validation['flags'])} issue(s) detected"
                )
        
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
                "overall_confidence": 0.0,
                "reliability_score": "MANUAL",
                "extraction_status": "MANUAL_ENTRY_REQUIRED",
                "requires_manual_review": True,
            }

        documents.append(parsed)

    # ── Build initial state ───────────────────────────────────────────────────
    initial_state: Dict[str, Any] = {
        "job_id": job_id,
        "application_id": application_id,  # Link to entity onboarding if provided
        "company_name": company_name.strip(),
        "sector": sector.strip(),
        "loan_amount_requested": loan_amount,
        "qualitative_notes": qualitative_notes.strip(),
        "qualitative_inputs": qualitative_data,
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
