import logging

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Question, Testcase

logger = logging.getLogger(__name__)


async def create_question(
    session: AsyncSession,
    assignment_id: int,
    question_text: str,
) -> Question:
    logger.info("Creating question for assignment %d", assignment_id)
    question = Question(
        assignment_id=assignment_id,
        question_text=question_text,
    )
    session.add(question)
    await session.commit()
    await session.refresh(question)
    logger.info(
        "Question created (id=%d) for assignment %d", question.id, assignment_id
    )
    return question


async def get_question_by_id(
    session: AsyncSession, question_id: int, assignment_id: int
) -> Question | None:
    logger.debug("Looking up question %d in assignment %d", question_id, assignment_id)
    result = await session.execute(
        select(Question).where(
            Question.id == question_id, Question.assignment_id == assignment_id
        )
    )
    return result.scalar_one_or_none()


async def get_questions_by_assignment_id(
    session: AsyncSession, assignment_id: int
) -> list[Question]:
    logger.debug("Fetching questions for assignment %d", assignment_id)
    result = await session.execute(
        select(Question).where(Question.assignment_id == assignment_id)
    )
    return result.scalars().all()


async def update_question(
    session: AsyncSession, question_id: int, assignment_id: int, **fields
) -> Question | None:
    logger.info("Updating question %d in assignment %d", question_id, assignment_id)
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
    logger.info("Deleting question %d from assignment %d", question_id, assignment_id)
    result = await session.execute(
        delete(Question).where(
            Question.id == question_id, Question.assignment_id == assignment_id
        )
    )
    await session.commit()
    deleted = result.rowcount > 0
    if deleted:
        logger.info("Question %d deleted", question_id)
    else:
        logger.warning(
            "Question %d not found for deletion in assignment %d",
            question_id,
            assignment_id,
        )
    return deleted


async def create_testcase(
    session: AsyncSession,
    question_id: int,
    assignment_id: int,
    input_data: str,
    expected_output: str,
) -> Testcase:
    logger.info(
        "Creating testcase for question %d in assignment %d", question_id, assignment_id
    )
    testcase = Testcase(
        question_id=question_id,
        assignment_id=assignment_id,
        input=input_data,
        expected_output=expected_output,
    )
    session.add(testcase)
    await session.commit()
    await session.refresh(testcase)
    logger.info("Testcase created (id=%d) for question %d", testcase.id, question_id)
    return testcase


async def get_testcases_by_question_id(
    session: AsyncSession, question_id: int, assignment_id: int
) -> list[Testcase]:
    logger.debug(
        "Fetching testcases for question %d in assignment %d",
        question_id,
        assignment_id,
    )
    result = await session.execute(
        select(Testcase).where(
            Testcase.question_id == question_id,
            Testcase.assignment_id == assignment_id,
        )
    )
    return result.scalars().all()


async def delete_testcase(session: AsyncSession, testcase_id: int) -> None:
    logger.info("Deleting testcase %d", testcase_id)
    await session.execute(delete(Testcase).where(Testcase.id == testcase_id))
    await session.commit()
    logger.info("Testcase %d deleted", testcase_id)
