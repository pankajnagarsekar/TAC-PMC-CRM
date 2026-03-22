"""
Authentication module for JWT token management.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status, Depends, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import os
import secrets
import hashlib

# Security configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY", os.getenv("SECRET_KEY", "your-secret-key-change-in-production"))
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30  # 30 minutes for access token
REFRESH_TOKEN_EXPIRE_DAYS = 7     # 7 days for refresh token

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def generate_jti() -> str:
    """Generate a unique JWT ID (jti) for token revocation."""
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    """Create a hash of the token for storage (security best practice)."""
    return hashlib.sha256(token.encode()).hexdigest()


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token.
    
    Args:
        data: Dictionary containing user data (user_id, email, role, etc.)
        expires_delta: Optional custom expiration time
    
    Returns:
        Encoded JWT token string
    """
    to_encode = data.copy()
    
    # Generate unique token ID for revocation support
    jti = generate_jti()
    to_encode["jti"] = jti
    
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "access"
    })
    
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token(user_id: str, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT refresh token with rotation support.
    
    Args:
        user_id: The user's ID
        expires_delta: Optional custom expiration time
    
    Returns:
        Encoded JWT refresh token string
    """
    # Generate unique token ID for revocation support
    jti = generate_jti()
    
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    
    to_encode = {
        "user_id": user_id,
        "jti": jti,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "refresh"
    }
    
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str, check_revocation: bool = True) -> dict:
    """
    Decode and validate JWT access token.
    
    Args:
        token: The JWT token to decode
        check_revocation: Whether to check if token is revoked (default: True)
    
    Returns:
        Decoded token payload
    
    Raises:
        HTTPException: If token is invalid, expired, or revoked
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        # Verify token type
        if payload.get("type") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type"
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


def decode_refresh_token(token: str, check_revocation: bool = True) -> dict:
    """
    Decode and validate JWT refresh token.
    
    Args:
        token: The JWT refresh token to decode
        check_revocation: Whether to check if token is revoked (default: True)
    
    Returns:
        Decoded token payload
    
    Raises:
        HTTPException: If token is invalid, expired, or revoked
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        # Verify token type
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type"
            )
        
        return payload
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has expired"
        )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate refresh token"
        )


async def revoke_token(jti: str, token_type: str, db) -> None:
    """
    Add token JTI to blacklist for revocation.
    
    Args:
        jti: The JWT ID to revoke
        token_type: Type of token ('access' or 'refresh')
        db: Database connection
    """
    await db.token_blacklist.insert_one({
        "jti": jti,
        "token_type": token_type,
        "revoked_at": datetime.now(timezone.utc)
    })


async def is_token_revoked(jti: str, db) -> bool:
    """
    Check if a token is revoked.
    
    Args:
        jti: The JWT ID to check
        db: Database connection
    
    Returns:
        True if token is revoked, False otherwise
    """
    return await db.token_blacklist.find_one({"jti": jti}) is not None


async def revoke_all_user_tokens(user_id: str, db) -> None:
    """
    Revoke all tokens for a user (useful for password change, security breach, etc.)
    
    Args:
        user_id: The user ID whose tokens should be revoked
        db: Database connection
    """
    # Mark all refresh tokens as revoked
    await db.refresh_tokens.update_many(
        {"user_id": user_id, "is_revoked": False},
        {"$set": {"is_revoked": True, "revoked_at": datetime.now(timezone.utc)}}
    )


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Dependency to get current authenticated user from access token.
    
    Args:
        credentials: HTTP Authorization credentials containing the JWT token
    
    Returns:
        Decoded token payload containing user information
    
    Raises:
        HTTPException: If token is invalid, expired, or user not found
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    token = credentials.credentials
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = decode_access_token(token)
        user_id: str = payload.get("user_id")
        email: str = payload.get("email")
        
        if user_id is None or email is None:
            raise credentials_exception
            
        return payload
        
    except HTTPException:
        raise credentials_exception


async def get_current_user_with_revocation_check(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db=None
):
    """
    Dependency to get current user with token revocation check.
    Use this for sensitive operations where revoked tokens should be rejected immediately.
    
    Args:
        credentials: HTTP Authorization credentials containing the JWT token
        db: Database connection for revocation check
    
    Returns:
        Decoded token payload containing user information
    
    Raises:
        HTTPException: If token is invalid, expired, revoked, or user not found
    """
    token = credentials.credentials
    
    try:
        payload = decode_access_token(token)
        
        # Check if token is revoked
        jti = payload.get("jti")
        if jti and db and await is_token_revoked(jti, db):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked"
            )
        
        return payload
        
    except HTTPException:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_token_from_header_or_query(
    token: Optional[str] = Query(None),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
):
    """
    Dependency that extracts valid JWT payload from either:
    1. Authorization: Bearer <token> header
    2. 'token' query parameter
    Useful for direct file links (PDFs, exports) where headers are hard to set.
    """
    actual_token = None

    # Header takes precedence
    if credentials:
        actual_token = credentials.credentials
    # Fallback to query parameter
    elif token:
        actual_token = token

    if not actual_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_access_token(actual_token)
        return payload
    except HTTPException as e:
        # Re-raise authentication errors
        raise e
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
