"""Workspace and tenant management service."""

import re
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from askbase.core.errors import BadRequestError, ConflictError, NotFoundError
from askbase.models.user import User
from askbase.models.workspace import Workspace, WorkspaceMembership
from askbase.repositories.user import UserRepository
from askbase.repositories.workspace import WorkspaceRepository


def slugify(text: str) -> str:
    """Generate clean URL-safe slug from arbitrary string."""
    clean = re.sub(r"[^a-zA-Z0-9\s-]", "", text.strip().lower())
    clean = re.sub(r"[\s_-]+", "-", clean)
    return clean.strip("-") or "workspace"


class WorkspaceService:
    """Handles workspace lifecycles, tenant boundaries, and membership roles."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.ws_repo = WorkspaceRepository(session)
        self.user_repo = UserRepository(session)

    async def create_workspace(
        self,
        creator_user_id: uuid.UUID,
        name: str,
        slug: str | None = None,
        plan: str = "free",
    ) -> Workspace:
        """Create a new workspace boundary and assign creator as owner."""
        if not name.strip():
            raise BadRequestError("Workspace name is required.")

        base_slug = slugify(slug if slug and slug.strip() else name)
        final_slug = f"{base_slug}-{uuid.uuid4().hex[:6]}"

        ws = await self.ws_repo.create(
            name=name.strip(),
            slug=final_slug,
            plan=plan,
        )

        await self.ws_repo.add_membership(
            workspace_id=ws.id,
            user_id=creator_user_id,
            role="owner",
        )

        return ws

    async def list_workspaces_for_user(self, user_id: uuid.UUID) -> list[Workspace]:
        """List all workspaces the user has access to."""
        return await self.ws_repo.list_for_user(user_id)

    async def get_workspace(self, workspace_id: uuid.UUID) -> Workspace:
        """Get workspace by ID or raise NotFoundError."""
        ws = await self.ws_repo.get_by_id(workspace_id)
        if not ws:
            raise NotFoundError("Workspace not found.")
        return ws

    async def add_member(
        self,
        workspace_id: uuid.UUID,
        user_email: str,
        role: str = "member",
    ) -> tuple[WorkspaceMembership, User]:
        """Add an existing user to a workspace."""
        if role not in {"owner", "admin", "member"}:
            raise BadRequestError("Role must be one of 'owner', 'admin', or 'member'.")

        user = await self.user_repo.get_by_email(user_email)
        if not user:
            raise NotFoundError(f"No registered user found with email '{user_email}'.")

        existing = await self.ws_repo.get_membership(workspace_id, user.id)
        if existing:
            raise ConflictError("User is already a member of this workspace.")

        membership = await self.ws_repo.add_membership(workspace_id, user.id, role=role)
        return membership, user

    async def list_members(
        self,
        workspace_id: uuid.UUID,
    ) -> list[tuple[WorkspaceMembership, User]]:
        """List all active memberships and user details in a workspace."""
        return await self.ws_repo.list_members(workspace_id)

    async def remove_member(
        self,
        workspace_id: uuid.UUID,
        target_user_id: uuid.UUID,
    ) -> bool:
        """Remove a user's membership from a workspace."""
        removed = await self.ws_repo.remove_membership(workspace_id, target_user_id)
        if not removed:
            raise NotFoundError("Membership record not found.")
        return True
