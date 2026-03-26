from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status
import secrets
import hashlib
import logging

from app.core.config import settings
from app.repositories.auth_repo import TokenBlacklistRepository, RefreshTokenRepository
from app.repositories.user_repo import UserRepository
from app.schemas.auth import Token, LoginRequest
from app.schemas.user import UserResponse

logger = logging.getLogger(__name__)

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def generate_jti() -> str:
    """Generate a unique JWT ID (jti) for token revocation."""
    return secrets.token_urlsafe(32)

class AuthService:
    """Standalone service for authentication and token management"""
    
    def __init__(self, db=None):
        if db:
            self.blacklist_repo = TokenBlacklistRepository(db)
            self.refresh_repo = RefreshTokenRepository(db)
            self.user_repo = UserRepository(db)

    @staticmethod
    def hash_password(password: str) -> str:
        return pwd_context.hash(password)

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
        to_encode = data.copy()
        jti = generate_jti()
        to_encode["jti"] = jti
        
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode.update({
            "exp": expire,
            "iat": datetime.now(timezone.utc),
            "type": "access"
        })
        return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.ALGORITHM)

    @staticmethod
    def create_refresh_token(user_id: str, expires_delta: Optional[timedelta] = None) -> str:
        jti = generate_jti()
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        
        to_encode = {
            "user_id": user_id,
            "jti": jti,
            "exp": expire,
            "iat": datetime.now(timezone.utc),
            "type": "refresh"
        }
        return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.ALGORITHM)

    @staticmethod
    def decode_token(token: str, token_type: str = "access") -> dict:
        try:
            payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.ALGORITHM])
            if payload.get("type") != token_type:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=f"Invalid token type. Expected {token_type}"
                )
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials"
            )

    async def login(self, login_data: LoginRequest) -> Token:
        """Business logic for user login"""
        # Find user by email
        user = await self.user_repo.get_by_email(login_data.email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )

        # Verify password
        if not self.verify_password(login_data.password, user["hashed_password"]):
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
        user_id = user["id"]
        token_data = {
            "user_id": user_id,
            "email": user["email"],
            "role": user["role"],
            "organisation_id": user["organisation_id"]
        }
        access_token = self.create_access_token(data=token_data)
        refresh_token = self.create_refresh_token(user_id=user_id)

        # Store refresh token
        refresh_payload = self.decode_token(refresh_token, "refresh")
        await self.refresh_repo.create({
            "jti": refresh_payload["jti"],
            "user_id": user_id,
            "is_revoked": False,
            "expires_at": datetime.fromtimestamp(refresh_payload["exp"], tz=timezone.utc)
        })

        user_res = UserResponse(**user)
        return Token(
            access_token=access_token,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=user_res
        )

    async def refresh_token(self, refresh_token: str) -> Token:
        """Business logic for refreshing access token"""
        try:
            payload = self.decode_token(refresh_token, "refresh")
            jti = payload["jti"]
            user_id = payload["user_id"]

            token_doc = await self.refresh_repo.find_one({
                "jti": jti,
                "user_id": user_id,
                "is_revoked": False
            })
            if not token_doc:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Refresh token is invalid or has been revoked"
                )

            user = await self.user_repo.get_by_id(user_id)
            if not user or not user.get("active_status", False):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found or inactive"
                )

            # Revoke old refresh token
            await self.refresh_repo.update_one({"jti": jti}, {"$set": {"is_revoked": True}})

            # Create new tokens
            token_data = {
                "user_id": user_id,
                "email": user["email"],
                "role": user["role"],
                "organisation_id": user["organisation_id"]
            }
            access_token = self.create_access_token(data=token_data)
            new_refresh_token = self.create_refresh_token(user_id=user_id)

            # Store new refresh token
            new_payload = self.decode_token(new_refresh_token, "refresh")
            await self.refresh_repo.create({
                "jti": new_payload["jti"],
                "user_id": user_id,
                "is_revoked": False,
                "expires_at": datetime.fromtimestamp(new_payload["exp"], tz=timezone.utc)
            })

            return Token(
                access_token=access_token,
                expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
                user=UserResponse(**user)
            )
        except Exception as e:
            logger.error(f"Token refresh failed: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not refresh token"
            )

    async def revoke_token(self, jti: str, token_type: str) -> None:
        await self.blacklist_repo.create({
            "jti": jti,
            "token_type": token_type,
            "revoked_at": datetime.now(timezone.utc)
        })

    async def is_token_revoked(self, jti: str) -> bool:
        return await self.blacklist_repo.find_one({"jti": jti}) is not None

    async def revoke_all_user_tokens(self, user_id: str) -> None:
        await self.refresh_repo.update_many(
            {"user_id": user_id, "is_revoked": False},
            {"$set": {"is_revoked": True, "revoked_at": datetime.now(timezone.utc)}}
        )

    async def logout(self, user_payload: dict, refresh_token: Optional[str]) -> dict:
        """Business logic for user logout"""
        jti = user_payload.get("jti")
        if jti:
            await self.revoke_token(jti, "access")

        if refresh_token:
            try:
                payload = self.decode_token(refresh_token, "refresh")
                await self.revoke_token(payload["jti"], "refresh")
                await self.refresh_repo.update_one(
                    {"jti": payload["jti"]},
                    {"$set": {"is_revoked": True}}
                )
            except:
                pass
        
        return {"status": "success"}
