from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from app.modules.shared.domain.exceptions import AuthenticationError, PermissionDeniedError, ValidationError
import secrets
import logging

from app.core.config import settings
from ..infrastructure.repository import TokenBlacklistRepository, RefreshTokenRepository, UserRepository
from ..schemas.dto import Token, LoginRequest, UserResponse
from app.core.time import now

logger = logging.getLogger(__name__)

class AuthService:
    """
    Sovereign Auth Orchestrator for Identity Context.
    Enforces Clock Skew tolerance and strict rotation policies.
    """
    
    def __init__(self, db, config=settings):
        self.config = config
        self.blacklist_repo = TokenBlacklistRepository(db)
        self.refresh_repo = RefreshTokenRepository(db)
        self.user_repo = UserRepository(db)
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    def hash_password(self, password: str) -> str:
        return self.pwd_context.hash(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        return self.pwd_context.verify(plain_password, hashed_password)

    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """Create token with logic versioning."""
        to_encode = data.copy()
        jti = secrets.token_urlsafe(32)
        to_encode["jti"] = jti
        
        expire_at = now() + (expires_delta or timedelta(minutes=self.config.ACCESS_TOKEN_EXPIRE_MINUTES))
        
        to_encode.update({
            "exp": expire_at,
            "iat": now(),
            "type": "access",
            "v": 1 # Token Logic Version
        })
        return jwt.encode(to_encode, self.config.JWT_SECRET_KEY, algorithm=self.config.ALGORITHM)

    def create_refresh_token(self, user_id: str, expires_delta: Optional[timedelta] = None) -> str:
        expire_at = now() + (expires_delta or timedelta(days=self.config.REFRESH_TOKEN_EXPIRE_DAYS))
        to_encode = {
            "user_id": user_id,
            "jti": secrets.token_urlsafe(32),
            "exp": expire_at,
            "iat": now(),
            "type": "refresh"
        }
        return jwt.encode(to_encode, self.config.JWT_SECRET_KEY, algorithm=self.config.ALGORITHM)

    async def decode_token(self, token: str, token_type: str = "access", check_revocation: bool = True) -> Dict[str, Any]:
        """Hard Decryption with Clock Skew Handling."""
        try:
            payload = jwt.decode(
                token, 
                self.config.JWT_SECRET_KEY, 
                algorithms=[self.config.ALGORITHM],
                options={"leeway": 30} 
            )
            
            if payload.get("type") != token_type:
                raise AuthenticationError(f"AUTH_ERROR: Invalid purpose ({token_type} expected).")
            
            if check_revocation:
                jti = payload.get("jti")
                if jti and await self.is_token_revoked(jti):
                    raise AuthenticationError("AUTH_ERROR: Identity has been retired.")
                    
            return payload
        except JWTError:
            raise AuthenticationError("AUTH_ERROR: Identity cannot be verified or expired.")

    async def login(self, login_data: LoginRequest) -> Token:
        user = await self.user_repo.get_by_email(login_data.email)
        if not user or not self.verify_password(login_data.password, user["hashed_password"]):
            raise AuthenticationError("INVALID_CREDENTIALS")

        if not user.get("active_status", False):
            raise PermissionDeniedError("ACCOUNT_DISABLED")

        user_id = user["_id"]
        user["user_id"] = user_id
        token_data = {
            "user_id": user_id,
            "organisation_id": user["organisation_id"],
            "role": user["role"]
        }
        
        access_token = self.create_access_token(data=token_data)
        refresh_token = self.create_refresh_token(user_id=user_id)

        # Session Persistence
        refresh_payload = jwt.decode(refresh_token, self.config.JWT_SECRET_KEY, options={"verify_exp": False})
        await self.refresh_repo.create({
            "jti": refresh_payload["jti"],
            "user_id": user_id,
            "is_revoked": False,
            "expires_at": datetime.fromtimestamp(refresh_payload["exp"], tz=timezone.utc)
        })

        return Token(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=self.config.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=UserResponse(**user)
        )

    async def refresh_token(self, refresh_token: str) -> Token:
        payload = await self.decode_token(refresh_token, "refresh")
        jti = payload["jti"]
        user_id = payload["user_id"]

        token_doc = await self.refresh_repo.find_one({"jti": jti, "user_id": user_id, "is_revoked": False})
        if not token_doc:
            raise AuthenticationError("SESSION_EXPIRED")

        user = await self.user_repo.get_by_id(user_id)
        if not user or not user.get("active_status", False):
             raise AuthenticationError("IDENTITY_INACTIVE")

        await self.refresh_repo.update_one({"jti": jti}, {"$set": {"is_revoked": True}})

        user["user_id"] = user["_id"]
        token_data = {"user_id": user_id, "organisation_id": user["organisation_id"], "role": user["role"]}
        new_access = self.create_access_token(data=token_data)
        new_refresh = self.create_refresh_token(user_id=user_id)

        new_payload = jwt.decode(new_refresh, self.config.JWT_SECRET_KEY, options={"verify_exp": False})
        await self.refresh_repo.create({
            "jti": new_payload["jti"],
            "user_id": user_id,
            "is_revoked": False,
            "expires_at": datetime.fromtimestamp(new_payload["exp"], tz=timezone.utc)
        })

        return Token(
            access_token=new_access,
            refresh_token=new_refresh,
            expires_in=self.config.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=UserResponse(**user)
        )

    async def is_token_revoked(self, jti: str) -> bool:
        return await self.blacklist_repo.find_one({"jti": jti}) is not None

    async def revoke_token(self, jti: str, token_type: str) -> None:
        await self.blacklist_repo.create({
            "jti": jti,
            "token_type": token_type,
            "revoked_at": now()
        })

    async def logout(self, user_payload: dict, refresh_token: Optional[str]) -> Dict[str, str]:
        jti = user_payload.get("jti")
        if jti: await self.revoke_token(jti, "access")
        if refresh_token:
            try:
                payload = await self.decode_token(refresh_token, "refresh")
                await self.revoke_token(payload["jti"], "refresh")
                await self.refresh_repo.update_one({"jti": payload["jti"]}, {"$set": {"is_revoked": True}})
            except: pass
        return {"status": "SUCCESS"}
