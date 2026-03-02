from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Question


async def create_question(
    session: AsyncSession,
    assignment_id: int,
    question_text: str,
) -> Question:
    question = Question(
        assignment_id=assignment_id,
        question_text=question_text,
    )
    session.add(question)
    await session.commit()
    await session.refresh(question)
    return question


async def get_question_by_id(
    session: AsyncSession, question_id: int, assignment_id: int
) -> Question | None:
    result = await session.execute(
        select(Question).where(
            Question.id == question_id, Question.assignment_id == assignment_id
        )
    )
    return result.scalar_one_or_none()


async def get_questions_by_assignment_id(
    session: AsyncSession, assignment_id: int
) -> list[Question]:
    result = await session.execute(
        select(Question).where(Question.assignment_id == assignment_id)
    )
    return result.scalars().all()


async def update_question(
    session: AsyncSession, question_id: int, assignment_id: int, **fields
) -> Question | None:
    await session.execute(
        update(Question)
        .where(Question.id == question_id, Question.assignment_id == assignment_id)
        .values(**fields)
    )
    await session.commit()
    return await get_question_by_id(session, question_id, assignment_id)


async def delete_question(
    session: AsyncSession, question_id: int, assignment_id: int
) -> bool:
    result = await session.execute(
        delete(Question).where(
            Question.id == question_id, Question.assignment_id == assignment_id
        )
    )
    await session.commit()
    return result.rowcount > 0
