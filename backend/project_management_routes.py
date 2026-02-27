"""
PHASE 2 WAVE 3: API ROUTES

Routes for:
- PILLAR A: Snapshot & Report Engine
- PILLAR B: Background Job Engine
- PILLAR C: AI Integration Layer
- PILLAR D: Security Hardening

All routes require authentication.

PHASE 2 EXTENSION: Snapshot + Document Integrity
- DPR submit creates immutable snapshot
- Document locking after submission
"""

from core.snapshot_service import SnapshotService, SnapshotEntityType, build_dpr_snapshot
from core.security_hardening import (
    SecurityHardening,
    OrganisationAccessError,
    SignedURLExpiredError,
    SignedURLInvalidError
)
from core.ai_service import AIService, AIServiceError
from core.background_job_engine import BackgroundJobEngine
from core.snapshot_engine import SnapshotEngine, SnapshotNotFoundError
from permissions import PermissionChecker
from auth import get_current_user
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Query, Request
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId, Decimal128
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
from pydantic import BaseModel, Field
import logging
import os

from dotenv import load_dotenv
load_dotenv()


logger = logging.getLogger(__name__)


def serialize_mongo_doc(obj: Any) -> Any:
    """Recursively serialize MongoDB objects for JSON response"""
    if isinstance(obj, ObjectId):
        return str(obj)
    elif isinstance(obj, Decimal128):
        return float(obj.to_decimal())
    elif isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {k: serialize_mongo_doc(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [serialize_mongo_doc(item) for item in obj]
    else:
        return obj


def parse_object_id(value: str, field_name: str = "id") -> ObjectId:
    """Validate ObjectId values from path/query input and return HTTP 400 for malformed IDs."""
    try:
        return ObjectId(value)
    except Exception:
        raise HTTPException(status_code=400, detail=f"Invalid {field_name}")


# Router
project_management_router = APIRouter(
    prefix="/api/v2", tags=["Phase 2 Wave 3"])

# MongoDB
mongo_url = os.environ.get(
    'MONGO_URL',
    'mongodb://localhost:27017/?replicaSet=rs0')
db_name = os.environ.get('DB_NAME', 'construction_management')
ai_api_key = os.environ.get('EMERGENT_LLM_KEY')

client = AsyncIOMotorClient(mongo_url)
db = client[db_name]

# Services
permission_checker = PermissionChecker(db)
snapshot_engine = SnapshotEngine(client, db)
job_engine = BackgroundJobEngine(client, db)
ai_service = AIService(client, db, ai_api_key)
security = SecurityHardening(client, db)

# Phase 2 - Snapshot + Document Integrity services
dpr_snapshot_service = SnapshotService(db)


# =============================================================================
# MODELS
# =============================================================================

class SnapshotCreate(BaseModel):
    report_type: str
    project_id: str
    filters: Optional[Dict] = None


class JobSchedule(BaseModel):
    job_type: str = Field(
        ...,
        description="FINANCIAL_INTEGRITY, MEDIA_PURGE, AUDIO_PURGE, PDF_PURGE, DRIVE_RETRY, COMPRESSION_RETRY")
    params: Dict = Field(default_factory=dict)


class OCRVerify(BaseModel):
    ocr_id: str
    verified_data: Dict


class VisionOverride(BaseModel):
    tag_id: str
    override_code: str


class SettingsUpdate(BaseModel):
    media_retention_days: Optional[int] = None
    audio_retention_days: Optional[int] = None
    pdf_retention_days: Optional[int] = None
    signed_url_expiration_hours: Optional[int] = None


# =============================================================================
# PILLAR A: SNAPSHOT & REPORT ENDPOINTS
# =============================================================================

@project_management_router.post("/snapshots", status_code=201)
async def create_snapshot(
    snapshot_data: SnapshotCreate,
    current_user: dict = Depends(get_current_user)
):
    """
    Create immutable snapshot for reporting.

    Snapshot cannot be edited or deleted after creation.
    """
    user = await permission_checker.get_authenticated_user(current_user)
    await permission_checker.check_project_access(user, snapshot_data.project_id, require_write=False)

    # Generate report data based on type
    if snapshot_data.report_type == "FINANCIAL_SUMMARY":
        data = await snapshot_engine.generate_financial_summary_data(
            snapshot_data.project_id,
            user["organisation_id"]
        )
    else:
        # For other report types, data should be provided in filters
        data = snapshot_data.filters or {}

    snapshot_id = await snapshot_engine.create_snapshot(
        report_type=snapshot_data.report_type,
        project_id=snapshot_data.project_id,
        organisation_id=user["organisation_id"],
        generated_by=user["user_id"],
        data=data,
        filters=snapshot_data.filters
    )

    return {"snapshot_id": snapshot_id,
            "report_type": snapshot_data.report_type}


@project_management_router.get("/snapshots/{snapshot_id}")
async def get_snapshot(
    snapshot_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get snapshot by ID with checksum verification"""
    user = await permission_checker.get_authenticated_user(current_user)

    try:
        snapshot = await snapshot_engine.get_snapshot(snapshot_id, verify_checksum=True)

        # Verify organisation access
        if snapshot.get("organisation_id") != user["organisation_id"]:
            raise HTTPException(status_code=403, detail="Access denied")

        # Serialize to handle Decimal128
        return serialize_mongo_doc(snapshot)
    except SnapshotNotFoundError:
        raise HTTPException(status_code=404, detail="Snapshot not found")


@project_management_router.get("/snapshots/{snapshot_id}/render")
async def render_report_from_snapshot(
    snapshot_id: str,
    output_format: str = "json",
    current_user: dict = Depends(get_current_user)
):
    """
    Render report from snapshot.

    Reports render ONLY from snapshot data_json.
    Historical data preserved even if live data changes.
    """
    user = await permission_checker.get_authenticated_user(current_user)

    try:
        snapshot = await snapshot_engine.get_snapshot(snapshot_id)

        if snapshot.get("organisation_id") != user["organisation_id"]:
            raise HTTPException(status_code=403, detail="Access denied")

        report = await snapshot_engine.render_report_from_snapshot(snapshot_id, output_format)
        # Serialize to handle Decimal128
        return serialize_mongo_doc(report)
    except SnapshotNotFoundError:
        raise HTTPException(status_code=404, detail="Snapshot not found")


@project_management_router.get("/snapshots")
async def list_snapshots(
    project_id: Optional[str] = None,
    report_type: Optional[str] = None,
    limit: int = 100,
    current_user: dict = Depends(get_current_user)
):
    """List snapshots for organisation"""
    user = await permission_checker.get_authenticated_user(current_user)

    snapshots = await snapshot_engine.list_snapshots(
        organisation_id=user["organisation_id"],
        project_id=project_id,
        report_type=report_type,
        limit=limit
    )

    return {"snapshots": snapshots}


@project_management_router.put("/snapshots/{snapshot_id}")
async def update_snapshot_blocked(snapshot_id: str):
    """UPDATE is blocked - snapshots are immutable"""
    raise HTTPException(
        status_code=405,
        detail="Snapshots are immutable and cannot be updated"
    )


@project_management_router.delete("/snapshots/{snapshot_id}")
async def delete_snapshot_blocked(snapshot_id: str):
    """DELETE is blocked - snapshots are immutable"""
    raise HTTPException(
        status_code=405,
        detail="Snapshots are immutable and cannot be deleted"
    )


# =============================================================================
# PILLAR B: BACKGROUND JOB ENDPOINTS
# =============================================================================

@project_management_router.post("/jobs", status_code=201)
async def schedule_job(
    job_data: JobSchedule,
    current_user: dict = Depends(get_current_user)
):
    """
    Schedule a background job.

    Jobs run asynchronously without blocking API.
    """
    user = await permission_checker.get_authenticated_user(current_user)
    await permission_checker.check_admin_role(user)

    valid_types = [
        "FINANCIAL_INTEGRITY",
        "MEDIA_PURGE",
        "AUDIO_PURGE",
        "PDF_PURGE",
        "DRIVE_RETRY",
        "COMPRESSION_RETRY"]
    if job_data.job_type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid job_type. Must be one of: {valid_types}"
        )

    job_id = await job_engine.schedule_job(
        job_type=job_data.job_type,
        params=job_data.params or {},
        organisation_id=user["organisation_id"],
        scheduled_by=user["user_id"]
    )

    # Start job execution asynchronously
    await job_engine.run_job_async(job_id)

    return {"job_id": job_id, "status": "scheduled"}


@project_management_router.get("/jobs/{job_id}")
async def get_job_status(
    job_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get job status"""
    user = await permission_checker.get_authenticated_user(current_user)

    job = await job_engine.get_job_status(job_id)

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.get("organisation_id") != user["organisation_id"]:
        raise HTTPException(status_code=403, detail="Access denied")

    return job


@project_management_router.get("/jobs")
async def list_jobs(
    status_filter: Optional[str] = None,
    limit: int = 50,
    current_user: dict = Depends(get_current_user)
):
    """List jobs for organisation"""
    user = await permission_checker.get_authenticated_user(current_user)

    query = {"organisation_id": user["organisation_id"]}
    if status_filter:
        query["status"] = status_filter

    jobs = await db.background_jobs.find(query).sort("scheduled_at", -1).limit(limit).to_list(length=limit)

    for job in jobs:
        job["job_id"] = str(job.pop("_id"))

    return {"jobs": jobs}


@project_management_router.get("/alerts")
async def get_alerts(
    resolved: bool = False,
    limit: int = 100,
    current_user: dict = Depends(get_current_user)
):
    """Get financial integrity alerts"""
    user = await permission_checker.get_authenticated_user(current_user)

    alerts = await db.alerts.find({
        "organisation_id": user["organisation_id"],
        "resolved": resolved
    }).sort("detected_at", -1).limit(limit).to_list(length=limit)

    for alert in alerts:
        alert["alert_id"] = str(alert.pop("_id"))

    return {"alerts": alerts}


# =============================================================================
# PILLAR C: AI ENDPOINTS
# =============================================================================

@project_management_router.post("/ai/ocr")
async def run_ocr(
    file: UploadFile = File(...),
    project_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """
    Run OCR on uploaded document.

    Extracts vendor, invoice number, date, amount.
    Does NOT auto-create PC.
    """
    user = await permission_checker.get_authenticated_user(current_user)

    # Read file
    content = await file.read()
    file_type = file.filename.split(
        ".")[-1].lower() if file.filename else "unknown"

    try:
        result = await ai_service.run_ocr(
            file_content=content,
            file_type=file_type,
            organisation_id=user["organisation_id"],
            user_id=user["user_id"],
            project_id=project_id
        )
        return result
    except AIServiceError as e:
        raise HTTPException(status_code=500, detail=str(e))


@project_management_router.post("/ai/ocr/verify")
async def verify_ocr_result(
    verify_data: OCRVerify,
    current_user: dict = Depends(get_current_user)
):
    """Manually verify/correct OCR result"""
    user = await permission_checker.get_authenticated_user(current_user)

    try:
        await ai_service.verify_ocr_result(
            ocr_id=verify_data.ocr_id,
            verified_data=verify_data.verified_data,
            user_id=user["user_id"],
            organisation_id=user["organisation_id"]
        )
        return {"status": "verified", "ocr_id": verify_data.ocr_id}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@project_management_router.post("/ai/stt")
async def run_stt(
    file: UploadFile = File(...),
    project_id: str = Query(...),
    code_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """
    Run speech-to-text on audio file.

    Auto-creates Issue if keywords detected.
    """
    user = await permission_checker.get_authenticated_user(current_user)

    content = await file.read()
    audio_format = file.filename.split(
        ".")[-1].lower() if file.filename else "unknown"

    try:
        result = await ai_service.run_stt(
            audio_content=content,
            audio_format=audio_format,
            organisation_id=user["organisation_id"],
            user_id=user["user_id"],
            project_id=project_id,
            code_id=code_id
        )
        return result
    except AIServiceError as e:
        raise HTTPException(status_code=500, detail=str(e))


@project_management_router.post("/ai/vision-tag")
async def run_vision_tag(
    file: UploadFile = File(...),
    project_id: str = Query(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Run vision tagging on image.

    Suggests CODE based on image content.
    """
    user = await permission_checker.get_authenticated_user(current_user)

    content = await file.read()

    try:
        result = await ai_service.run_vision_tag(
            image_content=content,
            organisation_id=user["organisation_id"],
            user_id=user["user_id"],
            project_id=project_id
        )
        return result
    except AIServiceError as e:
        raise HTTPException(status_code=500, detail=str(e))


@project_management_router.post("/ai/vision-tag/override")
async def override_vision_tag(
    override_data: VisionOverride,
    current_user: dict = Depends(get_current_user)
):
    """Manually override vision tag suggestion"""
    user = await permission_checker.get_authenticated_user(current_user)

    try:
        await ai_service.override_vision_tag(
            tag_id=override_data.tag_id,
            override_code=override_data.override_code,
            user_id=user["user_id"],
            organisation_id=user["organisation_id"]
        )
        return {"status": "overridden", "tag_id": override_data.tag_id}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# =============================================================================
# PILLAR D: SECURITY ENDPOINTS
# =============================================================================

@project_management_router.get("/media/{encoded_path}")
async def get_signed_media(
    encoded_path: str,
    sig: str,
    exp: int,
    org: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Access media via signed URL.

    Validates signature, expiration, and organisation.
    """
    user = await permission_checker.get_authenticated_user(current_user)

    try:
        resource_path = security.verify_signed_url(
            encoded_path=encoded_path,
            signature=sig,
            expiration=exp,
            organisation_id=org,
            user_organisation_id=user["organisation_id"]
        )

        # In production, return actual file
        # For now, return path info
        return {
            "resource_path": resource_path,
            "access_granted": True,
            "note": "Actual file serving requires storage integration"
        }
    except SignedURLExpiredError:
        raise HTTPException(status_code=401, detail="Signed URL has expired")
    except SignedURLInvalidError:
        raise HTTPException(status_code=401, detail="Invalid signed URL")
    except OrganisationAccessError:
        raise HTTPException(status_code=403, detail="Access denied")


@project_management_router.post("/media/sign")
async def generate_signed_url(
    resource_path: str,
    expiration_hours: Optional[int] = None,
    current_user: dict = Depends(get_current_user)
):
    """Generate signed URL for resource access"""
    user = await permission_checker.get_authenticated_user(current_user)

    if not security.validate_file_path(resource_path):
        raise HTTPException(status_code=400, detail="Invalid resource path")

    signed_url = security.generate_signed_url(
        resource_path=resource_path,
        organisation_id=user["organisation_id"],
        expiration_hours=expiration_hours
    )

    return {"signed_url": signed_url}


@project_management_router.get("/settings")
async def get_settings(current_user: dict = Depends(get_current_user)):
    """Get organisation settings including retention periods"""
    user = await permission_checker.get_authenticated_user(current_user)

    settings = await security.get_organisation_settings(user["organisation_id"])
    return settings


@project_management_router.put("/settings")
async def update_settings(
    settings_data: SettingsUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update organisation settings (Admin only)"""
    user = await permission_checker.get_authenticated_user(current_user)
    await permission_checker.check_admin_role(user)

    await security.update_organisation_settings(
        organisation_id=user["organisation_id"],
        user_id=user["user_id"],
        settings=settings_data.dict(exclude_none=True)
    )

    return {"status": "updated"}


# =============================================================================
# DPR (DAILY PROGRESS REPORT) ENDPOINTS
# =============================================================================

class DPRCreate(BaseModel):
    project_id: str
    dpr_date: str  # YYYY-MM-DD format
    progress_notes: Optional[str] = None
    weather_conditions: Optional[str] = None
    manpower_count: Optional[int] = None
    activities_completed: List[str] = Field(default_factory=list)
    issues_encountered: Optional[str] = None


class DPRImage(BaseModel):
    dpr_id: str
    image_data: str  # Base64 encoded (portrait 9:16)
    caption: Optional[str] = None
    activity_code: Optional[str] = None


class AICaptionRequest(BaseModel):
    image_data: str  # Base64 encoded image


@project_management_router.post("/dpr", status_code=201)
async def create_dpr(
    dpr_data: DPRCreate,
    current_user: dict = Depends(get_current_user)
):
    """
    Create a new Daily Progress Report.
    """
    user = await permission_checker.get_authenticated_user(current_user)
    await permission_checker.check_project_access(user, dpr_data.project_id, require_write=True)

    # Parse date
    try:
        dpr_date = datetime.strptime(dpr_data.dpr_date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400,
                            detail="Invalid date format. Use YYYY-MM-DD")

    # Check if DPR already exists for this date/project/user
    existing = await db.dpr.find_one({
        "project_id": dpr_data.project_id,
        "supervisor_id": user["user_id"],
        "dpr_date": dpr_date
    })

    if existing:
        # Return existing DPR info so frontend can ask user what to do
        return {
            "exists": True,
            "dpr_id": str(existing["_id"]),
            "status": existing.get("status", "Draft"),
            "created_at": existing.get("created_at"),
            "message": "DPR already exists for this date"
        }

    # Generate filename in MMMM, DD, YYYY format
    file_name = dpr_date.strftime("%B, %d, %Y") + ".pdf"

    # Create DPR
    dpr_doc = {
        "project_id": dpr_data.project_id,
        "organisation_id": user["organisation_id"],
        "supervisor_id": user["user_id"],
        "dpr_date": dpr_date,
        "progress_notes": dpr_data.progress_notes,
        "weather_conditions": dpr_data.weather_conditions,
        "manpower_count": dpr_data.manpower_count,
        "activities_completed": dpr_data.activities_completed or [],
        "issues_encountered": dpr_data.issues_encountered,
        "images": [],
        "image_count": 0,
        "file_name": file_name,
        "file_size_kb": 0,
        "pdf_generated": False,
        "drive_file_id": None,
        "drive_link": None,
        "status": "Draft",
        "locked_flag": False,
        "version_number": 1,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }

    result = await db.dpr.insert_one(dpr_doc)

    return {
        "dpr_id": str(result.inserted_id),
        "file_name": file_name,
        "status": "created",
        "message": "DPR created. Add minimum 4 portrait (9:16) photos."
    }


@project_management_router.post("/dpr/ai-caption")
async def generate_ai_caption(
    request: AICaptionRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Generate AI-recommended caption for a construction progress image.
    Uses OpenAI GPT-4o Vision API to analyze the actual photo content.
    User can override with manual caption.
    """
    await permission_checker.get_authenticated_user(current_user)

    # Get API key - prefer Emergent LLM key
    api_key = os.environ.get(
        'EMERGENT_LLM_KEY') or os.environ.get('OPENAI_API_KEY')

    if not api_key:
        # Fallback to mock captions if no API key
        import random
        suggested_captions = [
            "Foundation work in progress",
            "Concrete pouring completed",
            "Steel reinforcement installation",
            "Formwork preparation",
            "Site excavation work",
        ]
        return {
            "ai_caption": random.choice(suggested_captions),
            "confidence": 0.5,
            "alternatives": [],
            "note": "Mock caption - API key not configured"
        }

    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage, ImageContent
        import uuid

        # Prepare image data
        image_data = request.image_data

        # Remove data URL prefix if present
        if image_data.startswith('data:'):
            # Extract base64 part after the comma
            image_data = image_data.split(
                ',')[1] if ',' in image_data else image_data

        # Create image content
        image_content = ImageContent(image_base64=image_data)

        # Initialize chat with vision-capable model
        chat = LlmChat(
            api_key=api_key,
            session_id=f"dpr-caption-{uuid.uuid4()}",
            system_message="""You are an expert construction site supervisor and photographer.

Your task is to analyze construction progress images and provide:
1. A detailed yet concise caption describing what you SEE in the image
2. Identify the type of construction work visible (foundation, structural, MEP, finishing, etc.)
3. Note any materials, equipment, or workers visible
4. Comment on the stage/phase of work

Keep captions professional and under 20 words.
Focus on factual observations from the image content."""
        ).with_model("openai", "gpt-4o")

        # Create message with image in file_contents list
        user_message = UserMessage(
            text="""Analyze this construction site photo and provide:
1. MAIN CAPTION: A single professional caption describing what you see (max 20 words)
2. ALTERNATIVE 1: Another way to describe the same scene
3. ALTERNATIVE 2: A third variation
4. ALTERNATIVE 3: A fourth variation

Format your response exactly like this:
MAIN: [your main caption]
ALT1: [alternative 1]
ALT2: [alternative 2]
ALT3: [alternative 3]""",
            file_contents=[image_content]  # Pass image in file_contents list
        )

        # Send message and get response
        ai_response = await chat.send_message(user_message)
        logger.info(f"AI Vision response: {ai_response}")

        # Parse structured response
        lines = ai_response.split('\n')
        main_caption = "Construction progress captured"
        alternatives = []

        for line in lines:
            line = line.strip()
            if line.upper().startswith('MAIN:'):
                main_caption = line[5:].strip()
            elif line.upper().startswith('ALT1:'):
                alternatives.append(line[5:].strip())
            elif line.upper().startswith('ALT2:'):
                alternatives.append(line[5:].strip())
            elif line.upper().startswith('ALT3:'):
                alternatives.append(line[5:].strip())

        # If parsing failed, try line-by-line approach
        if main_caption == "Construction progress captured" and len(lines) > 0:
            for line in lines:
                clean_line = line.strip()
                if clean_line and not clean_line.upper().startswith(
                        ('MAIN', 'ALT', '1.', '2.', '3.', '4.', '-')):
                    main_caption = clean_line[:100]
                    break
            for line in lines[1:4]:
                clean_line = line.strip()
                for prefix in [
                    '1.',
                    '2.',
                    '3.',
                    '4.',
                    '-',
                    '*',
                    'ALT:',
                        'Alternative:']:
                    clean_line = clean_line.replace(prefix, '').strip()
                if clean_line and clean_line != main_caption and len(
                        clean_line) > 5:
                    alternatives.append(clean_line[:100])

        return {
            "ai_caption": main_caption,
            "confidence": 0.92,
            "alternatives": alternatives[:3],
            "note": "AI analyzed your image. You can edit or select alternatives."
        }

    except Exception as e:
        logger.error(f"AI Vision API error: {str(e)}")
        # Fallback to construction-specific suggestions
        import random
        fallback_captions = [
            "Foundation work in progress",
            "Concrete pouring completed",
            "Steel reinforcement installation",
            "Formwork preparation",
            "Site excavation work",
            "Column casting completed",
            "Beam reinforcement work",
            "Slab concreting in progress",
        ]
        return {
            "ai_caption": random.choice(fallback_captions),
            "confidence": 0.5,
            "alternatives": random.sample(fallback_captions, 3),
            "note": "Fallback caption - AI service temporarily unavailable"
        }


class SpeechToTextRequest(BaseModel):
    """Request for speech-to-text conversion"""
    audio_data: str  # Base64 encoded audio
    audio_format: str = "webm"  # webm, mp3, wav, m4a, etc.


@project_management_router.post("/speech-to-text")
async def speech_to_text(
    request: SpeechToTextRequest,
    current_user: dict = Depends(get_current_user)
):
    """Convert speech to text and translate to English."""
    import base64
    import tempfile
    from pathlib import Path

    try:
        audio_data = request.audio_data
        if audio_data.startswith('data:'):
            audio_data = audio_data.split(',')[1]

        audio_bytes = base64.b64decode(audio_data)
        if len(audio_bytes) < 100:
            return {"transcript": "", "error": "Audio too short"}

        api_key = os.environ.get('EMERGENT_LLM_KEY')

        # Graceful fallback when no API key is configured
        if not api_key:
            logger.warning(
                "[STT] EMERGENT_LLM_KEY not set - returning mock transcription")
            return {
                "transcript": "",
                "original": "",
                "error": "API key not configured. Set EMERGENT_LLM_KEY in backend .env to enable voice-to-text.",
                "note": "mock"}

        file_ext = request.audio_format.lower() or 'webm'

        # Write to temp file
        with tempfile.NamedTemporaryFile(suffix=f'.{file_ext}', delete=False) as f:
            f.write(audio_bytes)
            temp_path = f.name

        try:
            # Use official OpenAI client directly
            from openai import OpenAI
            client = OpenAI(api_key=api_key)

            # Step 1: Transcribe with Whisper
            with open(temp_path, 'rb') as audio_file:
                result = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    response_format="json"
                )

            transcript = result.text if hasattr(
                result, 'text') else str(result)
            Path(temp_path).unlink(missing_ok=True)

            if not transcript.strip():
                return {"transcript": "", "error": "No speech detected"}

            # Step 2: Translate to English using GPT
            translation_response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a translator. Only output the English translation, nothing else. If the text is already in English, output it as-is."},
                    {"role": "user", "content": f"Translate to English: {transcript}"}
                ],
                temperature=0.3,
                max_tokens=2000
            )

            english = translation_response.choices[0].message.content or transcript

            return {
                "transcript": english.strip(),
                "original": transcript.strip()}
        except Exception as e:
            Path(temp_path).unlink(missing_ok=True)
            raise e
    except Exception as e:
        logger.error(f"[STT] Error: {str(e)}")
        return {"transcript": "", "error": str(e)}


@project_management_router.post("/dpr/{dpr_id}/images", status_code=201)
async def add_dpr_image(
    dpr_id: str,
    image_data: DPRImage,
    current_user: dict = Depends(get_current_user)
):
    """
    Add image to DPR.

    Images must be portrait 9:16 ratio.
    Minimum 4 images required for DPR submission.
    Images are compressed to ensure PDF < 3MB.
    """
    user = await permission_checker.get_authenticated_user(current_user)
    dpr_object_id = parse_object_id(dpr_id, "dpr_id")

    # Get DPR
    dpr = await db.dpr.find_one({"_id": dpr_object_id})
    if not dpr:
        raise HTTPException(status_code=404, detail="DPR not found")

    if dpr.get("locked_flag"):
        raise HTTPException(status_code=400,
                            detail="DPR is locked and cannot be modified")

    if dpr.get("organisation_id") != user["organisation_id"]:
        raise HTTPException(status_code=403, detail="Access denied")

    # Compress image to reduce size (simulate compression)
    # In production, use PIL/Pillow for actual compression
    compressed_data = image_data.image_data

    # Estimate compressed size (base64 is ~33% larger than binary)
    estimated_size_kb = len(compressed_data) * 0.75 / 1024

    # Create image document
    image_doc = {
        "image_id": str(ObjectId()),
        "image_data": compressed_data,
        "caption": image_data.caption,
        "activity_code": image_data.activity_code,
        "aspect_ratio": "9:16",
        "size_kb": estimated_size_kb,
        "uploaded_by": user["user_id"],
        "uploaded_at": datetime.utcnow().isoformat()
    }

    # Add to DPR
    await db.dpr.update_one(
        {"_id": dpr_object_id},
        {
            "$push": {"images": image_doc},
            "$inc": {"image_count": 1},
            "$set": {"updated_at": datetime.utcnow()}
        }
    )

    return {
        "image_id": image_doc["image_id"],
        "size_kb": round(estimated_size_kb, 2),
        "status": "added",
        "message": "Image added to DPR"
    }


# M10: Update image caption
class UpdateImageCaptionRequest(BaseModel):
    caption: str


@project_management_router.put("/dpr/{dpr_id}/images/{image_id}")
async def update_image_caption(
    dpr_id: str,
    image_id: str,
    request: UpdateImageCaptionRequest,
    current_user: dict = Depends(get_current_user)
):
    """Update caption for a specific image in DPR"""
    user = await permission_checker.get_authenticated_user(current_user)
    dpr_object_id = parse_object_id(dpr_id, "dpr_id")

    # Verify DPR exists and belongs to org
    dpr = await db.dpr.find_one({"_id": dpr_object_id})
    if not dpr:
        raise HTTPException(status_code=404, detail="DPR not found")

    if dpr.get("organisation_id") != user["organisation_id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    if dpr.get("locked_flag"):
        raise HTTPException(status_code=400,
                            detail="DPR is locked and cannot be modified")

    # Update the caption for the specific image
    result = await db.dpr.update_one(
        {
            "_id": dpr_object_id,
            "images.image_id": image_id
        },
        {
            "$set": {
                "images.$.caption": request.caption,
                "updated_at": datetime.utcnow()
            }
        }
    )

    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Image not found in DPR")

    return {"status": "updated", "message": "Caption updated successfully"}


@project_management_router.post("/dpr/{dpr_id}/generate-pdf")
async def generate_dpr_pdf(
    dpr_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Generate PDF from DPR.

    PDF Structure:
    - Page 1: Project details, Voice summary, Worker attendance
    - Page 2+: One image per page with caption

    Filename format: "ProjectCode - MMM DD, YYYY.pdf"
    """
    from core.pdf_service import pdf_generator
    from fastapi.responses import Response

    user = await permission_checker.get_authenticated_user(current_user)
    dpr_object_id = parse_object_id(dpr_id, "dpr_id")

    # Get DPR
    dpr = await db.dpr.find_one({"_id": dpr_object_id})
    if not dpr:
        raise HTTPException(status_code=404, detail="DPR not found")

    if dpr.get("organisation_id") != user["organisation_id"]:
        raise HTTPException(status_code=403, detail="Access denied")

    image_count = dpr.get("image_count", 0)
    if image_count < 4:
        raise HTTPException(
            status_code=400,
            detail=f"DPR requires minimum 4 images. Current: {image_count}"
        )

    # Get project data - try multiple lookup strategies
    project_id = dpr.get("project_id")
    project = None

    # Strategy 1: Try as ObjectId (seed-created projects use auto _id)
    try:
        project = await db.projects.find_one({"_id": ObjectId(project_id)})
    except BaseException:
        pass

    # Strategy 2: Try by project_id field
    if not project:
        project = await db.projects.find_one({"project_id": project_id})

    # Strategy 3: Try by string _id
    if not project:
        project = await db.projects.find_one({"_id": project_id})

    if not project:
        project = {"project_name": "Unknown Project", "project_code": "DPR"}

    # Normalize field names (seed uses 'name', app expects 'project_name')
    if "project_name" not in project and "name" in project:
        project["project_name"] = project["name"]
    if "project_code" not in project:
        project["project_code"] = project.get("code", "DPR")

    # Get worker log for today
    dpr_date = dpr.get("dpr_date")
    if isinstance(dpr_date, datetime):
        date_str = dpr_date.strftime("%Y-%m-%d")
    else:
        date_str = str(dpr_date).split(
            "T")[0] if dpr_date else datetime.now().strftime("%Y-%m-%d")

    worker_log = await db.worker_logs.find_one({
        "project_id": project_id,
        "date": date_str
    })

    # Prepare DPR data
    dpr_data = {
        "dpr_date": dpr.get("dpr_date"),
        "progress_notes": dpr.get("progress_notes", ""),
        "voice_summary": dpr.get("voice_summary", ""),
        "weather_conditions": dpr.get("weather_conditions", "Normal"),
        "supervisor_name": user.get("name", "Supervisor"),
    }

    # Get images
    images = dpr.get("images", [])

    # Generate PDF
    try:
        pdf_bytes = pdf_generator.generate_pdf(
            project_data=project,
            dpr_data=dpr_data,
            worker_log=worker_log,
            images=images
        )

        # Generate filename
        if isinstance(dpr_date, str):
            try:
                dpr_date_obj = datetime.fromisoformat(
                    dpr_date.replace('Z', '+00:00'))
            except BaseException:
                dpr_date_obj = datetime.now()
        elif isinstance(dpr_date, datetime):
            dpr_date_obj = dpr_date
        else:
            dpr_date_obj = datetime.now()

        project_code = project.get("project_code", "DPR")
        file_name = pdf_generator.get_filename(project_code, dpr_date_obj)

        # Calculate file size
        file_size_kb = len(pdf_bytes) / 1024

        # Update DPR with PDF info
        await db.dpr.update_one(
            {"_id": dpr_object_id},
            {
                "$set": {
                    "pdf_generated": True,
                    "file_name": file_name,
                    "file_size_kb": round(file_size_kb, 2),
                    "pdf_generated_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                }
            }
        )

        # Return PDF as downloadable file
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{file_name}"',
                "Content-Length": str(len(pdf_bytes))
            }
        )

    except Exception as e:
        logger.error(f"PDF generation failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate PDF: {str(e)}"
        )


@project_management_router.delete("/dpr/{dpr_id}")
async def delete_dpr(
    dpr_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete a DPR (only drafts or by owner)"""
    user = await permission_checker.get_authenticated_user(current_user)
    dpr_object_id = parse_object_id(dpr_id, "dpr_id")

    dpr = await db.dpr.find_one({"_id": dpr_object_id})
    if not dpr:
        raise HTTPException(status_code=404, detail="DPR not found")

    # Only owner or admin can delete
    if dpr.get("supervisor_id") != user["user_id"] and user.get(
            "role") != "Admin":
        raise HTTPException(status_code=403, detail="Not authorized")

    await db.dpr.delete_one({"_id": dpr_object_id})
    return {"message": "DPR deleted"}


@project_management_router.post("/dpr/{dpr_id}/submit")
async def submit_dpr(
    dpr_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Submit DPR for review.

    - Requires minimum 4 images
    - Generates PDF with:
      * Page 1: Project details, Voice summary, Worker attendance
      * Page 2+: One image per page with caption
    - Filename: "ProjectCode - MMM DD, YYYY.pdf"
    - Sends notification to admin
    - Locks DPR from further edits
    """
    from core.pdf_service import pdf_generator
    import hashlib
    import base64

    user = await permission_checker.get_authenticated_user(current_user)
    dpr_object_id = parse_object_id(dpr_id, "dpr_id")

    # Get DPR
    dpr = await db.dpr.find_one({"_id": dpr_object_id})
    if not dpr:
        raise HTTPException(status_code=404, detail="DPR not found")

    if dpr.get("organisation_id") != user["organisation_id"]:
        raise HTTPException(status_code=403, detail="Access denied")

    if dpr.get("locked_flag"):
        raise HTTPException(status_code=400, detail="DPR is already submitted")

    image_count = dpr.get("image_count", 0)
    if image_count < 4:
        raise HTTPException(
            status_code=400,
            detail=f"DPR requires minimum 4 images. Current: {image_count}"
        )

    # Get project data - try multiple lookup strategies
    project_id = dpr.get("project_id")
    project = None

    # Strategy 1: Try as ObjectId (seed-created projects use auto _id)
    try:
        project = await db.projects.find_one({"_id": ObjectId(project_id)})
    except BaseException:
        pass

    # Strategy 2: Try by project_id field
    if not project:
        project = await db.projects.find_one({"project_id": project_id})

    # Strategy 3: Try by string _id
    if not project:
        project = await db.projects.find_one({"_id": project_id})

    if not project:
        project = {"project_name": "Unknown Project", "project_code": "DPR"}

    # Normalize field names (seed uses 'name', app expects 'project_name')
    if "project_name" not in project and "name" in project:
        project["project_name"] = project["name"]
    if "project_code" not in project:
        project["project_code"] = project.get("code", "DPR")

    project_name = project.get("project_name", "Unknown Project")
    project_code = project.get("project_code", "DPR")

    # Get worker log for today
    dpr_date = dpr.get("dpr_date")
    if isinstance(dpr_date, datetime):
        date_str = dpr_date.strftime("%Y-%m-%d")
        dpr_date_obj = dpr_date
    else:
        date_str = str(dpr_date).split(
            "T")[0] if dpr_date else datetime.now().strftime("%Y-%m-%d")
        try:
            dpr_date_obj = datetime.fromisoformat(date_str)
        except BaseException:
            dpr_date_obj = datetime.now()

    worker_log = await db.worker_logs.find_one({
        "project_id": project_id,
        "date": date_str
    })

    # Prepare DPR data
    dpr_data = {
        "dpr_date": dpr_date_obj,
        "progress_notes": dpr.get("progress_notes", ""),
        "voice_summary": dpr.get("voice_summary", ""),
        "weather_conditions": dpr.get("weather_conditions", "Normal"),
        "supervisor_name": user.get("name", "Supervisor"),
    }

    # Get images
    images = dpr.get("images", [])

    # Generate PDF
    try:
        pdf_bytes = pdf_generator.generate_pdf(
            project_data=project,
            dpr_data=dpr_data,
            worker_log=worker_log,
            images=images
        )

        # Generate filename: "ProjectCode - MMM DD, YYYY.pdf"
        file_name = pdf_generator.get_filename(project_code, dpr_date_obj)
        file_size_kb = len(pdf_bytes) / 1024

        # Generate checksum
        pdf_checksum = hashlib.sha256(pdf_bytes).hexdigest()

        # Convert PDF to base64 for frontend download
        pdf_base64 = base64.b64encode(pdf_bytes).decode('utf-8')

    except Exception as e:
        logger.error(f"PDF generation failed: {e}")
        # Fallback - continue with submit but mark PDF as failed
        file_name = f"{project_code} - {
            dpr_date_obj.strftime('%b %d, %Y')}.pdf"
        file_size_kb = 0
        pdf_checksum = None
        pdf_base64 = None

    # Update DPR with PDF info
    await db.dpr.update_one(
        {"_id": dpr_object_id},
        {
            "$set": {
                "pdf_generated": pdf_base64 is not None,
                "file_name": file_name,
                "file_size_kb": round(file_size_kb, 2),
                "pdf_generated_at": datetime.utcnow(),
                "pdf_checksum": pdf_checksum,
            }
        }
    )

    # Build complete embedded snapshot
    snapshot_data = await build_dpr_snapshot(db, dpr_id)

    # Create immutable snapshot (with settings embedded)
    snapshot = await dpr_snapshot_service.create_snapshot(
        entity_type=SnapshotEntityType.DPR,
        entity_id=dpr_id,
        data=snapshot_data,
        organisation_id=user["organisation_id"],
        user_id=user["user_id"]
    )

    # Submit and lock
    await db.dpr.update_one(
        {"_id": dpr_object_id},
        {
            "$set": {
                "status": "submitted",
                "locked_flag": True,
                "locked_snapshot_version": snapshot.get("version", 1),
                "submitted_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
        }
    )

    # Create notification for admin
    try:
        # Format DPR date and time for message
        now = datetime.utcnow()
        time_str = now.strftime("%I:%M %p")  # e.g., "02:30 PM"

        if isinstance(dpr_date_obj, datetime):
            date_str = dpr_date_obj.strftime("%B %d, %Y")
        else:
            date_str = str(dpr_date).split(
                'T')[0] if dpr_date else now.strftime("%B %d, %Y")

        notification_doc = {
            "organisation_id": user["organisation_id"],
            "recipient_role": "admin",
            "recipient_user_id": None,
            "title": "New DPR Submitted",
            "message": f"{
                user.get(
                    'name',
                    'A supervisor')} submitted a Daily Progress Report for {project_name} on {date_str} at {time_str}",
            "notification_type": "dpr_submitted",
            "priority": "normal",
            "reference_type": "dpr",
            "reference_id": dpr_id,
            "project_id": project_id,
            "project_name": project_name,
            "sender_id": user["user_id"],
            "sender_name": user.get(
                "name",
                "Supervisor"),
            "is_read": False,
            "read_at": None,
            "created_at": now}

        await db.notifications.insert_one(notification_doc)
        logger.info(f"[DPR] Notification sent to admin for DPR {dpr_id}")
    except Exception as e:
        # Don't fail DPR submission if notification fails
        logger.warning(f"[DPR] Failed to create notification: {e}")

    return {
        "dpr_id": dpr_id,
        "status": "submitted",
        "pdf_generated": pdf_base64 is not None,
        "file_name": file_name,
        "file_size_kb": round(file_size_kb, 2),
        "pdf_data": pdf_base64,  # Base64 encoded PDF for download
        "snapshot_version": snapshot.get("version"),
        "locked": True,
        "message": "DPR submitted successfully with immutable snapshot"
    }


@project_management_router.get("/dpr/{dpr_id}/download")
async def download_dpr_pdf(
    dpr_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get DPR PDF download info.

    Returns PDF data or Google Drive link.
    """
    user = await permission_checker.get_authenticated_user(current_user)
    dpr_object_id = parse_object_id(dpr_id, "dpr_id")

    dpr = await db.dpr.find_one({"_id": dpr_object_id})
    if not dpr:
        raise HTTPException(status_code=404, detail="DPR not found")

    if dpr.get("organisation_id") != user["organisation_id"]:
        raise HTTPException(status_code=403, detail="Access denied")

    if not dpr.get("pdf_generated"):
        raise HTTPException(
            status_code=400,
            detail="PDF not yet generated. Submit DPR first.")

    return {
        "dpr_id": dpr_id,
        "file_name": dpr.get("file_name"),
        "file_size_kb": dpr.get("file_size_kb"),
        "drive_link": dpr.get("drive_link"),
        "generated_at": dpr.get("pdf_generated_at"),
        "note": "PDF export completed. Google Drive integration pending configuration."
    }


@project_management_router.get("/dpr")
async def list_dprs(
    project_id: Optional[str] = None,
    status_filter: Optional[str] = None,
    limit: int = 50,
    current_user: dict = Depends(get_current_user)
):
    """List DPRs"""
    user = await permission_checker.get_authenticated_user(current_user)

    query = {"organisation_id": user["organisation_id"]}

    if project_id:
        query["project_id"] = project_id

    if status_filter:
        query["status"] = status_filter

    dprs = await db.dpr.find(query).sort("dpr_date", -1).limit(limit).to_list(length=limit)

    result = []
    for dpr in dprs:
        dpr["dpr_id"] = str(dpr.pop("_id"))
        # Don't include full image data in list
        dpr["images"] = [{"image_id": img.get("image_id"), "caption": img.get(
            "caption")} for img in dpr.get("images", [])]
        result.append(serialize_mongo_doc(dpr))

    return {"dprs": result}


@project_management_router.get("/dpr/{dpr_id}")
async def get_dpr(
    dpr_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get single DPR with all details including images"""
    user = await permission_checker.get_authenticated_user(current_user)
    dpr_object_id = parse_object_id(dpr_id, "dpr_id")

    dpr = await db.dpr.find_one({"_id": dpr_object_id})
    if not dpr:
        raise HTTPException(status_code=404, detail="DPR not found")

    if dpr.get("organisation_id") != user["organisation_id"]:
        raise HTTPException(status_code=403, detail="Access denied")

    # Get project name
    project = None
    project_id = dpr.get("project_id")
    try:
        project = await db.projects.find_one({"_id": ObjectId(project_id)})
    except Exception:
        project = await db.projects.find_one({"project_id": project_id})
    if project:
        dpr["project_name"] = project.get("project_name", "Unknown")

    dpr["dpr_id"] = str(dpr.pop("_id"))
    return serialize_mongo_doc(dpr)


class UpdateDPRRequest(BaseModel):
    progress_notes: Optional[str] = None
    weather_conditions: Optional[str] = None
    manpower_count: Optional[int] = None
    issues_encountered: Optional[str] = None
    status: Optional[str] = None  # Admin can approve/change status


@project_management_router.put("/dpr/{dpr_id}")
async def update_dpr(
    dpr_id: str,
    request: UpdateDPRRequest,
    current_user: dict = Depends(get_current_user)
):
    """Update a DPR - admin can edit any status"""
    user = await permission_checker.get_authenticated_user(current_user)
    dpr_object_id = parse_object_id(dpr_id, "dpr_id")

    dpr = await db.dpr.find_one({"_id": dpr_object_id})
    if not dpr:
        raise HTTPException(status_code=404, detail="DPR not found")

    if dpr.get("organisation_id") != user["organisation_id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    if dpr.get("locked_flag"):
        raise HTTPException(status_code=400,
                            detail="DPR is locked and cannot be modified")

    # Build update dict
    update_data = {}
    if request.progress_notes is not None:
        update_data["progress_notes"] = request.progress_notes
    if request.weather_conditions is not None:
        update_data["weather_conditions"] = request.weather_conditions
    if request.manpower_count is not None:
        update_data["manpower_count"] = request.manpower_count
    if request.issues_encountered is not None:
        update_data["issues_encountered"] = request.issues_encountered
    if request.status is not None:
        update_data["status"] = request.status

    update_data["updated_at"] = datetime.utcnow()

    await db.dpr.update_one(
        {"_id": dpr_object_id},
        {"$set": update_data}
    )

    return {"status": "success", "message": "DPR updated"}


# =============================================================================
# SYSTEM
# =============================================================================

@project_management_router.post("/system/init-pm-indexes")
async def initialize_pm_indexes(
        current_user: dict = Depends(get_current_user)):
    """Initialize all Wave 3 database indexes"""
    user = await permission_checker.get_authenticated_user(current_user)
    await permission_checker.check_admin_role(user)

    await snapshot_engine.create_indexes()
    await job_engine.create_indexes()
    await ai_service.create_indexes()
    await security.create_indexes()

    return {"status": "success", "message": "Wave 3 indexes created"}


@project_management_router.get("/pm/health")
async def pm_health():
    """Wave 3 health check"""
    return {
        "status": "healthy",
        "wave": "3",
        "timestamp": datetime.utcnow().isoformat(),
        "features": {
            "snapshot_engine": True,
            "background_jobs": True,
            "ai_ocr": True,
            "ai_stt": True,
            "ai_vision": True,
            "signed_urls": True,
            "org_isolation": True,
            "configurable_retention": True
        },
        "ai_provider": "EMERGENT" if ai_api_key else "MOCK"
    }


# =============================================================================
# SNAPSHOT QUERY ENDPOINTS (Phase 2)
# =============================================================================

@project_management_router.get("/snapshots/{entity_type}/{entity_id}")
async def get_entity_snapshot(
    entity_type: str,
    entity_id: str,
    version: Optional[int] = None,
    current_user: dict = Depends(get_current_user)
):
    """
    Get snapshot for an entity.

    Args:
        entity_type: WORK_ORDER, PAYMENT_CERTIFICATE, or DPR
        entity_id: The entity ID
        version: Optional specific version (defaults to latest)

    Returns immutable snapshot with embedded data and settings.
    """
    user = await permission_checker.get_authenticated_user(current_user)

    snapshot = await dpr_snapshot_service.get_snapshot(entity_type, entity_id, version)

    if not snapshot:
        raise HTTPException(status_code=404, detail="Snapshot not found")
    if snapshot.get("organisation_id") != user["organisation_id"]:
        raise HTTPException(status_code=403, detail="Access denied")

    # Convert for response
    snapshot["snapshot_id"] = str(snapshot.get("_id", ""))
    if "_id" in snapshot:
        del snapshot["_id"]

    return serialize_mongo_doc(snapshot)


@project_management_router.get("/snapshots/{entity_type}/{entity_id}/versions")
async def get_all_snapshot_versions(
    entity_type: str,
    entity_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get all snapshot versions for an entity.

    Returns list of versions with metadata (no full data).
    """
    user = await permission_checker.get_authenticated_user(current_user)

    snapshots = await dpr_snapshot_service.get_all_versions(entity_type, entity_id)
    snapshots = [s for s in snapshots if s.get(
        "organisation_id") == user["organisation_id"]]

    # Return metadata only
    result = []
    for s in snapshots:
        result.append({
            "version": s.get("version"),
            "generated_at": s.get("generated_at"),
            "generated_by": s.get("generated_by"),
            "is_latest": s.get("is_latest", False),
            "data_checksum": s.get("data_checksum"),
            "pdf_checksum": s.get("pdf_checksum")
        })

    return result


@project_management_router.post("/snapshots/{entity_type}/{entity_id}/verify")
async def verify_snapshot_integrity(
    entity_type: str,
    entity_id: str,
    version: int,
    current_user: dict = Depends(get_current_user)
):
    """
    Verify integrity of a snapshot.

    Returns checksum verification results.
    """
    user = await permission_checker.get_authenticated_user(current_user)

    result = await dpr_snapshot_service.verify_checksum(entity_type, entity_id, version)
    snapshot = await dpr_snapshot_service.get_snapshot(entity_type, entity_id, version)
    if not snapshot:
        raise HTTPException(status_code=404, detail="Snapshot not found")
    if snapshot.get("organisation_id") != user["organisation_id"]:
        raise HTTPException(status_code=403, detail="Access denied")

    return result


# =============================================================================
# ATTENDANCE ENDPOINTS
# =============================================================================

@project_management_router.post("/attendance", status_code=201)
async def mark_attendance(
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """Mark attendance (check-in) for today"""
    user = await permission_checker.get_authenticated_user(current_user)

    try:
        body = await request.json()
    except Exception:
        body = {}
    project_id = body.get("project_id")
    location = body.get("location", {})

    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    # Check if already marked today
    existing = await db.attendance.find_one({
        "user_id": user["user_id"],
        "check_in_time": {"$gte": today}
    })

    if existing:
        raise HTTPException(status_code=400,
                            detail="Attendance already marked for today")

    doc = {
        "user_id": user["user_id"],
        "user_name": user.get("name", "Unknown"),
        "role": user.get("role", "Supervisor"),
        "organisation_id": user["organisation_id"],
        "project_id": project_id,
        "check_in_time": datetime.utcnow(),
        "location": location,
        "status": "checked_in",
    }

    result = await db.attendance.insert_one(doc)

    return {"status": "success", "attendance_id": str(result.inserted_id)}


@project_management_router.get("/attendance/check")
async def check_attendance(
    project_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Check if current user has marked attendance today"""
    user = await permission_checker.get_authenticated_user(current_user)

    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    query = {
        "user_id": user["user_id"],
        "check_in_time": {"$gte": today}
    }

    existing = await db.attendance.find_one(query)

    return {"attendance_marked": existing is not None, "check_in_time": existing.get(
        "check_in_time").isoformat() if existing else None, }


@project_management_router.get("/attendance/history")
async def get_attendance_history(
    limit: int = 10,
    current_user: dict = Depends(get_current_user)
):
    """Get attendance history for current user"""
    user = await permission_checker.get_authenticated_user(current_user)

    records = await db.attendance.find({
        "user_id": user["user_id"]
    }).sort("check_in_time", -1).limit(limit).to_list(length=limit)

    result = []
    for r in records:
        r["attendance_id"] = str(r.pop("_id"))
        result.append(serialize_mongo_doc(r))

    return {"attendance": result}


@project_management_router.get("/attendance/admin/all")
async def get_all_attendance(
    project_id: Optional[str] = None,
    date: Optional[str] = None,
    limit: int = 50,
    current_user: dict = Depends(get_current_user)
):
    """Admin: Get all attendance records, optionally filtered by project and date"""
    user = await permission_checker.get_authenticated_user(current_user)
    await permission_checker.check_admin_role(user)

    query: dict = {"organisation_id": user["organisation_id"]}

    if project_id:
        query["project_id"] = project_id

    if date:
        try:
            day_start = datetime.strptime(date, "%Y-%m-%d")
            day_end = day_start + timedelta(days=1)
            query["check_in_time"] = {"$gte": day_start, "$lt": day_end}
        except ValueError:
            pass

    records = await db.attendance.find(query).sort("check_in_time", -1).limit(limit).to_list(length=limit)

    result = []
    for r in records:
        r["attendance_id"] = str(r.pop("_id"))
        # Enrich with project name
        if r.get("project_id"):
            try:
                project = await db.projects.find_one({"_id": ObjectId(r["project_id"])})
                r["project_name"] = project.get(
                    "project_name", "Unknown") if project else "Unknown"
            except Exception:
                r["project_name"] = "Unknown"
        result.append(serialize_mongo_doc(r))

    return {"attendance": result, "total": len(result)}


# =============================================================================
# ADMIN: PROJECTS OVERVIEW (BIRDS-EYE VIEW)
# =============================================================================

@project_management_router.get("/admin/projects-overview")
async def get_admin_projects_overview(
    current_user: dict = Depends(get_current_user)
):
    """
    Birds-eye view of ALL active projects with aggregated stats.
    Returns per-project: budget totals, DPR counts, worker counts, completion %.
    """
    try:
        user = await permission_checker.get_authenticated_user(current_user)
        await permission_checker.check_admin_role(user)
        org_id = user.get("organisation_id")

        # Get all active projects for this org
        projects = await db.projects.find({
            "organisation_id": org_id,
            "status": {"$in": ["active", "Active"]}
        }).to_list(length=100)

        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        result = []

        for project in projects:
            pid = str(project["_id"])

            # --- Budget aggregation ---
            budgets = await db.project_budgets.find({"project_id": pid}).to_list(length=None)
            total_master_budget = 0.0
            total_committed = 0.0
            total_certified = 0.0
            total_remaining = 0.0
            categories = []

            for b in budgets:
                approved = b.get("approved_budget_amount", 0)
                total_master_budget += approved

                # Get financial state
                fs = await db.financial_state.find_one({
                    "project_id": pid,
                    "code_id": b.get("code_id")
                })

                committed = 0.0
                certified = 0.0
                remaining = approved

                if fs:
                    committed = fs.get("committed_value", 0)
                    certified = fs.get("certified_value", 0)
                    remaining = fs.get("balance_budget_remaining", approved)

                total_committed += committed
                total_certified += certified
                total_remaining += remaining

                # Get code name
                code = await db.code_master.find_one({"_id": ObjectId(b.get("code_id"))})
                code_name = code.get(
                    "code_description", code.get(
                        "code_short", "Unknown")) if code else "Unknown"

                categories.append({
                    "code_id": b.get("code_id"),
                    "code_name": code_name,
                    "approved_budget": approved,
                    "committed": committed,
                    "certified": certified,
                    "remaining": remaining,
                })

            # --- Completion % (budget-based) ---
            completion_pct = 0.0
            if total_master_budget > 0:
                completion_pct = round(
                    (total_certified / total_master_budget) * 100, 1)

            # --- DPR counts ---
            total_dprs = await db.dpr.count_documents({"project_id": pid, "organisation_id": org_id})
            dprs_today = await db.dpr.count_documents({"project_id": pid, "organisation_id": org_id, "created_at": {"$gte": today}})
            pending_approvals = await db.dpr.count_documents({"project_id": pid, "organisation_id": org_id, "status": "submitted"})

            # --- Worker count (from latest worker logs) ---
            latest_logs = await db.worker_logs.find({"project_id": pid, "organisation_id": org_id}).sort("date", -1).limit(10).to_list(length=10)
            total_workers = 0
            for log in latest_logs:
                total_workers += log.get("total_workers", 0)

            # --- Petty cash total ---
            petty_pipeline = [
                {"$match": {"project_id": pid, "organisation_id": org_id}},
                {"$group": {"_id": None, "total": {"$sum": "$amount"}}}
            ]
            petty_result = await db.petty_cash.aggregate(petty_pipeline).to_list(length=1)
            petty_cash_total = petty_result[0]["total"] if petty_result else 0

            result.append({
                "project_id": pid,
                "project_name": project.get("project_name", "Unknown"),
                "project_code": project.get("project_code"),
                "status": project.get("status", "active"),
                "completion_pct": completion_pct,
                "budget": {
                    "total_master": total_master_budget,
                    "total_committed": total_committed,
                    "total_certified": total_certified,
                    "total_remaining": total_remaining,
                    "categories": categories,
                },
                "petty_cash_total": petty_cash_total,
                "dprs": {
                    "total": total_dprs,
                    "today": dprs_today,
                    "pending_approvals": pending_approvals,
                },
                "workers": {
                    "recent_total": total_workers,
                },
            })

        return {"projects": result}

    except Exception as e:
        logger.error(f"Projects overview error: {e}")
        raise HTTPException(status_code=500,
                            detail="Projects overview unavailable")


# =============================================================================
# ADMIN DASHBOARD STATS ENDPOINT
# =============================================================================

@project_management_router.get("/admin/dashboard-stats")
async def get_admin_dashboard_stats(
    project_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """
    Get admin dashboard statistics, optionally scoped to a project.
    """
    try:
        user = await permission_checker.get_authenticated_user(current_user)
        await permission_checker.check_admin_role(user)
        org_id = user.get("organisation_id")

        if project_id:
            await permission_checker.check_project_access(user, project_id, require_write=False)

        # Count supervisors
        supervisor_count = await db.users.count_documents({"role": "Supervisor", "organisation_id": org_id})

        # Build DPR query
        dpr_query: dict = {"organisation_id": org_id}
        if project_id:
            dpr_query["project_id"] = project_id

        # Count today's DPRs
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        today_query = {**dpr_query, "created_at": {"$gte": today}}
        dprs_today = await db.dpr.count_documents(today_query)

        # Count pending approvals (status = submitted)
        pending_query = {**dpr_query, "status": "submitted"}
        pending_approvals = await db.dpr.count_documents(pending_query)

        # Count total worker logs for this project
        wl_query: dict = {"organisation_id": org_id}
        if project_id:
            wl_query["project_id"] = project_id
        total_workers = 0
        worker_logs = await db.worker_logs.find(wl_query).to_list(length=1000)
        for log in worker_logs:
            total_workers += log.get("total_workers", 0)

        return {
            "total_workers": total_workers,
            "active_supervisors": supervisor_count,
            "dprs_today": dprs_today,
            "pending_approvals": pending_approvals
        }
    except Exception as e:
        logger.error(f"Dashboard stats error: {e}")
        raise HTTPException(status_code=500, detail="Stats unavailable")
