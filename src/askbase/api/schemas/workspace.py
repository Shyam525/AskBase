"""Workspace and membership schemas."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class CreateWorkspaceRequest(BaseModel):
    """Workspace creation payload."""

    name: str = Field(min_length=1, max_length=255)
    slug: str | None = Field(default=None, max_length=100)


class WorkspaceResponse(BaseModel):
    """Workspace representation."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    plan: str
    created_at: datetime
    updated_at: datetime


class AddMemberRequest(BaseModel):
    """Workspace member invitation payload."""

    email: EmailStr
    role: Literal["owner", "admin", "member"] = "member"


class MemberResponse(BaseModel):
    """Membership record with associated user details."""

    membership_id: uuid.UUID
    user_id: uuid.UUID
    email: str
    name: str
    role: str
    created_at: datetime
