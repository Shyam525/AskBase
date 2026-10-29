"""Authentication and user session service."""

import re
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from askbase.core.errors import ConflictError, UnauthorizedError, ValidationError
from askbase.core.security import (
    create_access_token,
    generate_secure_token,
    hash_password,
    verify_password,
)
from askbase.core.settings import get_settings
from askbase.models.user import User
from askbase.models.workspace import Workspace
from askbase.repositories.token import RefreshTokenRepository
from askbase.repositories.user import UserRepository
from askbase.repositories.workspace import WorkspaceRepository


def slugify(text: str) -> str:
    """Generate clean URL-safe slug from arbitrary string."""
    clean = re.sub(r"[^a-zA-Z0-9\s-]", "", text.strip().lower())
    clean = re.sub(r"[\s_-]+", "-", clean)
    return clean.strip("-") or "workspace"


class AuthService:
    """Handles user onboarding, authentication, and session token rotation."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.user_repo = UserRepository(session)
        self.ws_repo = WorkspaceRepository(session)
        self.token_repo = RefreshTokenRepository(session)
        self.settings = get_settings()

    async def register(
        self,
        org_name: str,
        email: str,
        password: str,
        name: str | None = None,
    ) -> tuple[User, Workspace, str, str]:
        """Register a new user, create their initial workspace, and issue tokens."""
        clean_email = email.strip().lower()
        if "@" not in clean_email or len(clean_email) < 5:
            raise ValidationError("A valid email address is required.")
        if len(password) < 8:
            raise ValidationError("Password must be at least 8 characters long.")
        if not org_name.strip():
            raise ValidationError("Organization/workspace name is required.")

        # Check for existing email case-insensitively
        existing = await self.user_repo.get_by_email(clean_email)
        if existing:
            raise ConflictError("An account with this email already exists.")

        # Create user
        display_name = name.strip() if name and name.strip() else clean_email.split("@")[0]
        hashed_pw = hash_password(password)
        user = await self.user_repo.create(
            email=clean_email,
            password_hash=hashed_pw,
            name=display_name,
        )

        # Generate unique workspace slug
        base_slug = slugify(org_name)
        slug = f"{base_slug}-{uuid.uuid4().hex[:6]}"
        workspace = await self.ws_repo.create(
            name=org_name.strip(),
            slug=slug,
            plan="free",
        )

        # Grant creator the 'owner' role
        await self.ws_repo.add_membership(
            workspace_id=workspace.id,
            user_id=user.id,
            role="owner",
        )

        # Issue tokens
        access_token, refresh_token = await self._issue_session_tokens(
            user=user,
            workspace_id=workspace.id,
            role="owner",
        )

        return user, workspace, access_token, refresh_token

    async def login(
        self,
        email: str,
        password: str,
    ) -> tuple[User, Workspace | None, str, str]:
        """Verify user credentials and issue new session tokens."""
        clean_email = email.strip().lower()
        user = await self.user_repo.get_by_email(clean_email)
        if not user or not verify_password(password, user.password_hash):
            raise UnauthorizedError("Invalid email or password.")

        # Determine user's active workspace
        workspaces = await self.ws_repo.list_for_user(user.id)
        active_ws = workspaces[0] if workspaces else None

        role = "member"
        if active_ws:
            membership = await self.ws_repo.get_membership(active_ws.id, user.id)
            if membership:
                role = membership.role

        access_token, refresh_token = await self._issue_session_tokens(
            user=user,
            workspace_id=active_ws.id if active_ws else None,
            role=role,
        )

        return user, active_ws, access_token, refresh_token

    async def refresh(self, raw_refresh_token: str) -> tuple[User, Workspace | None, str, str]:
        """Rotate refresh token and issue fresh short-lived access token."""
        stored = await self.token_repo.get_by_token(raw_refresh_token)
        if not stored or not stored.is_valid:
            raise UnauthorizedError("Invalid or expired refresh token.")

        # Revoke used refresh token (strict token rotation)
        await self.token_repo.revoke(raw_refresh_token)

        user = stored.user
        workspaces = await self.ws_repo.list_for_user(user.id)
        active_ws = workspaces[0] if workspaces else None

        role = "member"
        if active_ws:
            membership = await self.ws_repo.get_membership(active_ws.id, user.id)
            if membership:
                role = membership.role

        access_token, new_refresh_token = await self._issue_session_tokens(
            user=user,
            workspace_id=active_ws.id if active_ws else None,
            role=role,
        )

        return user, active_ws, access_token, new_refresh_token

    async def logout(self, raw_refresh_token: str) -> None:
        """Revoke a refresh session on logout."""
        await self.token_repo.revoke(raw_refresh_token)

    async def _issue_session_tokens(
        self,
        user: User,
        workspace_id: uuid.UUID | None,
        role: str,
    ) -> tuple[str, str]:
        """Sign JWT access token and persist random refresh token."""
        access_token = create_access_token(
            user_id=user.id,
            email=user.email,
            role=role,
            workspace_id=workspace_id,
        )

        raw_refresh = generate_secure_token(48)
        expires_at = datetime.now(UTC) + timedelta(days=self.settings.JWT_REFRESH_EXPIRES_IN_DAYS)

        await self.token_repo.create(
            user_id=user.id,
            token=raw_refresh,
            expires_at=expires_at,
        )

        return access_token, raw_refresh
