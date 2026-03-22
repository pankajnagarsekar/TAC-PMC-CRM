from dotenv import load_dotenv
from pathlib import Path
import os

# Load environment before any custom modules evaluate os.getenv()
ROOT_DIR = Path(__file__).resolve().parent
load_dotenv(ROOT_DIR / '.env')

from fastapi.staticfiles import StaticFiles  # noqa: E402
from fastapi import FastAPI, APIRouter, HTTPException, status, Depends, Response, Cookie, Query  # noqa: E402
from fastapi.concurrency import run_in_threadpool  # noqa: E402
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials  # noqa: E402
from starlette.middleware.cors import CORSMiddleware  # noqa: E402
from motor.motor_asyncio import AsyncIOMotorClient  # noqa: E402
from bson import ObjectId, Decimal128  # noqa: E402
from decimal import Decimal  # noqa: E402
import logging  # noqa: E402
from typing import List, Optional, Dict, Any  # noqa: E402
from datetime import datetime, timezone  # noqa: E402
from project_management_routes import project_management_router  # noqa: E402
from financial_routes import financial_router  # noqa: E402
from hardened_routes import hardened_router  # noqa: E402
from vendor_routes import router as vendor_router  # noqa: E402
from work_order_routes import router as work_order_router, project_scoped_router as work_order_project_router  # noqa: E402
from payment_certificate_routes import pc_router  # noqa: E402
from cash_routes import cash_router  # noqa: E402
from site_operations_routes import router as site_operations_router, dpr_router, attendance_router, voice_log_router, site_overheads_router  # noqa: E402
from core.database import db_manager  # noqa: E402
from reporting_routes import reporting_router  # noqa: E402
from settings_routes import settings_router  # noqa: E402
from audit_routes import router as audit_router  # noqa: E402
from project_scheduler_routes import scheduler_router  # noqa: E402
from core.indexes import ensure_indexes  # noqa: E402
from core.rate_limit import init_rate_limiting  # noqa: E402

# Import custom modules
from models import (  # noqa: E402
    UserCreate, UserResponse, UserUpdate, UserProjectMapCreate, ProjectCreate, ProjectUpdate,
    CodeMasterCreate, CodeMasterUpdate, ProjectBudgetCreate, ProjectBudgetUpdate,
    Token, LoginRequest, RefreshTokenRequest, WorkersDailyLogCreate, WorkersDailyLogUpdate,
    NotificationCreate, Client, ClientCreate, ClientUpdate, Project, CodeMaster, ProjectBudget,
    PaymentCertificate, PaymentCertificateCreate, GlobalSettings, FundAllocation, CashTransaction,
    SiteOverhead, SiteOverheadCreate, SiteOverheadUpdate
)
from auth import (  # noqa: E402
    hash_password, verify_password, create_access_token, create_refresh_token, decode_refresh_token,
    get_current_user, revoke_token, decode_access_token
)
from audit_service import AuditService  # noqa: E402
from financial_service import FinancialRecalculationService  # noqa: E402
from permissions import PermissionChecker  # noqa: E402
from core.utils import serialize_doc  # noqa: E402


# Local serialize_doc removed, using core.utils.serialize_doc


# MongoDB connection
mongo_url = os.environ['MONGO_URL']
db_name = os.environ['DB_NAME']
db_manager.connect(mongo_url, db_name)
db = db_manager.db

# Initialize services
audit_service = AuditService(db)
financial_service = FinancialRecalculationService(db)
permission_checker = PermissionChecker(db)

# Create the main app
app = FastAPI(
    title="Construction Management System - Phase 2 Hardened",
    version="2.0.0",
    description="Enterprise Construction Management with Hardened Financial Core"
)

# Configure CORS — MUST be added before routes
allowed_origins = [
    "http://localhost:3000",
    "http://localhost:3001",
    "http://localhost:3002",
    "http://localhost:3010",
    "http://localhost:19006",
    "http://localhost:8081",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3001",
    "http://127.0.0.1:3002",
    "http://127.0.0.1:3010",
    "http://127.0.0.1:19006",
    "http://127.0.0.1:8081",
]

