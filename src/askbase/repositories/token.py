"""Refresh token repository."""

import uuid
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from askbase.models.token import RefreshToken


class RefreshTokenRepository:
    """Repository handling RefreshToken persistence and revocation."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        user_id: uuid.UUID,
        token: str,
        expires_at: datetime,
    ) -> RefreshToken:
        """Create and store a refresh token record."""
        record = RefreshToken(
            user_id=user_id,
            token=token,
            expires_at=expires_at,
        )
        self.session.add(record)
        await self.session.flush()
        return record

    async def get_by_token(self, token: str) -> RefreshToken | None:
        """Fetch active token with associated user."""
        stmt = (
            select(RefreshToken)
            .where(RefreshToken.token == token)
            .options(selectinload(RefreshToken.user))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def revoke(self, token: str) -> bool:
        """Mark a specific refresh token as revoked."""
        record = await self.get_by_token(token)
        if record:
            record.revoked = True
            await self.session.flush()
            return True
        return False

    async def revoke_all_for_user(self, user_id: uuid.UUID) -> int:
        """Revoke all active refresh tokens for a user upon logout or password reset."""
        stmt = (
            update(RefreshToken)
            .where(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked.is_(False),
            )
            .values(revoked=True)
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        rowcount = getattr(result, "rowcount", 0)
        return int(rowcount) if rowcount is not None else 0
