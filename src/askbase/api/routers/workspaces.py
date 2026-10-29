"""Workspaces and membership management router."""

import uuid

from fastapi import APIRouter, Depends

from askbase.api.deps import (
    CurrentUser,
    DBSession,
    WorkspaceMember,
    require_role,
)
from askbase.api.schemas.workspace import (
    AddMemberRequest,
    CreateWorkspaceRequest,
    MemberResponse,
    WorkspaceResponse,
)
from askbase.services.workspace import WorkspaceService

router = APIRouter(prefix="/api/workspaces", tags=["Workspaces"])


@router.post("", response_model=WorkspaceResponse)
async def create_workspace(
    req: CreateWorkspaceRequest,
    user: CurrentUser,
    db: DBSession,
):
    """Create a new workspace boundary and assign caller as owner."""
    service = WorkspaceService(db)
    ws = await service.create_workspace(
        creator_user_id=user.id,
        name=req.name,
        slug=req.slug,
    )
    return ws


@router.get("", response_model=list[WorkspaceResponse])
async def list_workspaces(
    user: CurrentUser,
    db: DBSession,
):
    """List all workspaces the authenticated user belongs to."""
    service = WorkspaceService(db)
    return await service.list_workspaces_for_user(user.id)


@router.get("/{workspace_id}", response_model=WorkspaceResponse)
async def get_workspace(
    workspace_id: uuid.UUID,
    _membership: WorkspaceMember,
    db: DBSession,
):
    """Get workspace details (enforces workspace membership)."""
    service = WorkspaceService(db)
    return await service.get_workspace(workspace_id)


@router.post(
    "/{workspace_id}/members",
    response_model=MemberResponse,
    dependencies=[Depends(require_role("admin"))],
)
async def add_workspace_member(
    workspace_id: uuid.UUID,
    req: AddMemberRequest,
    db: DBSession,
):
    """Add a member to a workspace (requires admin or owner privileges)."""
    service = WorkspaceService(db)
    membership, user = await service.add_member(
        workspace_id=workspace_id,
        user_email=req.email,
        role=req.role,
    )

    return MemberResponse(
        membership_id=membership.id,
        user_id=membership.user_id,
        email=user.email,
        name=user.name,
        role=membership.role,
        created_at=membership.created_at,
    )


@router.get(
    "/{workspace_id}/members",
    response_model=list[MemberResponse],
)
async def list_workspace_members(
    workspace_id: uuid.UUID,
    _membership: WorkspaceMember,
    db: DBSession,
):
    """List all members of a workspace."""
    service = WorkspaceService(db)
    records = await service.list_members(workspace_id)

    return [
        MemberResponse(
            membership_id=m.id,
            user_id=u.id,
            email=u.email,
            name=u.name,
            role=m.role,
            created_at=m.created_at,
        )
        for m, u in records
    ]


@router.delete(
    "/{workspace_id}/members/{user_id}",
    dependencies=[Depends(require_role("admin"))],
)
async def remove_workspace_member(
    workspace_id: uuid.UUID,
    user_id: uuid.UUID,
    db: DBSession,
):
    """Remove a user from a workspace (requires admin or owner privileges)."""
    service = WorkspaceService(db)
    await service.remove_member(workspace_id, user_id)
    return {"message": "Member removed successfully."}
