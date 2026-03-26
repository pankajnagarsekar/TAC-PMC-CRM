from app.repositories.base_repo import BaseRepository
from pydantic import BaseModel
from datetime import datetime

class TokenBlacklist(BaseModel):
    jti: str
    token_type: str
    revoked_at: datetime

class RefreshToken(BaseModel):
    user_id: str
    jti: str
    is_revoked: bool
    revoked_at: datetime

class TokenBlacklistRepository(BaseRepository[TokenBlacklist]):
    def __init__(self, db):
        super().__init__(db, "token_blacklist", TokenBlacklist)

class RefreshTokenRepository(BaseRepository[RefreshToken]):
    def __init__(self, db):
        super().__init__(db, "refresh_tokens", RefreshToken)
