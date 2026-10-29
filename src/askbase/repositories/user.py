"""User data access repository."""

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from askbase.models.user import User


class UserRepository:
    """Repository handling User entity persistence operations."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        """Fetch user by primary key."""
        stmt = select(User).where(User.id == user_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        """Fetch user by case-insensitive email match."""
        normalized = email.strip().lower()
        stmt = select(User).where(func.lower(User.email) == normalized)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create(self, email: str, password_hash: str, name: str) -> User:
        """Create and persist a new user."""
        user = User(
            email=email.strip().lower(),
            password_hash=password_hash,
            name=name.strip(),
        )
        self.session.add(user)
        await self.session.flush()
        return user
