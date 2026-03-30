import logging

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import User, UserRole


async def list_users_by_role(session: AsyncSession, role: UserRole) -> list[User]:
    result = await session.execute(select(User).where(User.role == role))
    return list(result.scalars().all())


logger = logging.getLogger(__name__)


async def create_user(
    session: AsyncSession, username: str, password_hash: str, email: str, role: UserRole
) -> User:
    logger.info("Creating user: %s (role=%s)", username, role.value)
    user = User(username=username, password_hash=password_hash, email=email, role=role)
    session.add(user)
    await session.commit()
    await session.refresh(user)
    logger.info("User created: %s (id=%d)", username, user.id)
    return user


async def get_user_by_username(session: AsyncSession, username: str) -> User | None:
    logger.debug("Looking up user by username: %s", username)
    result = await session.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if not user:
        logger.debug("User not found: %s", username)
    return user


async def get_user_by_id(session: AsyncSession, user_id: int) -> User | None:
    logger.debug("Looking up user by id: %d", user_id)
    result = await session.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def update_user_email(
    session: AsyncSession, username: str, new_email: str
) -> User | None:
    logger.info("Updating email for user: %s", username)
    await session.execute(
        update(User).where(User.username == username).values(email=new_email)
    )
    await session.commit()
    return await get_user_by_username(session, username)


async def delete_user(session: AsyncSession, username: str) -> bool:
    logger.info("Deleting user: %s", username)
    result = await session.execute(delete(User).where(User.username == username))
    await session.commit()
    deleted = result.rowcount > 0
    if deleted:
        logger.info("User deleted: %s", username)
    else:
        logger.warning("User not found for deletion: %s", username)
    return deleted
