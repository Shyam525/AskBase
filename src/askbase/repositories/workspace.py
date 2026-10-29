"""Workspace and Membership data access repository."""

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from askbase.models.user import User
from askbase.models.workspace import Workspace, WorkspaceMembership


class WorkspaceRepository:
    """Repository handling Workspace and WorkspaceMembership persistence."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, workspace_id: uuid.UUID) -> Workspace | None:
        """Fetch workspace by primary key."""
        stmt = (
            select(Workspace)
            .where(Workspace.id == workspace_id)
            .options(selectinload(Workspace.memberships))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_slug(self, slug: str) -> Workspace | None:
        """Fetch workspace by case-insensitive slug match."""
        normalized = slug.strip().lower()
        stmt = select(Workspace).where(func.lower(Workspace.slug) == normalized)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create(self, name: str, slug: str, plan: str = "free") -> Workspace:
        """Create and persist a new workspace."""
        workspace = Workspace(
            name=name.strip(),
            slug=slug.strip().lower(),
            plan=plan,
        )
        self.session.add(workspace)
        await self.session.flush()
        return workspace

    async def list_for_user(self, user_id: uuid.UUID) -> list[Workspace]:
        """List all workspaces in which the user holds membership."""
        stmt = (
            select(Workspace)
            .join(WorkspaceMembership, Workspace.id == WorkspaceMembership.workspace_id)
            .where(WorkspaceMembership.user_id == user_id)
            .order_by(Workspace.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_membership(
        self,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> WorkspaceMembership | None:
        """Retrieve membership record for a specific user and workspace."""
        stmt = select(WorkspaceMembership).where(
            WorkspaceMembership.workspace_id == workspace_id,
            WorkspaceMembership.user_id == user_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def add_membership(
        self,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
        role: str = "member",
    ) -> WorkspaceMembership:
        """Add a user to a workspace with an assigned role."""
        membership = WorkspaceMembership(
            workspace_id=workspace_id,
            user_id=user_id,
            role=role,
        )
        self.session.add(membership)
        await self.session.flush()
        return membership

    async def remove_membership(
        self,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> bool:
        """Remove membership associating a user with a workspace."""
        membership = await self.get_membership(workspace_id, user_id)
        if membership:
            await self.session.delete(membership)
            await self.session.flush()
            return True
        return False

    async def list_members(
        self,
        workspace_id: uuid.UUID,
    ) -> list[tuple[WorkspaceMembership, User]]:
        """List all members and their user profiles within a workspace."""
        stmt = (
            select(WorkspaceMembership, User)
            .join(User, WorkspaceMembership.user_id == User.id)
            .where(WorkspaceMembership.workspace_id == workspace_id)
            .order_by(WorkspaceMembership.created_at.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.all())