# Allow environment variable override
env_origins = os.getenv("ALLOWED_ORIGINS")
if env_origins:
    allowed_origins = [origin.strip() for origin in env_origins.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

init_rate_limiting(app)

app.include_router(audit_router, prefix="/api")
app.include_router(scheduler_router, prefix="/api/projects")

# Create router with /api prefix
api_router = APIRouter(prefix="/api")

# HTTP Bearer for token extraction
security = HTTPBearer()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Startup tasks
@app.on_event("startup")
async def startup_db_client():
    await ensure_indexes(db)
    logger.info("Database startup tasks completed.")


@api_router.get("/clients", response_model=List[Client])
async def list_clients(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    current_user: dict = Depends(get_current_user)
):
    """List all clients for the organisation with pagination"""
    user = await permission_checker.get_authenticated_user(current_user)
    clients = await db.clients.find({"organisation_id": user["organisation_id"]}).skip(skip).limit(limit).to_list(length=limit)
    return [serialize_doc(c) for c in clients]


@api_router.post("/clients", response_model=Client, status_code=status.HTTP_201_CREATED)
async def create_client(client_data: ClientCreate, current_user: dict = Depends(get_current_user)):
    """Create a new client"""
    user = await permission_checker.get_authenticated_user(current_user)
    # Phase 6.3: Block Supervisor from Web CRM, Block Client from writes
    await permission_checker.check_web_crm_access(user)
    await permission_checker.check_client_readonly(user)
    await permission_checker.check_admin_role(user)

    client_dict = client_data.dict()
    client_dict["organisation_id"] = user["organisation_id"]
    client_dict["created_at"] = datetime.now(timezone.utc)
    client_dict["updated_at"] = datetime.now(timezone.utc)
    client_dict["active_status"] = True

    result = await db.clients.insert_one(client_dict)
    client_dict["_id"] = result.inserted_id

    # Audit log
    await audit_service.log_action(
        organisation_id=user["organisation_id"],
        module_name="CLIENT_MANAGEMENT",
        entity_type="CLIENT",
        entity_id=str(result.inserted_id),
        action_type="CREATE",
        user_id=user["user_id"],
        new_value={"client_name": client_data.client_name}
    )
    return serialize_doc(client_dict)


@api_router.get("/clients/{client_id}", response_model=Client)
async def get_client(client_id: str, current_user: dict = Depends(get_current_user)):
    """Get a specific client by ID"""
    user = await permission_checker.get_authenticated_user(current_user)
    client = await db.clients.find_one({"_id": ObjectId(client_id), "organisation_id": user["organisation_id"]})
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return serialize_doc(client)


@api_router.put("/clients/{client_id}", response_model=Client)
async def update_client(client_id: str, client_data: ClientUpdate, current_user: dict = Depends(get_current_user)):
    """Update a client"""
    user = await permission_checker.get_authenticated_user(current_user)
    # Phase 6.3: Block Supervisor from Web CRM, Block Client from writes
    await permission_checker.check_web_crm_access(user)
    await permission_checker.check_client_readonly(user)
    await permission_checker.check_admin_role(user)

    update_data = {k: v for k, v in client_data.dict().items() if v is not None}
    update_data["updated_at"] = datetime.now(timezone.utc)

    result = await db.clients.find_one_and_update(
        {"_id": ObjectId(client_id), "organisation_id": user["organisation_id"]},
        {"$set": update_data},
        return_document=True
    )
    if not result:
        raise HTTPException(status_code=404, detail="Client not found")

    # Audit log
    await audit_service.log_action(
        organisation_id=user["organisation_id"],
        module_name="CLIENT_MANAGEMENT",
        entity_type="CLIENT",
        entity_id=client_id,
        action_type="UPDATE",
        user_id=user["user_id"],
        new_value=update_data
    )
    return serialize_doc(result)


@api_router.delete("/clients/{client_id}")
async def delete_client(client_id: str, current_user: dict = Depends(get_current_user)):
    """Soft delete a client by setting active_status to false"""
    user = await permission_checker.get_authenticated_user(current_user)
    # Phase 6.3: Block Supervisor from Web CRM, Block Client from writes
    await permission_checker.check_web_crm_access(user)
    await permission_checker.check_client_readonly(user)
    await permission_checker.check_admin_role(user)

    # Check if client has associated projects
    project_count = await db.projects.count_documents({"client_id": client_id, "organisation_id": user["organisation_id"]})
    if project_count > 0:
        raise HTTPException(status_code=400, detail="Cannot delete client with associated projects")

    result = await db.clients.find_one_and_update(
        {"_id": ObjectId(client_id), "organisation_id": user["organisation_id"]},
        {"$set": {"active_status": False, "updated_at": datetime.now(timezone.utc)}},
        return_document=True
    )
    if not result:
        raise HTTPException(status_code=404, detail="Client not found")

    # Audit log
    await audit_service.log_action(
        organisation_id=user["organisation_id"],
        module_name="CLIENT_MANAGEMENT",
        entity_type="CLIENT",
        entity_id=client_id,
        action_type="DELETE",
        user_id=user["user_id"],
        old_value={"client_name": result.get("client_name")}
    )
    return {"message": "Client deleted successfully"}


# ============================================



# ============================================
# PAYMENT CERTIFICATE ENDPOINTS
# ============================================
@api_router.get("/payment-certificates")
async def list_payment_certificates(
    project_id: str = Query(..., description="Project ID"),
    limit: int = Query(50, ge=1, le=500, description="Results limit"),
    cursor: Optional[str] = Query(None, description="Pagination cursor"),
    current_user: dict = Depends(get_current_user)
):
    """List all payment certificates for a project"""
    user = await permission_checker.get_authenticated_user(current_user)
    # Check project
    project = await db.projects.find_one({"_id": ObjectId(project_id), "organisation_id": user["organisation_id"]})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    query = {"project_id": project_id, "organisation_id": user["organisation_id"]}
    if cursor:
        try:
            parsed_cursor = datetime.fromisoformat(cursor.replace('Z', '+00:00'))
            query["created_at"] = {"$lt": parsed_cursor}
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid cursor format")

    cursor_obj = db.payment_certificates.find(query).sort("created_at", -1).limit(limit)
    docs = await cursor_obj.to_list(length=limit)

    next_cursor = None
    if len(docs) == limit:
        last_doc = docs[-1]
        ts = last_doc.get("created_at")
        if isinstance(ts, datetime):
            next_cursor = ts.isoformat()

    return {
        "items": [serialize_doc(c) for c in docs],
        "next_cursor": next_cursor
    }


@api_router.post("/payment-certificates", response_model=PaymentCertificate, status_code=status.HTTP_201_CREATED)
async def create_payment_certificate(pc_data: PaymentCertificateCreate, current_user: dict = Depends(get_current_user)):
    """Create a new payment certificate (can be from OCR)"""
    user = await permission_checker.get_authenticated_user(current_user)
    pc_dict = pc_data.dict()
    pc_dict["organisation_id"] = user["organisation_id"]
    pc_dict["created_at"] = datetime.now(timezone.utc)
    pc_dict["status"] = "draft"

    result = await db.payment_certificates.insert_one(pc_dict)
    pc_dict["_id"] = result.inserted_id

    # Audit
    await audit_service.log_action(
        organisation_id=user["organisation_id"],
        module_name="PAYMENT_CERTIFICATES",
        entity_type="PAYMENT_CERTIFICATE",
        entity_id=str(result.inserted_id),
        action_type="CREATE",
        user_id=user["user_id"],
        project_id=pc_data.project_id,
        new_value={"total_amount": pc_data.total_amount, "vendor": pc_data.vendor_name}
    )
    return serialize_doc(pc_dict)


@api_router.post("/auth/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(user_data: UserCreate):
    """
    Register a new user. First user becomes Admin, subsequent users default to their specified role.
    """
    # Check if email already exists
    existing_user = await db.users.find_one({"email": user_data.email})
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Get default organisation (assuming single org for Phase 1)
    organisation = await db.organisations.find_one({})
    if not organisation:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No organisation found. Please run seed script."
        )
    organisation_id = str(organisation["_id"])

    # Check if this is the first user
    user_count = await db.users.count_documents({})
    role = "Admin" if user_count == 0 else user_data.role

    # Hash password
    hashed_pw = hash_password(user_data.password)

    # Create user
    user_dict = {
        "organisation_id": organisation_id,
        "name": user_data.name,
        "email": user_data.email,
        "hashed_password": hashed_pw,
        "role": role,
        "active_status": True,
        "dpr_generation_permission": user_data.dpr_generation_permission,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }
    result = await db.users.insert_one(user_dict)
    user_id = str(result.inserted_id)

    # Audit log
    await audit_service.log_action(
        organisation_id=organisation_id,
        module_name="USER_MANAGEMENT",
        entity_type="USER",
        entity_id=user_id,
        action_type="CREATE",
        user_id=user_id,
        new_value={"email": user_data.email, "role": role}
    )

    # Return user response
    user_dict["user_id"] = user_id
    del user_dict["hashed_password"]
    return UserResponse(**user_dict)


@api_router.post("/auth/login", response_model=Token)
async def login(login_data: LoginRequest, response: Response):
    """
    Authenticate user and return JWT tokens.
    CORRECTED: Access token expires in 30 minutes (not 30 days).
    Refresh token expires in 7 days.
    """
    # Find user by email
    user = await db.users.find_one({"email": login_data.email})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    # Verify password (Offload blocking work to threadpool)
    if not await run_in_threadpool(verify_password, login_data.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    # Check active status
    if not user.get("active_status", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )

    # Create tokens
    user_id = str(user["_id"])
    token_data = {
        "user_id": user_id,
        "email": user["email"],
        "role": user["role"],
        "organisation_id": user["organisation_id"]
    }
    access_token = create_access_token(data=token_data)
    refresh_token = create_refresh_token(user_id=user_id)

    # Store refresh token in database (for token rotation)
    from auth import decode_refresh_token
    refresh_payload = decode_refresh_token(refresh_token)
    refresh_token_doc = {
        "jti": refresh_payload["jti"],
        "user_id": user_id,
        "token_hash": hash_password(refresh_token),  # Store hashed
        "expires_at": datetime.fromtimestamp(refresh_payload["exp"], tz=timezone.utc),
        "is_revoked": False,
        "created_at": datetime.now(timezone.utc)
    }
    await db.refresh_tokens.insert_one(refresh_token_doc)

    # Prepare user response
    user_response = UserResponse(
        user_id=user_id,
        organisation_id=user["organisation_id"],
        name=user["name"],
        email=user["email"],
        role=user["role"],
        active_status=user["active_status"],
        dpr_generation_permission=user.get("dpr_generation_permission", False),
        assigned_projects=user.get("assigned_projects", []),
        screen_permissions=user.get("screen_permissions", []),
        created_at=user["created_at"],
        updated_at=user["updated_at"]
    )

    # Set refresh token in HTTP-only cookie
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        max_age=7 * 24 * 3600,  # 7 days
        expires=7 * 24 * 3600,
        samesite="lax",
        secure=os.getenv("NODE_ENV") == "production"
    )

    return Token(
        access_token=access_token,
        expires_in=1800,  # 30 minutes in seconds
        user=user_response
    )


@api_router.post("/auth/refresh", response_model=Token)
async def refresh_access_token(
    response: Response,
    refresh_token: Optional[str] = Cookie(None)
):
    """
    Refresh access token using refresh token from cookie.
    Token Rotation: Old refresh token is revoked, new one is issued.
    """
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token missing"
        )

    try:
        # Decode refresh token
        payload = decode_refresh_token(refresh_token)
        jti = payload["jti"]
        user_id = payload["user_id"]

        # Check if refresh token exists and is not revoked
        token_doc = await db.refresh_tokens.find_one({
            "jti": jti,
            "user_id": user_id,
            "is_revoked": False
        })
        if not token_doc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token is invalid or has been revoked"
            )

        # Get user
        user = await db.users.find_one({"_id": ObjectId(user_id)})
        if not user or not user.get("active_status", False):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive"
            )

        # Revoke old refresh token (Strict rotation)
        await db.refresh_tokens.update_one(
            {"jti": jti},
            {"$set": {"is_revoked": True}}
        )

        # Create new tokens (token rotation)
        token_data = {
            "user_id": user_id,
            "email": user["email"],
            "role": user["role"],
            "organisation_id": user["organisation_id"]
        }
        access_token = create_access_token(data=token_data)
        new_refresh_token = create_refresh_token(user_id=user_id)

        # New refresh token metadata
        new_payload = decode_refresh_token(new_refresh_token)
        await db.refresh_tokens.insert_one({
            "jti": new_payload["jti"],
            "user_id": user_id,
            "token_hash": hash_password(new_refresh_token),
            "expires_at": datetime.fromtimestamp(new_payload["exp"], tz=timezone.utc),
            "is_revoked": False,
            "created_at": datetime.now(timezone.utc)
        })

        # Set new refresh token in cookie
        response.set_cookie(
            key="refresh_token",
            value=new_refresh_token,
            httponly=True,
            max_age=7 * 24 * 3600,
            samesite="lax",
            secure=os.getenv("NODE_ENV") == "production"
        )

        # Prepare user response
        user_response = UserResponse(
            user_id=user_id,
            organisation_id=user["organisation_id"],
            name=user["name"],
            email=user["email"],
            role=user["role"],
            active_status=user["active_status"],
            created_at=user["created_at"],
            updated_at=user["updated_at"]
        )

        return Token(
            access_token=access_token,
            expires_in=1800,
            user=user_response
        )
    except Exception as e:
        logger.error(f"Token refresh failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not refresh token"
        )


