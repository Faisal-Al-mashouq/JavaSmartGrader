from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Question, Testcase


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


async def create_testcase(
    session: AsyncSession,
    question_id: int,
    assignment_id: int,
    input_data: str,
    expected_output: str,
) -> Testcase:
    testcase = Testcase(
        question_id=question_id,
        assignment_id=assignment_id,
        input=input_data,
        expected_output=expected_output,
    )
    session.add(testcase)
    await session.commit()
    await session.refresh(testcase)
    return testcase


async def get_testcases_by_question_id(
    session: AsyncSession, question_id: int, assignment_id: int
) -> list[Testcase]:
    result = await session.execute(
        select(Testcase).where(
            Testcase.question_id == question_id,
            Testcase.assignment_id == assignment_id,
        )
    )
    return result.scalars().all()


async def delete_testcase(session: AsyncSession, testcase_id: int) -> None:
    await session.execute(delete(Testcase).where(Testcase.id == testcase_id))
    await session.commit()
