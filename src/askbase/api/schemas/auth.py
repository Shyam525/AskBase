"""Authentication request and response schemas."""

import uuid

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RegisterRequest(BaseModel):
    """Registration payload accepting both snake_case and camelCase attributes."""

    model_config = ConfigDict(populate_by_name=True)

    org_name: str = Field(alias="orgName", min_length=1, max_length=255)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    name: str | None = Field(default=None, max_length=255)


class LoginRequest(BaseModel):
    """Login payload."""

    email: EmailStr
    password: str = Field(min_length=1)


class RefreshRequest(BaseModel):
    """Refresh session token payload."""

    model_config = ConfigDict(populate_by_name=True)

    refresh_token: str = Field(alias="refreshToken", min_length=1)


class AuthResponse(BaseModel):
    """Token issuance response."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user_id: uuid.UUID
    email: str
    org_id: uuid.UUID | None = None
    role: str = "member"


class CurrentUserResponse(BaseModel):
    """Authenticated user profile."""

    user_id: uuid.UUID
    email: str
    name: str
    role: str
    tenant_id: uuid.UUID | None = None
    workspaces: list[dict[str, str | uuid.UUID]]
