"""FastAPI dependency injection for database sessions, authentication, and tenant authorization."""

import uuid
from collections.abc import AsyncGenerator
from typing import Annotated, Literal

from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from askbase.core.errors import ForbiddenError, UnauthorizedError
from askbase.core.security import decode_access_token
from askbase.db.session import get_db_session
from askbase.models.user import User
from askbase.models.workspace import WorkspaceMembership
from askbase.repositories.user import UserRepository
from askbase.repositories.workspace import WorkspaceRepository

ROLE_HIERARCHY: dict[str, int] = {
    "owner": 3,
    "admin": 2,
    "member": 1,
}


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for obtaining an asynchronous database session."""
    async for session in get_db_session():
        yield session


DBSession = Annotated[AsyncSession, Depends(get_db)]


async def get_current_user(
    db: DBSession,
    authorization: str | None = Header(default=None),
) -> User:
    """Validate Bearer JWT access token and return active authenticated user."""
    if not authorization:
        raise UnauthorizedError("Authorization header is missing.")

    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise UnauthorizedError("Invalid Authorization header format. Expected 'Bearer <token>'.")

    token = parts[1]
    payload = decode_access_token(token)

    sub = payload.get("sub")
    if not sub:
        raise UnauthorizedError("Access token contains no subject claim.")

    try:
        user_id = uuid.UUID(sub)
    except ValueError as e:
        raise UnauthorizedError("Invalid user ID in token subject.") from e

    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(user_id)
    if not user:
        raise UnauthorizedError("User associated with this token does not exist.")

    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


async def get_workspace_membership(
    workspace_id: uuid.UUID,
    user: CurrentUser,
    db: DBSession,
) -> WorkspaceMembership:
    """Verify that current user is an authorized member of the requested workspace.

    Guarantees tenant isolation: Prevents horizontal privilege escalation across workspaces.
    """
    ws_repo = WorkspaceRepository(db)
    membership = await ws_repo.get_membership(workspace_id=workspace_id, user_id=user.id)
    if not membership:
        raise ForbiddenError("Access denied: You are not a member of this workspace.")
    return membership


WorkspaceMember = Annotated[WorkspaceMembership, Depends(get_workspace_membership)]


def require_role(min_role: Literal["owner", "admin", "member"]):
    """Factory dependency enforcing a minimum role hierarchy within a workspace."""

    async def _role_checker(
        membership: WorkspaceMember,
    ) -> WorkspaceMembership:
        user_level = ROLE_HIERARCHY.get(membership.role.lower(), 0)
        required_level = ROLE_HIERARCHY.get(min_role.lower(), 0)

        if user_level < required_level:
            raise ForbiddenError(
                f"Action requires minimum '{min_role}' privileges in this workspace."
            )
        return membership

    return _role_checker
