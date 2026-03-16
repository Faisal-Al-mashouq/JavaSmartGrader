import logging

from db.crud.grading import (
    create_grade,
    get_ai_feedback_by_submission_id,
    get_compile_result_by_submission_id,
    get_grade_by_submission_id,
    get_transcription_by_submission_id,
    update_grade,
)
from db.crud.submissions import get_submission_by_id
from db.models import UserRole
from fastapi import APIRouter, Depends, HTTPException
from schemas import (
    AIFeedbackBase,
    CompileResultBase,
    GradeBase,
    TranscriptionBase,
    UserBase,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import get_current_user, require_role
from ..dependencies import get_db

logger = logging.getLogger(__name__)

router = APIRouter()


async def _verify_submission_access(
    session, submission_id: int, current_user: UserBase
):
    submission = await get_submission_by_id(session, submission_id)
    if not submission:
        logger.warning("Submission not found: %d", submission_id)
        raise HTTPException(status_code=404, detail="Submission not found")
    if (
        current_user.role != UserRole.instructor
        and submission.student_id != current_user.id
    ):
        logger.warning(
            "User %d forbidden from accessing submission %d grading",
            current_user.id,
            submission_id,
        )
        raise HTTPException(status_code=403, detail="Forbidden")
    return submission


@router.get("/{submission_id}/compile_result", response_model=CompileResultBase)
async def get_compile_result(
    submission_id: int,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    logger.debug("Fetching compile result for submission %d", submission_id)
    await _verify_submission_access(session, submission_id, current_user)
    compile_result = await get_compile_result_by_submission_id(session, submission_id)
    if not compile_result:
        logger.warning("Compile result not found for submission %d", submission_id)
        raise HTTPException(status_code=404, detail="Compile result not found")
    return compile_result


@router.get("/{submission_id}/transcription", response_model=TranscriptionBase)
async def get_transcription(
    submission_id: int,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    logger.debug("Fetching transcription for submission %d", submission_id)
    await _verify_submission_access(session, submission_id, current_user)
    transcription = await get_transcription_by_submission_id(session, submission_id)
    if not transcription:
        logger.warning("Transcription not found for submission %d", submission_id)
        raise HTTPException(status_code=404, detail="Transcription not found")
    return transcription


@router.get("/{submission_id}/ai_feedback", response_model=AIFeedbackBase)
async def get_ai_feedback(
    submission_id: int,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    logger.debug("Fetching AI feedback for submission %d", submission_id)
    await _verify_submission_access(session, submission_id, current_user)
    ai_feedback = await get_ai_feedback_by_submission_id(session, submission_id)
    if not ai_feedback:
        logger.warning("AI feedback not found for submission %d", submission_id)
        raise HTTPException(status_code=404, detail="AI feedback not found")
    return ai_feedback


@router.post("/{submission_id}/grade", response_model=GradeBase)
async def add_grade(
    submission_id: int,
    final_grade: float | None = None,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(require_role(UserRole.instructor)),
):
    logger.info(
        "Instructor %d adding grade for submission %d", current_user.id, submission_id
    )
    await _verify_submission_access(session, submission_id, current_user)
    try:
        grade = await create_grade(
            session=session,
            submission_id=submission_id,
            instructor_id=current_user.id,
            final_grade=final_grade,
        )
        logger.info("Grade added for submission %d: %s", submission_id, final_grade)
        return grade
    except IntegrityError:
        logger.error("Failed to add grade for submission %d", submission_id)
        raise HTTPException(status_code=400, detail="Failed to add grade") from None
    except Exception:
        logger.error("Duplicate grade entry for submission %d", submission_id)
        raise HTTPException(status_code=409, detail="Duplicate grade entry") from None


@router.put("/{submission_id}/grade", response_model=GradeBase)
async def reassign_grade(
    submission_id: int,
    grade: float,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(require_role(UserRole.instructor)),
):
    logger.info(
        "Instructor %d reassigning grade for submission %d to %s",
        current_user.id,
        submission_id,
        grade,
    )
    existing_grade = await get_grade_by_submission_id(session, submission_id)
    if not existing_grade:
        logger.warning("Grade not found for submission %d", submission_id)
        raise HTTPException(status_code=404, detail="Grade not found")
    if existing_grade.instructor_id != current_user.id:
        logger.warning(
            "Instructor %d forbidden from updating grade for submission %d",
            current_user.id,
            submission_id,
        )
        raise HTTPException(status_code=403, detail="Forbidden")
    try:
        updated_grade = await update_grade(
            session=session,
            submission_id=submission_id,
            new_final_grade=grade,
        )
        logger.info("Grade updated for submission %d to %s", submission_id, grade)
        return updated_grade
    except IntegrityError:
        logger.error("Failed to update grade for submission %d", submission_id)
        raise HTTPException(status_code=400, detail="Failed to update grade") from None
