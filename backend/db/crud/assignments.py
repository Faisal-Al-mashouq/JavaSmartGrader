from datetime import datetime

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Assignment


async def create_assignment(
    session: AsyncSession,
    instructor_id: int,
    title: str,
    question: str,
    description: str | None,
    due_date: datetime | None,
) -> Assignment:
    assignment = Assignment(
        instructor_id=instructor_id,
        title=title,
        question=question,
        description=description,
        due_date=due_date,
    )
    session.add(assignment)
    await session.commit()
    await session.refresh(assignment)
    return assignment


async def get_assignment_by_id(
    session: AsyncSession, assignment_id: int
) -> Assignment | None:

    result = await session.execute(
        select(Assignment).where(Assignment.id == assignment_id)
    )
    return result.scalar_one_or_none()


async def get_assignments_by_instructor_id(
    session: AsyncSession, instructor_id: int
) -> list[Assignment]:

    result = await session.execute(
        select(Assignment).where(Assignment.instructor_id == instructor_id)
    )
    return result.scalars().all()


async def update_assignment(
    session: AsyncSession, assignment_id: int, **fields
) -> Assignment | None:
    await session.execute(
        update(Assignment).where(Assignment.id == assignment_id).values(**fields)
    )
    await session.commit()
    return await get_assignment_by_id(session, assignment_id)


async def delete_assignment(session: AsyncSession, assignment_id: int) -> bool:
    result = await session.execute(
        delete(Assignment).where(Assignment.id == assignment_id)
    )
    await session.commit()
    return result.rowcount > 0
