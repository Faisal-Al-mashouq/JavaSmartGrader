from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Submission, SubmissionState


async def create_submission(
    session: AsyncSession,
    assignment_id: int,
    student_id: int,
    image_url: str | None = None,
) -> Submission:
    submission = Submission(
        assignment_id=assignment_id,
        student_id=student_id,
        image_url=image_url,
    )
    session.add(submission)
    await session.commit()
    await session.refresh(submission)
    return submission


async def get_submission_by_id(
    session: AsyncSession, submission_id: int
) -> Submission | None:

    result = await session.execute(
        select(Submission).where(Submission.id == submission_id)
    )
    return result.scalar_one_or_none()


async def get_submissions_by_student_id(
    session: AsyncSession, student_id: int
) -> list[Submission]:

    result = await session.execute(
        select(Submission).where(Submission.student_id == student_id)
    )
    return result.scalars().all()


async def get_submissions_by_assignment_id(
    session: AsyncSession, assignment_id: int
) -> list[Submission]:

    result = await session.execute(
        select(Submission).where(Submission.assignment_id == assignment_id)
    )
    return result.scalars().all()


async def update_submission_state(
    session: AsyncSession, submission_id: int, new_state: SubmissionState
) -> Submission | None:
    await session.execute(
        update(Submission).where(Submission.id == submission_id).values(state=new_state)
    )
    await session.commit()
    return await get_submission_by_id(session, submission_id)


async def update_submission(
    session: AsyncSession, submission_id: int, **fields
) -> Submission | None:
    await session.execute(
        update(Submission).where(Submission.id == submission_id).values(**fields)
    )
    await session.commit()
    return await get_submission_by_id(session, submission_id)


async def delete_submission(session: AsyncSession, submission_id: int) -> bool:
    result = await session.execute(
        delete(Submission).where(Submission.id == submission_id)
    )
    await session.commit()
    return result.rowcount > 0
