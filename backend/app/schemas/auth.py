from pydantic import BaseModel, EmailStr, field_validator

from app.models.user import UserRole
from app.schemas.base import TimestampSchema


# ─── Auth ────────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


# ─── User ────────────────────────────────────────────────────────────────────

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Senha deve ter pelo menos 8 caracteres")
        return v


class UserResponse(TimestampSchema):
    email: str
    full_name: str
    role: UserRole
    is_active: bool
    tenant_id: str


# ─── Tenant ──────────────────────────────────────────────────────────────────

class TenantCreate(BaseModel):
    name: str
    slug: str

    @field_validator("slug")
    @classmethod
    def slug_format(cls, v: str) -> str:
        import re
        if not re.match(r"^[a-z0-9-]+$", v):
            raise ValueError("Slug deve conter apenas letras minúsculas, números e hífens")
        return v


class TenantResponse(TimestampSchema):
    name: str
    slug: str
    is_active: bool
