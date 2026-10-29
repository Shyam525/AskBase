"""Authentication and session management router."""

from fastapi import APIRouter

from askbase.api.deps import CurrentUser, DBSession
from askbase.api.schemas.auth import (
    AuthResponse,
    CurrentUserResponse,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
)
from askbase.repositories.workspace import WorkspaceRepository
from askbase.services.auth import AuthService

router = APIRouter(prefix="/api/auth", tags=["Auth"])


@router.post("/register", response_model=AuthResponse)
async def register(req: RegisterRequest, db: DBSession):
    """Register a new user and tenant organization."""
    service = AuthService(db)
    user, workspace, access_token, refresh_token = await service.register(
        org_name=req.org_name,
        email=req.email,
        password=req.password,
        name=req.name,
    )
    return AuthResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        user_id=user.id,
        email=user.email,
        org_id=workspace.id,
        role="owner",
    )


@router.post("/login", response_model=AuthResponse)
async def login(req: LoginRequest, db: DBSession):
    """Authenticate with email and password."""
    service = AuthService(db)
    user, workspace, access_token, refresh_token = await service.login(
        email=req.email,
        password=req.password,
    )
    role = "member"
    if workspace:
        ws_repo = WorkspaceRepository(db)
        membership = await ws_repo.get_membership(workspace.id, user.id)
        if membership:
            role = membership.role

    return AuthResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        user_id=user.id,
        email=user.email,
        org_id=workspace.id if workspace else None,
        role=role,
    )


@router.post("/refresh", response_model=AuthResponse)
async def refresh(req: RefreshRequest, db: DBSession):
    """Rotate refresh token and issue new access token."""
    service = AuthService(db)
    user, workspace, access_token, new_refresh = await service.refresh(req.refresh_token)
    role = "member"
    if workspace:
        ws_repo = WorkspaceRepository(db)
        membership = await ws_repo.get_membership(workspace.id, user.id)
        if membership:
            role = membership.role

    return AuthResponse(
        access_token=access_token,
        refresh_token=new_refresh,
        token_type="bearer",
        user_id=user.id,
        email=user.email,
        org_id=workspace.id if workspace else None,
        role=role,
    )


@router.post("/logout")
async def logout(req: RefreshRequest, db: DBSession):
    """Revoke a refresh token session."""
    service = AuthService(db)
    await service.logout(req.refresh_token)
    return {"message": "Logged out successfully."}


@router.get("/me", response_model=CurrentUserResponse)
async def get_me(user: CurrentUser, db: DBSession):
    """Retrieve profile and workspace access for currently authenticated user."""
    ws_repo = WorkspaceRepository(db)
    workspaces = await ws_repo.list_for_user(user.id)

    ws_data = []
    primary_role = "member"
    primary_tenant_id = None

    if workspaces:
        primary_tenant_id = workspaces[0].id
        mem = await ws_repo.get_membership(workspaces[0].id, user.id)
        if mem:
            primary_role = mem.role

    for w in workspaces:
        m = await ws_repo.get_membership(w.id, user.id)
        ws_data.append(
            {
                "id": w.id,
                "name": w.name,
                "slug": w.slug,
                "role": m.role if m else "member",
            }
        )

    return CurrentUserResponse(
        user_id=user.id,
        email=user.email,
        name=user.name,
        role=primary_role,
        tenant_id=primary_tenant_id,
        workspaces=ws_data,
    )
