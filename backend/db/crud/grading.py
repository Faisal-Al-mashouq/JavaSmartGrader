import logging
from datetime import UTC, datetime

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import AIFeedback, CompileResult, Grade, Transcription

logger = logging.getLogger(__name__)


async def create_compile_result(
    session: AsyncSession,
    submission_id: int,
    compiled_ok: bool,
    compile_errors: str | None,
    runtime_errors: str | None,
    runtime_outputs: str | None,
) -> CompileResult:
    logger.info(
        "Creating compile result for submission %d (compiled_ok=%s)",
        submission_id,
        compiled_ok,
    )
    compile_result = CompileResult(
        submission_id=submission_id,
        compiled_ok=compiled_ok,
        compile_errors=compile_errors,
        runtime_errors=runtime_errors,
        runtime_outputs=runtime_outputs,
    )
    session.add(compile_result)
    await session.commit()
    await session.refresh(compile_result)
    logger.info("Compile result created for submission %d", submission_id)
    return compile_result


async def get_compile_result_by_submission_id(
    session: AsyncSession, submission_id: int
) -> CompileResult | None:
    logger.debug("Fetching compile result for submission %d", submission_id)
    result = await session.execute(
        select(CompileResult).where(CompileResult.submission_id == submission_id)
    )
    return result.scalar_one_or_none()


async def create_transcription(
    session: AsyncSession, submission_id: int, transcribed_text: str | None
) -> Transcription:
    logger.info("Creating transcription for submission %d", submission_id)
    transcription = Transcription(
        submission_id=submission_id,
        transcribed_text=transcribed_text,
    )
    session.add(transcription)
    await session.commit()
    await session.refresh(transcription)
    logger.info("Transcription created for submission %d", submission_id)
    return transcription


async def get_transcription_by_submission_id(
    session: AsyncSession, submission_id: int
) -> Transcription | None:
    logger.debug("Fetching transcription for submission %d", submission_id)
    result = await session.execute(
        select(Transcription).where(Transcription.submission_id == submission_id)
    )
    return result.scalar_one_or_none()


async def get_transcription_by_id(
    session: AsyncSession, transcription_id: int
) -> Transcription | None:
    logger.debug("Fetching transcription %d", transcription_id)
    result = await session.execute(
        select(Transcription).where(Transcription.id == transcription_id)
    )
    return result.scalar_one_or_none()


async def update_transcription_text(
    session: AsyncSession, transcription_id: int, new_text: str
) -> Transcription | None:
    logger.info("Updating transcription text for transcription %d", transcription_id)
    result = await session.execute(
        select(Transcription).where(Transcription.id == transcription_id)
    )
    transcription = result.scalar_one_or_none()
    if transcription is None:
        logger.warning("Transcription %d not found for update", transcription_id)
        return None
    transcription.transcribed_text = new_text
    await session.commit()
    await session.refresh(transcription)
    logger.info("Transcription %d text updated", transcription_id)
    return transcription


async def delete_compile_result_by_submission_id(
    session: AsyncSession, submission_id: int
) -> bool:
    logger.info("Deleting compile result for submission %d", submission_id)
    result = await session.execute(
        delete(CompileResult).where(CompileResult.submission_id == submission_id)
    )
    await session.commit()
    deleted = result.rowcount > 0
    if deleted:
        logger.info("Compile result deleted for submission %d", submission_id)
    else:
        logger.debug("No compile result found for submission %d", submission_id)
    return deleted


async def create_ai_feedback(
    session: AsyncSession,
    submission_id: int,
    suggested_grade: float | None,
    instructor_guidance: str | None,
    student_feedback: str | None,
) -> AIFeedback:
    logger.info(
        "Creating AI feedback for submission %d (suggested_grade=%s)",
        submission_id,
        suggested_grade,
    )
    ai_feedback = AIFeedback(
        submission_id=submission_id,
        suggested_grade=suggested_grade,
        instructor_guidance=instructor_guidance,
        student_feedback=student_feedback,
    )
    session.add(ai_feedback)
    await session.commit()
    await session.refresh(ai_feedback)
    logger.info("AI feedback created for submission %d", submission_id)
    return ai_feedback


async def get_ai_feedback_by_submission_id(
    session: AsyncSession, submission_id: int
) -> AIFeedback | None:
    logger.debug("Fetching AI feedback for submission %d", submission_id)
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
    logger.info(
        "Creating grade for submission %d by instructor %d (grade=%s)",
        submission_id,
        instructor_id,
        final_grade,
    )
    grade = Grade(
        submission_id=submission_id,
        instructor_id=instructor_id,
        final_grade=final_grade,
        published_at=datetime.now(UTC) if final_grade is not None else None,
    )
    session.add(grade)
    await session.commit()
    await session.refresh(grade)
    logger.info("Grade created for submission %d", submission_id)
    return grade


async def get_grade_by_submission_id(
    session: AsyncSession, submission_id: int
) -> Grade | None:
    logger.debug("Fetching grade for submission %d", submission_id)
    result = await session.execute(
        select(Grade).where(Grade.submission_id == submission_id)
    )
    return result.scalar_one_or_none()


async def update_grade(
    session: AsyncSession, submission_id: int, new_final_grade: float
) -> Grade | None:
    logger.info(
        "Updating grade for submission %d to %s", submission_id, new_final_grade
    )
    await session.execute(
        update(Grade)
        .where(Grade.submission_id == submission_id)
        .values(final_grade=new_final_grade, published_at=datetime.now(UTC))
    )
    await session.commit()
    return await get_grade_by_submission_id(session, submission_id)
