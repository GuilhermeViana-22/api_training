from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshRequest(BaseModel):
    refresh_token: str


class RefreshResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class LogoutRequest(BaseModel):
    refresh_token: str


class AdminProfileResponse(BaseModel):
    full_name: str
    cref: str | None = None
    phone: str | None = None
    bio: str | None = None


class StudentProfileResponse(BaseModel):
    full_name: str
    phone: str | None = None
    birth_date: str | None = None
    height_cm: float | None = None
    weight_kg: float | None = None
    goal: str | None = None


class MeResponse(BaseModel):
    id: str
    email: EmailStr
    role: str
    is_active: bool
    profile: AdminProfileResponse | StudentProfileResponse
    created_at: datetime
