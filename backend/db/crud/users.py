from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import User, UserRole


async def create_user(
    session: AsyncSession, username: str, password_hash: str, email: str, role: UserRole
) -> User:
    user = User(username=username, password_hash=password_hash, email=email, role=role)
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def get_user_by_username(session: AsyncSession, username: str) -> User | None:

    result = await session.execute(select(User).where(User.username == username))
    return result.scalar_one_or_none()


async def get_user_by_id(session: AsyncSession, user_id: int) -> User | None:

    result = await session.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def update_user_email(
    session: AsyncSession, username: str, new_email: str
) -> User | None:
    await session.execute(
        update(User).where(User.username == username).values(email=new_email)
    )
    await session.commit()
    return await get_user_by_username(session, username)


async def delete_user(session: AsyncSession, username: str) -> bool:
    result = await session.execute(delete(User).where(User.username == username))
    await session.commit()
    return result.rowcount > 0
