import logging
from datetime import datetime

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Assignment

logger = logging.getLogger(__name__)


async def create_assignment(
    session: AsyncSession,
    course_id: int,
    rubric_json: dict,
    title: str,
    description: str | None,
    due_date: datetime | None,
) -> Assignment:
    logger.info("Creating assignment '%s' for course %d", title, course_id)
    assignment = Assignment(
        course_id=course_id,
        rubric_json=rubric_json,
        title=title,
        description=description,
        due_date=due_date,
    )
    session.add(assignment)
    await session.commit()
    await session.refresh(assignment)
    logger.info("Assignment created: '%s' (id=%d)", assignment.title, assignment.id)
    return assignment


async def get_assignment_by_id(
    session: AsyncSession, assignment_id: int
) -> Assignment | None:
    logger.debug("Looking up assignment by id: %d", assignment_id)
    result = await session.execute(
        select(Assignment).where(Assignment.id == assignment_id)
    )
    return result.scalar_one_or_none()


async def get_assignments_by_course_id(
    session: AsyncSession, course_id: int
) -> list[Assignment]:
    logger.debug("Fetching assignments for course %d", course_id)
    result = await session.execute(
        select(Assignment).where(Assignment.course_id == course_id)
    )
    return result.scalars().all()


async def update_assignment(
    session: AsyncSession, assignment_id: int, **fields
) -> Assignment | None:
    logger.info(
        "Updating assignment %d with fields: %s", assignment_id, list(fields.keys())
    )
    await session.execute(
        update(Assignment).where(Assignment.id == assignment_id).values(**fields)
    )
    await session.commit()
    return await get_assignment_by_id(session, assignment_id)


async def delete_assignment(session: AsyncSession, assignment_id: int) -> bool:
    logger.info("Deleting assignment %d", assignment_id)
    result = await session.execute(
        delete(Assignment).where(Assignment.id == assignment_id)
    )
    await session.commit()
    deleted = result.rowcount > 0
    if deleted:
        logger.info("Assignment %d deleted", assignment_id)
    else:
        logger.warning("Assignment %d not found for deletion", assignment_id)
    return deleted