@api_router.post("/auth/logout")
async def logout(
    response: Response,
    refresh_token: Optional[str] = Cookie(None),
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    Logout user by revoking both access token and refresh token.
    Implements complete token revocation for security.
    """
    # Revoke access token
    try:
        token = credentials.credentials
        payload = decode_access_token(token)
        jti = payload.get("jti")
        if jti:
            await revoke_token(jti, "access", db)
    except Exception as e:
        logger.debug(f"Could not revoke access token: {e}")

    # Revoke refresh token
    if refresh_token:
        try:
            payload = decode_refresh_token(refresh_token)
            jti = payload.get("jti")
            if jti:
                await revoke_token(jti, "refresh", db)
            await db.refresh_tokens.update_one(
                {"jti": payload["jti"]},
                {"$set": {"is_revoked": True}}
            )
        except Exception as e:
            logger.debug(f"Could not revoke refresh token: {e}")

    response.delete_cookie(key="refresh_token")
    return {"message": "Logged out successfully"}


# ============================================
# USER MANAGEMENT ENDPOINTS
# ============================================
@api_router.get("/users", response_model=List[UserResponse])
async def get_users(current_user: dict = Depends(get_current_user)):
    """Get all users in the organisation"""
    user = await permission_checker.get_authenticated_user(current_user)
    # Filter by organisation
    users = await db.users.find(
        {"organisation_id": user["organisation_id"]}
    ).to_list(length=None)

    # Convert to response format
    user_list = []
    for u in users:
        user_list.append(
            UserResponse(
                user_id=str(u["_id"]),
                organisation_id=u["organisation_id"],
                name=u["name"],
                email=u["email"],
                role=u["role"],
                active_status=u["active_status"],
                dpr_generation_permission=u.get("dpr_generation_permission", False),
                assigned_projects=u.get("assigned_projects", []),
                screen_permissions=u.get("screen_permissions", []),
                created_at=u["created_at"],
                updated_at=u["updated_at"]
            )
        )
    return user_list


@api_router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get specific user by ID"""
    user = await permission_checker.get_authenticated_user(current_user)
    target_user = await db.users.find_one({"_id": ObjectId(user_id)})
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Check organisation match
    if target_user["organisation_id"] != user["organisation_id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    return UserResponse(
        user_id=str(target_user["_id"]),
        organisation_id=target_user["organisation_id"],
        name=target_user["name"],
        email=target_user["email"],
        role=target_user["role"],
        active_status=target_user["active_status"],
        dpr_generation_permission=target_user.get("dpr_generation_permission", False),
        assigned_projects=target_user.get("assigned_projects", []),
        screen_permissions=target_user.get("screen_permissions", []),
        created_at=target_user["created_at"],
        updated_at=target_user["updated_at"]
    )


@api_router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    update_data: UserUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update user (Admin only)"""
    user = await permission_checker.get_authenticated_user(current_user)
    await permission_checker.check_admin_role(user)

    # Get existing user
    target_user = await db.users.find_one({"_id": ObjectId(user_id)})
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Check organisation match
    if target_user["organisation_id"] != user["organisation_id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    # Prepare update
    update_dict = update_data.dict(exclude_unset=True)
    update_dict["updated_at"] = datetime.now(timezone.utc)

    # Update user
    await db.users.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": update_dict}
    )

    # Audit log
    await audit_service.log_action(
        organisation_id=user["organisation_id"],
        module_name="USER_MANAGEMENT",
        entity_type="USER",
        entity_id=user_id,
        action_type="UPDATE",
        user_id=user["user_id"],
        old_value={"role": target_user.get("role"), "active_status": target_user.get("active_status")},
        new_value=update_dict
    )

    # Get updated user
    updated_user = await db.users.find_one({"_id": ObjectId(user_id)})
    return UserResponse(
        user_id=str(updated_user["_id"]),
        organisation_id=updated_user["organisation_id"],
        name=updated_user["name"],
        email=updated_user["email"],
        role=updated_user["role"],
        active_status=updated_user["active_status"],
        dpr_generation_permission=updated_user.get("dpr_generation_permission", False),
        assigned_projects=updated_user.get("assigned_projects", []),
        screen_permissions=updated_user.get("screen_permissions", []),
        created_at=updated_user["created_at"],
        updated_at=updated_user["updated_at"]
    )


@api_router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete/deactivate user (Admin only)"""
    user = await permission_checker.get_authenticated_user(current_user)
    await permission_checker.check_admin_role(user)

    target_user = await db.users.find_one({"_id": ObjectId(user_id)})
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    if target_user["organisation_id"] != user["organisation_id"]:
        raise HTTPException(status_code=403, detail="Access denied")

    # Don't allow deleting self
    if str(target_user["_id"]) == user["user_id"]:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")

    # Soft delete - deactivate
    await db.users.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"active_status": False, "updated_at": datetime.now(timezone.utc)}}
    )
    return {"message": "User deactivated successfully"}


