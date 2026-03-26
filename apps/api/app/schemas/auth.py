from pydantic import BaseModel
from app.schemas.user import UserResponse

class LoginRequest(BaseModel):
    email: str
    password: str

class RefreshTokenRequest(BaseModel):
    refresh_token: str

class Token(BaseModel):
    access_token: str
    expires_in: int
    user: UserResponse
