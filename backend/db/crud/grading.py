from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import AIFeedback, CompileResult, Grade, Testcase, Transcription


async def create_testcase(
    session: AsyncSession, assignment_id: int, input_data: str, expected_output: str
) -> Testcase:
    testcase = Testcase(
        assignment_id=assignment_id,
        input=input_data,
        expected_output=expected_output,
    )
    session.add(testcase)
    await session.commit()
    await session.refresh(testcase)
    return testcase


async def get_testcases_by_assignment_id(
    session: AsyncSession, assignment_id: int
) -> list[Testcase]:

    result = await session.execute(
        select(Testcase).where(Testcase.assignment_id == assignment_id)
    )
    return result.scalars().all()


async def delete_testcase(session: AsyncSession, testcase_id: int) -> None:

    await session.execute(delete(Testcase).where(Testcase.id == testcase_id))
    await session.commit()


async def create_compile_result(
    session: AsyncSession,
    submission_id: int,
    compiled_ok: bool,
    compile_errors: str | None,
    runtime_errors: str | None,
    runtime_output: str | None,
) -> CompileResult:
    compile_result = CompileResult(
        submission_id=submission_id,
        compiled_ok=compiled_ok,
        compile_errors=compile_errors,
        runtime_errors=runtime_errors,
        runtime_output=runtime_output,
    )
    session.add(compile_result)
    await session.commit()
    await session.refresh(compile_result)
    return compile_result


async def get_compile_result_by_submission_id(
    session: AsyncSession, submission_id: int
) -> CompileResult | None:

    result = await session.execute(
        select(CompileResult).where(CompileResult.submission_id == submission_id)
    )
    return result.scalar_one_or_none()


async def create_transcription(
    session: AsyncSession, submission_id: int, feedback_text: str | None
) -> Transcription:
    transcription = Transcription(
        submission_id=submission_id,
        feedback_text=feedback_text,
    )
    session.add(transcription)
    await session.commit()
    await session.refresh(transcription)
    return transcription


async def get_transcription_by_submission_id(
    session: AsyncSession, submission_id: int
) -> Transcription | None:
    result = await session.execute(
        select(Transcription).where(Transcription.submission_id == submission_id)
    )
    return result.scalar_one_or_none()


async def create_ai_feedback(
    session: AsyncSession,
    submission_id: int,
    suggested_grade: float | None,
    feedback_text: str | None,
) -> AIFeedback:
    ai_feedback = AIFeedback(
        submission_id=submission_id,
        suggested_grade=suggested_grade,
        feedback_text=feedback_text,
    )
    session.add(ai_feedback)
    await session.commit()
    await session.refresh(ai_feedback)
    return ai_feedback


async def get_ai_feedback_by_submission_id(
    session: AsyncSession, submission_id: int
) -> AIFeedback | None:

    result = await session.execute(
        select(AIFeedback).where(AIFeedback.submission_id == submission_id)
    )
    return result.scalar_one_or_none()


async def create_grade(
    session: AsyncSession,
    submission_id: int,
    instructor_id: int,
    final_grade: float | None,
) -> Grade:
    grade = Grade(
        submission_id=submission_id,
        instructor_id=instructor_id,
        final_grade=final_grade,
    )
    session.add(grade)
    await session.commit()
    await session.refresh(grade)
    return grade


async def get_grade_by_submission_id(
    session: AsyncSession, submission_id: int
) -> Grade | None:

    result = await session.execute(
        select(Grade).where(Grade.submission_id == submission_id)
    )
    return result.scalar_one_or_none()


async def update_grade(
    session: AsyncSession, submission_id: int, new_final_grade: float
) -> Grade | None:
    await session.execute(
        update(Grade)
        .where(Grade.submission_id == submission_id)
        .values(final_grade=new_final_grade)
    )
    await session.commit()
    return await get_grade_by_submission_id(session, submission_id)