# ============================================
# PROJECT ENDPOINTS
# (Canonical implementation moved to project_management_routes.py)
# ============================================

# DERIVED FINANCIAL STATE ENDPOINTS
# ============================================
@api_router.get("/financial-state")
async def get_financial_state(
    project_id: str,
    category_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get derived financial state for project"""
    user = await permission_checker.get_authenticated_user(current_user)
    await permission_checker.check_project_access(user, project_id, require_write=False)

    query = {"project_id": project_id}
    if category_id:
        query["category_id"] = category_id

    states = await db.financial_state.find(query).to_list(length=None)
    for s in states:
        s["state_id"] = str(s.pop("_id"))
    return states


# ============================================
# USER-PROJECT MAPPING ENDPOINTS
# ============================================
@api_router.post("/mappings", status_code=status.HTTP_201_CREATED)
async def create_mapping(
    mapping_data: UserProjectMapCreate,
    current_user: dict = Depends(get_current_user)
):
    """Create user-project mapping (Admin only)"""
    user = await permission_checker.get_authenticated_user(current_user)
    await permission_checker.check_admin_role(user)

    # Verify user and project exist
    target_user = await db.users.find_one({"_id": ObjectId(mapping_data.user_id)})
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    project = await db.projects.find_one({"_id": ObjectId(mapping_data.project_id)})
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    # Check if mapping already exists
    existing = await db.user_project_map.find_one({
        "user_id": mapping_data.user_id,
        "project_id": mapping_data.project_id
    })
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mapping already exists"
        )

    mapping_dict = mapping_data.dict()
    mapping_dict["organisation_id"] = user["organisation_id"]
    mapping_dict["created_at"] = datetime.now(timezone.utc)

    result = await db.user_project_map.insert_one(mapping_dict)
    map_id = str(result.inserted_id)

    # Audit log
    await audit_service.log_action(
        organisation_id=user["organisation_id"],
        module_name="ACCESS_CONTROL",
        entity_type="USER_PROJECT_MAP",
        entity_id=map_id,
        action_type="CREATE",
        user_id=user["user_id"],
        project_id=mapping_data.project_id,
        new_value={"user_id": mapping_data.user_id, "project_id": mapping_data.project_id}
    )

    mapping_dict["map_id"] = map_id
    # Remove MongoDB _id to avoid serialization issues
    if "_id" in mapping_dict:
        del mapping_dict["_id"]
    return mapping_dict


@api_router.get("/mappings")
async def get_mappings(
    user_id: Optional[str] = None,
    project_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get user-project mappings"""
    user = await permission_checker.get_authenticated_user(current_user)
    query = {"organisation_id": user["organisation_id"]}
    if user_id:
        query["user_id"] = user_id
    if project_id:
        query["project_id"] = project_id

    mappings = await db.user_project_map.find(query).to_list(length=None)
    for m in mappings:
        m["map_id"] = str(m.pop("_id"))
    return mappings


@api_router.delete("/mappings/{map_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_mapping(
    map_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete user-project mapping (Admin only)"""
    user = await permission_checker.get_authenticated_user(current_user)
    await permission_checker.check_admin_role(user)

    mapping = await db.user_project_map.find_one({
        "_id": ObjectId(map_id),
        "organisation_id": user["organisation_id"]
    })
    if not mapping:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied or mapping not found"
        )

    await db.user_project_map.delete_one({"_id": ObjectId(map_id)})

    # Audit log
    await audit_service.log_action(
        organisation_id=user["organisation_id"],
        module_name="ACCESS_CONTROL",
        entity_type="USER_PROJECT_MAP",
        entity_id=map_id,
        action_type="DELETE",
        user_id=user["user_id"],
        project_id=mapping["project_id"]
    )
    return None


# ============================================
# AUDIT LOG ENDPOINTS (READ ONLY)
# ============================================
@api_router.get("/audit-logs")
async def get_audit_logs(
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    project_id: Optional[str] = None,
    limit: int = 100,
    current_user: dict = Depends(get_current_user)
):
    """Get audit logs (Admin only)"""
    user = await permission_checker.get_authenticated_user(current_user)
    await permission_checker.check_admin_role(user)

    logs = await audit_service.get_audit_logs(
        organisation_id=user["organisation_id"],
        entity_type=entity_type,
        entity_id=entity_id,
        project_id=project_id,
        limit=limit
    )
    return logs


# ============================================
# PETTY CASH ENDPOINTS
# ============================================
@api_router.get("/petty-cash")
async def get_petty_cash(
    project_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get petty cash entries"""
    user = await permission_checker.get_authenticated_user(current_user)
    query = {"organisation_id": user["organisation_id"]}
    if project_id:
        query["project_id"] = project_id

    entries = await db.petty_cash.find(query).sort("date", -1).to_list(length=100)
    for entry in entries:
        entry["petty_cash_id"] = str(entry.pop("_id"))
    return entries


@api_router.post("/petty-cash", status_code=status.HTTP_201_CREATED)
async def create_petty_cash(
    data: dict,
    current_user: dict = Depends(get_current_user)
):
    """Create petty cash entry"""
    user = await permission_checker.get_authenticated_user(current_user)
    entry = {
        "organisation_id": user["organisation_id"],
        "project_id": data.get("project_id"),
        "date": datetime.fromisoformat(
            data.get("date").replace("Z", "+00:00")
        ) if isinstance(data.get("date"), str) else data.get("date"),
        "description": data.get("description"),
        "amount": float(data.get("amount", 0)),
        "type": data.get("type", "expense"),
        "category": data.get("category", "general"),
        "receipt_url": data.get("receipt_url"),
        "status": "pending",
        "created_by": user["user_id"],
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }
    result = await db.petty_cash.insert_one(entry)
    entry["petty_cash_id"] = str(result.inserted_id)
    if "_id" in entry:
        del entry["_id"]
    return entry


@api_router.put("/petty-cash/{entry_id}")
async def update_petty_cash(
    entry_id: str,
    data: dict,
    current_user: dict = Depends(get_current_user)
):
    """Update petty cash entry"""
    user = await permission_checker.get_authenticated_user(current_user)
    existing = await db.petty_cash.find_one({
        "_id": ObjectId(entry_id),
        "organisation_id": user["organisation_id"]
    })
    if not existing:
        raise HTTPException(status_code=403, detail="Access denied or entry not found")

    update_data = {
        "description": data.get("description", existing.get("description")),
        "amount": float(data.get("amount", existing.get("amount"))),
        "type": data.get("type", existing.get("type")),
        "category": data.get("category", existing.get("category")),
        "updated_at": datetime.now(timezone.utc)
    }
    await db.petty_cash.update_one({"_id": ObjectId(entry_id)}, {"$set": update_data})
    updated = await db.petty_cash.find_one({"_id": ObjectId(entry_id)})
    updated["petty_cash_id"] = str(updated.pop("_id"))
    return updated


@api_router.delete("/petty-cash/{entry_id}")
async def delete_petty_cash(
    entry_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete petty cash entry"""
    user = await permission_checker.get_authenticated_user(current_user)
    existing = await db.petty_cash.find_one({
        "_id": ObjectId(entry_id),
        "organisation_id": user["organisation_id"]
    })
    if not existing:
        raise HTTPException(status_code=403, detail="Access denied or entry not found")

    await db.petty_cash.delete_one({"_id": ObjectId(entry_id)})
    return {"message": "Entry deleted successfully"}


@api_router.post("/petty-cash/{entry_id}/approve")
async def approve_petty_cash(
    entry_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Approve petty cash entry"""
    user = await permission_checker.get_authenticated_user(current_user)
    await permission_checker.check_admin_role(user)

    result = await db.petty_cash.update_one(
        {"_id": ObjectId(entry_id), "organisation_id": user["organisation_id"]},
        {"$set": {"status": "approved", "approved_by": user["user_id"], "updated_at": datetime.now(timezone.utc)}}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=403, detail="Access denied or entry not found")
    return {"message": "Entry approved"}


# ============================================
# ORGANIZATION SETTINGS
# ============================================
# (Organisation settings handled by settings_routes.py)


# ============================================
# HEALTH CHECK
# ============================================

# ============================================
# WORKERS DAILY LOG ENDPOINTS
# ============================================
@api_router.post("/worker-logs", status_code=status.HTTP_201_CREATED)
async def create_worker_log(
    log_data: WorkersDailyLogCreate,
    current_user: dict = Depends(get_current_user)
):
    """Create or update a workers daily log (Supervisor)"""
    user = await permission_checker.get_authenticated_user(current_user)

    # Check if log already exists for this date and project
    existing = await db.worker_logs.find_one({
        "project_id": log_data.project_id,
        "date": log_data.date,
        "supervisor_id": user["user_id"]
    })

    # Calculate totals from new entries format or legacy workers format
    if log_data.entries:
        total_workers = sum(e.workers_count for e in log_data.entries)
        entries_data = [e.dict() for e in log_data.entries]
    else:
        total_workers = len(log_data.workers)
        entries_data = []

    total_hours = sum(w.hours_worked for w in log_data.workers) if log_data.workers else 0

    if existing:
        # Update existing log
        update_dict = {
            "entries": entries_data,
            "workers": [w.dict() for w in log_data.workers],
            "total_workers": log_data.total_workers if log_data.total_workers else total_workers,
            "total_hours": total_hours,
            "weather": log_data.weather,
            "site_conditions": log_data.site_conditions,
            "remarks": log_data.remarks,
            "status": "submitted",
            "updated_at": datetime.now(timezone.utc)
        }
        await db.worker_logs.update_one(
            {"_id": existing["_id"]},
            {"$set": update_dict}
        )
        updated = await db.worker_logs.find_one({"_id": existing["_id"]})
        updated["log_id"] = str(updated.pop("_id"))
        return updated

    log_dict = {
        "organisation_id": user["organisation_id"],
        "project_id": log_data.project_id,
        "date": log_data.date,
        "supervisor_id": user["user_id"],
        "supervisor_name": user["name"],
        "entries": entries_data,
        "workers": [w.dict() for w in log_data.workers],
        "total_workers": log_data.total_workers if log_data.total_workers else total_workers,
        "total_hours": total_hours,
        "weather": log_data.weather,
        "site_conditions": log_data.site_conditions,
        "remarks": log_data.remarks,
        "status": "submitted",
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }
    result = await db.worker_logs.insert_one(log_dict)
    log_dict["log_id"] = str(result.inserted_id)
    if "_id" in log_dict:
        del log_dict["_id"]
    return log_dict


@api_router.get("/worker-logs")
async def get_worker_logs(
    project_id: Optional[str] = None,
    date: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    supervisor_id: Optional[str] = None,
    vendor: Optional[str] = None,
    status: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get workers daily logs with optional filters"""
    user = await permission_checker.get_authenticated_user(current_user)
    query = {"organisation_id": user["organisation_id"]}
    if project_id:
        query["project_id"] = project_id

    # Date filters
    if date:
        query["date"] = date
    elif start_date or end_date:
        date_query = {}
        if start_date:
            date_query["$gte"] = start_date
        if end_date:
            date_query["$lte"] = end_date
        query["date"] = date_query

    if supervisor_id:
        query["supervisor_id"] = supervisor_id
    if vendor:
        query["entries.vendor_name"] = {"$regex": vendor, "$options": "i"}
    if status:
        query["status"] = status

    logs = await db.worker_logs.find(query).sort("date", -1).to_list(length=100)
    for log in logs:
        log["log_id"] = str(log.pop("_id"))
    return logs


@api_router.get("/worker-logs/{log_id}")
async def get_worker_log(
    log_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get a specific worker log by ID"""
    user = await permission_checker.get_authenticated_user(current_user)
    log = await db.worker_logs.find_one({
        "_id": ObjectId(log_id),
        "organisation_id": user["organisation_id"]
    })
    if not log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Worker log not found"
        )
    log["log_id"] = str(log.pop("_id"))
    return log


@api_router.put("/worker-logs/{log_id}")
async def update_worker_log(
    log_id: str,
    update_data: WorkersDailyLogUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update a workers daily log"""
    user = await permission_checker.get_authenticated_user(current_user)
    log = await db.worker_logs.find_one({
        "_id": ObjectId(log_id),
        "organisation_id": user["organisation_id"]
    })
    if not log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Worker log not found"
        )

    # Prepare update
    update_dict = {}
    if update_data.workers is not None:
        update_dict["workers"] = [w.dict() for w in update_data.workers]
        update_dict["total_workers"] = len(update_data.workers)
        update_dict["total_hours"] = sum(w.hours_worked for w in update_data.workers)
    if update_data.weather is not None:
        update_dict["weather"] = update_data.weather
    if update_data.site_conditions is not None:
        update_dict["site_conditions"] = update_data.site_conditions
    if update_data.remarks is not None:
        update_dict["remarks"] = update_data.remarks
    if update_data.status is not None:
        update_dict["status"] = update_data.status
    update_dict["updated_at"] = datetime.now(timezone.utc)

    await db.worker_logs.update_one(
        {"_id": ObjectId(log_id)},
        {"$set": update_dict}
    )
    updated_log = await db.worker_logs.find_one({"_id": ObjectId(log_id)})
    updated_log["log_id"] = str(updated_log.pop("_id"))
    return updated_log


@api_router.get("/worker-logs/check/{project_id}/{date}")
async def check_worker_log_exists(
    project_id: str,
    date: str,
    current_user: dict = Depends(get_current_user)
):
    """Check if worker log exists for a specific date and project"""
    user = await permission_checker.get_authenticated_user(current_user)
    log = await db.worker_logs.find_one({
        "project_id": project_id,
        "date": date,
        "supervisor_id": user["user_id"]
    })
    return {
        "exists": log is not None,
        "log_id": str(log["_id"]) if log else None,
        "status": log.get("status") if log else None
    }


@api_router.get("/worker-logs/report/summary")
async def get_worker_logs_summary(
    project_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get summary report of worker logs for admin"""
    user = await permission_checker.get_authenticated_user(current_user)
    await permission_checker.check_admin_role(user)

    query = {"organisation_id": user["organisation_id"]}
    if project_id:
        query["project_id"] = project_id
    if start_date:
        query["date"] = {"$gte": start_date}
    if end_date:
        if "date" in query:
            query["date"]["$lte"] = end_date
        else:
            query["date"] = {"$lte": end_date}

    logs = await db.worker_logs.find(query).to_list(length=1000)

    # Calculate summary statistics
    total_logs = len(logs)
    total_workers = sum(log.get("total_workers", 0) for log in logs)
    total_hours = sum(log.get("total_hours", 0) for log in logs)

    # Group by skill type
    skill_breakdown = {}
    for log in logs:
        for worker in log.get("workers", []):
            skill = worker.get("skill_type", "Unknown")
            if skill not in skill_breakdown:
                skill_breakdown[skill] = {"count": 0, "hours": 0}
            skill_breakdown[skill]["count"] += 1
            skill_breakdown[skill]["hours"] += worker.get("hours_worked", 0)

    return {
        "total_logs": total_logs,
        "total_workers": total_workers,
        "total_hours": total_hours,
        "skill_breakdown": skill_breakdown,
        "date_range": {
            "start": start_date,
            "end": end_date
        }
    }


@api_router.get("/auth/can-logout")
async def check_can_logout(
    current_user: dict = Depends(get_current_user)
):
    """Check if supervisor can logout - requires submitted worker log for today if checked in"""
    user = await permission_checker.get_authenticated_user(current_user)

    # Admins can always logout
    if user.get("role") == "Admin":
        return {"can_logout": True, "reason": None}

    # For supervisors, check if worker log is submitted for today
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Get user's assigned projects
    assigned_projects = user.get("assigned_projects", [])
    if not assigned_projects:
        # No projects assigned, can logout
        return {"can_logout": True, "reason": None}

    # Check if user has checked in today (by looking for any worker log activity)
    any_log_today = await db.worker_logs.find_one({
        "supervisor_id": user["user_id"],
        "date": today
    })

    # If no worker log exists for today, user hasn't started work - allow logout
    if not any_log_today:
        return {"can_logout": True, "reason": None}

    # User has started work - check if there's a submitted DPR
    dpr_log = await db.dpr.find_one({
        "supervisor_id": user["user_id"],
        "dpr_date": datetime.strptime(today, "%Y-%m-%d"),
    })
    if dpr_log and str(dpr_log.get("status", "")).lower() == "submitted":
        return {"can_logout": True, "reason": None}

    # Check if there's at least a draft DPR
    has_draft = dpr_log is not None and dpr_log.get("status") == "Draft"
    return {
        "can_logout": False,
        "reason": "dpr_required",
        "message": "Please submit your Daily Progress Report (DPR) before logging out.",
        "has_draft": has_draft,
        "draft_log_id": str(dpr_log["_id"]) if dpr_log else None
    }


# ============================================
# NOTIFICATION ENDPOINTS
# ============================================
@api_router.post("/notifications", status_code=status.HTTP_201_CREATED)
async def create_notification(
    notification_data: NotificationCreate,
    current_user: dict = Depends(get_current_user)
):
    """Create a new notification (internal use or admin)"""
    user = await permission_checker.get_authenticated_user(current_user)
    notification_doc = {
        "organisation_id": user["organisation_id"],
        "recipient_role": notification_data.recipient_role,
        "recipient_user_id": notification_data.recipient_user_id,
        "title": notification_data.title,
        "message": notification_data.message,
        "notification_type": notification_data.notification_type,
        "priority": notification_data.priority,
        "reference_type": notification_data.reference_type,
        "reference_id": notification_data.reference_id,
        "project_id": notification_data.project_id,
        "project_name": notification_data.project_name,
        "sender_id": user["user_id"],
        "sender_name": user.get("name", "System"),
        "is_read": False,
        "read_at": None,
        "created_at": datetime.now(timezone.utc)
    }
    result = await db.notifications.insert_one(notification_doc)
    return {
        "notification_id": str(result.inserted_id),
        "status": "created"
    }


@api_router.get("/notifications")
async def get_notifications(
    limit: int = 50,
    unread_only: bool = False,
    current_user: dict = Depends(get_current_user)
):
    """Get notifications for current user (based on role)"""
    user = await permission_checker.get_authenticated_user(current_user)

    # Build query
    query = {
        "organisation_id": user["organisation_id"],
        "$or": [
            {"recipient_role": user["role"].lower()},
            {"recipient_user_id": user["user_id"]}
        ]
    }
    if unread_only:
        query["is_read"] = False

    # Fetch notifications sorted by created_at (newest first)
    cursor = db.notifications.find(query).sort("created_at", -1).limit(limit)
    notifications = await cursor.to_list(length=limit)

    # Get unread count
    unread_count = await db.notifications.count_documents({
        "organisation_id": user["organisation_id"],
        "$or": [
            {"recipient_role": user["role"].lower()},
            {"recipient_user_id": user["user_id"]}
        ],
        "is_read": False
    })

    return {
        "notifications": [serialize_doc(n) for n in notifications],
        "unread_count": unread_count,
        "total": len(notifications)
    }


@api_router.put("/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Mark a notification as read"""
    user = await permission_checker.get_authenticated_user(current_user)
    result = await db.notifications.update_one(
        {
            "_id": ObjectId(notification_id),
            "organisation_id": user["organisation_id"]
        },
        {"$set": {"is_read": True, "read_at": datetime.now(timezone.utc)}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"status": "marked_read"}


@api_router.put("/notifications/mark-all-read")
async def mark_all_notifications_read(
    current_user: dict = Depends(get_current_user)
):
    """Mark all notifications as read for current user"""
    user = await permission_checker.get_authenticated_user(current_user)
    result = await db.notifications.update_many(
        {
            "organisation_id": user["organisation_id"],
            "$or": [
                {"recipient_role": user["role"].lower()},
                {"recipient_user_id": user["user_id"]}
            ],
            "is_read": False
        },
        {"$set": {"is_read": True, "read_at": datetime.now(timezone.utc)}}
    )
    return {"status": "success", "marked_count": result.modified_count}


@api_router.get("/notifications/unread-count")
async def get_unread_count(
    current_user: dict = Depends(get_current_user)
):
    """Get unread notification count for badge display"""
    user = await permission_checker.get_authenticated_user(current_user)
    count = await db.notifications.count_documents({
        "organisation_id": user["organisation_id"],
        "$or": [
            {"recipient_role": user["role"].lower()},
            {"recipient_user_id": user["user_id"]}
        ],
        "is_read": False
    })
    return {"unread_count": count}


@api_router.get("/projects", response_model=List[Project])
async def list_projects(current_user: dict = Depends(get_current_user)):
    """Fetch all projects for the user's organisation."""
    user = await permission_checker.get_authenticated_user(current_user)
    
    org_id = user.get("organisation_id")
    if not org_id:
        logging.error(f"User {user.get('user_id')} has no organisation_id assigned")
        raise HTTPException(status_code=400, detail="User has no organization assigned")
        
    logging.info(f"Fetching projects for org: {org_id}")
    
    # 6.3 check
    await permission_checker.check_web_crm_access(user)
    
    projects = await db.projects.find({"organisation_id": org_id}).to_list(length=1000)
    for p in projects:
        p["project_id"] = str(p["_id"])
    return [serialize_doc(p) for p in projects]


@api_router.get("/projects/{project_id}", response_model=Project)
async def get_project(project_id: str, current_user: dict = Depends(get_current_user)):
    """Fetch details for a single project."""
    user = await permission_checker.get_authenticated_user(current_user)
    
    # 6.3 check
    await permission_checker.check_web_crm_access(user)
    
    # Check project access (this also validates organisation isolation)
    await permission_checker.check_project_access(user, project_id, require_write=False)
    
    # Try finding by project_id field first, then by string ObjectId
    project = await db.projects.find_one({"project_id": project_id})
    if not project:
        try:
            project = await db.projects.find_one({"_id": ObjectId(project_id)})
        except:
            pass
            
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
        
    project["project_id"] = str(project["_id"])
    return serialize_doc(project)


@api_router.put("/projects/{project_id}")
async def update_project(
    project_id: str,
    project_data: ProjectUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update project details."""
    try:
        user = await permission_checker.get_authenticated_user(current_user)

        # Check web CRM access and admin role
        await permission_checker.check_web_crm_access(user)
        await permission_checker.check_admin_role(user)

        # Check if project access (this also validates organisation isolation)
        await permission_checker.check_project_access(user, project_id, require_write=True)

        # Build update dict - only include non-null values
        update_dict = {k: v for k, v in project_data.dict(exclude_unset=True).items() if v is not None}
        update_dict["updated_at"] = datetime.now(timezone.utc)

        # Find and update - support both ObjectId and project_id string
        try:
            query = {"_id": ObjectId(project_id)}
        except ValueError:
            query = {"project_id": project_id}

        result = await db.projects.find_one_and_update(
            query,
            {"$set": update_dict},
            return_document=True
        )

        if not result:
            raise HTTPException(status_code=404, detail="Project not found")

        # Audit log - wrapped in try/catch to not block the response
        try:
            await audit_service.log_action(
                organisation_id=user["organisation_id"],
                module_name="PROJECT_MANAGEMENT",
                entity_type="PROJECT",
                entity_id=project_id,
                action_type="UPDATE",
                user_id=user["user_id"],
                new_value=serialize_doc(update_dict)
            )
        except Exception as audit_err:
            logger.warning(f"Failed to log audit for project update {project_id}: {audit_err}")
            # Continue without blocking the response

        # Serialize and return the updated project
        serialized = serialize_doc(result)
        # Ensure project_id field is set for frontend
        if serialized and "_id" in serialized:
            serialized["project_id"] = serialized["_id"]
        return serialized

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating project {project_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update project: {str(e)}")


@api_router.get("/projects/{project_id}/budgets")
async def get_project_budgets(
    project_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get all budgets for a project."""
    user = await permission_checker.get_authenticated_user(current_user)

    # Check web CRM access
    await permission_checker.check_web_crm_access(user)

    # Check project access
    await permission_checker.check_project_access(user, project_id)

    # Fetch project budgets - support both ObjectId and project_id string
    try:
        query = {"_id": ObjectId(project_id)}
    except ValueError:
        query = {"project_id": project_id}

    try:
        budgets = await db.project_category_budgets.find(query).to_list(length=100)
        # Serialize and return - map category_id to code_id for frontend compatibility
        result = []
        for b in budgets:
            serialized = serialize_doc(b)
            # Map category_id to code_id for frontend compatibility
            if "category_id" in serialized:
                serialized["code_id"] = serialized["category_id"]
            result.append(serialized)
        return result
    except Exception as e:
        logger.error(f"Error fetching budgets for project {project_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch budgets: {str(e)}")


@api_router.post("/projects/{project_id}/budgets", response_model=ProjectBudget)
async def create_or_update_project_budget(
    project_id: str,
    budget_data: dict,  # Accept raw dict to support both code_id and category_id
    current_user: dict = Depends(get_current_user)
):
    """Create or update a budget allocation for a project category."""
    try:
        user = await permission_checker.get_authenticated_user(current_user)

        # 6.3 checks
        await permission_checker.check_web_crm_access(user)
        await permission_checker.check_client_readonly(user)
        await permission_checker.check_admin_role(user)

        # Check project access
        await permission_checker.check_project_access(user, project_id, require_write=True)

        # Support both code_id (from frontend) and category_id (from API spec)
        category_id = budget_data.get("category_id") or budget_data.get("code_id")
        if not category_id:
            raise HTTPException(status_code=400, detail="category_id or code_id is required")

        original_budget = budget_data.get("original_budget")
        if original_budget is None:
            raise HTTPException(status_code=400, detail="original_budget is required")

        # Check if category exists
        category = await db.code_master.find_one({"_id": ObjectId(category_id)})
        if not category:
            raise HTTPException(status_code=404, detail="Category not found")

        # Build budget dict
        budget_dict = {
            "project_id": project_id,
            "category_id": category_id,
            "organisation_id": user["organisation_id"],
            "updated_at": datetime.now(timezone.utc),
            "original_budget": Decimal128(str(original_budget)),
            "description": budget_data.get("description")
        }

        # Upsert logic
        query = {"project_id": project_id, "category_id": category_id}
        existing = await db.project_category_budgets.find_one(query)

        if existing:
            # Update
            await db.project_category_budgets.update_one(
                {"_id": existing["_id"]},
                {"$set": {
                    "original_budget": Decimal128(str(original_budget)),
                    "description": budget_data.get("description"),
                    "updated_at": datetime.now(timezone.utc)
                }}
            )
            result = await db.project_category_budgets.find_one({"_id": existing["_id"]})
        else:
            # Create
            budget_dict["created_at"] = datetime.now(timezone.utc)
            budget_dict["committed_amount"] = Decimal128("0.0")
            budget_dict["remaining_budget"] = Decimal128(str(original_budget))
            budget_dict["version"] = 1

            insert_res = await db.project_category_budgets.insert_one(budget_dict)
            result = await db.project_category_budgets.find_one({"_id": insert_res.inserted_id})

        # Recalculate project financials after budget change
        await financial_service.recalculate_all_project_financials(project_id)

        return serialize_doc(result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating/updating budget for project {project_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save budget: {str(e)}")


@api_router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc),
        "version": "1.0.0",
        "phase": "Phase 2 - Refactor"
    }


# Include router in main app
app.include_router(site_operations_router)
app.include_router(dpr_router)
app.include_router(attendance_router)
app.include_router(voice_log_router)
app.include_router(reporting_router)
app.include_router(site_overheads_router)
app.include_router(api_router)

# Include Phase 2 hardened routes
app.include_router(hardened_router)

# Include Phase 2 Wave 2 lifecycle routes
app.include_router(financial_router)

# Include Phase 2 Wave 3 routes
app.include_router(project_management_router)

# Register vendor router
app.include_router(vendor_router)

# Register work order router
app.include_router(work_order_router)
app.include_router(work_order_project_router)

# Register Payment Certificate router
app.include_router(pc_router)

# Register Cash Transaction (Liquidity) router
app.include_router(cash_router)

# Register Global Settings router
app.include_router(settings_router)

# Serve frontend static files
frontend_build = os.path.join(
    os.path.dirname(__file__), "../mobile/frontend/dist")
if os.path.exists(frontend_build):
    app.mount(
        "/",
        StaticFiles(directory=frontend_build, html=True),
        name="static"
    )


@app.on_event("shutdown")
async def shutdown_db_client():
    db_manager.disconnect()
