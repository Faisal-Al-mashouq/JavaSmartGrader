import logging

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Submission, SubmissionState

logger = logging.getLogger(__name__)


async def create_submission(
    session: AsyncSession,
    assignment_id: int,
    student_id: int,
    image_url: str | None = None,
) -> Submission:
    logger.info(
        "Creating submission for student %d, assignment %d", student_id, assignment_id
    )
    submission = Submission(
        assignment_id=assignment_id,
        student_id=student_id,
        image_url=image_url,
    )
    session.add(submission)
    await session.commit()
    await session.refresh(submission)
    logger.info("Submission created (id=%d) for student %d", submission.id, student_id)
    return submission


async def get_submission_by_id(
    session: AsyncSession, submission_id: int
) -> Submission | None:
    logger.debug("Looking up submission by id: %d", submission_id)
    result = await session.execute(
        select(Submission).where(Submission.id == submission_id)
    )
    return result.scalar_one_or_none()


async def get_submissions_by_student_id(
    session: AsyncSession, student_id: int
) -> list[Submission]:
    logger.debug("Fetching submissions for student %d", student_id)
    result = await session.execute(
        select(Submission).where(Submission.student_id == student_id)
    )
    return result.scalars().all()


async def get_submissions_by_assignment_id(
    session: AsyncSession, assignment_id: int
) -> list[Submission]:
    logger.debug("Fetching submissions for assignment %d", assignment_id)
    result = await session.execute(
        select(Submission).where(Submission.assignment_id == assignment_id)
    )
    return result.scalars().all()


async def update_submission_state(
    session: AsyncSession, submission_id: int, new_state: SubmissionState
) -> Submission | None:
    logger.info("Updating submission %d state to %s", submission_id, new_state.value)
    await session.execute(
        update(Submission).where(Submission.id == submission_id).values(state=new_state)
    )
    await session.commit()
    return await get_submission_by_id(session, submission_id)


async def update_submission(
    session: AsyncSession, submission_id: int, **fields
) -> Submission | None:
    logger.info(
        "Updating submission %d with fields: %s", submission_id, list(fields.keys())
    )
    await session.execute(
        update(Submission).where(Submission.id == submission_id).values(**fields)
    )
    await session.commit()
    return await get_submission_by_id(session, submission_id)


async def delete_submission(session: AsyncSession, submission_id: int) -> bool:
    logger.info("Deleting submission %d", submission_id)
    submission = await get_submission_by_id(session, submission_id)
    if not submission:
        logger.warning("Submission %d not found for deletion", submission_id)
        return False

    await session.delete(submission)
    await session.commit()
    logger.info("Submission %d deleted", submission_id)
    return True
