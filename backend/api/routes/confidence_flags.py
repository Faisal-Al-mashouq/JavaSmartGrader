import logging
import re
from decimal import Decimal

from db.crud.assignments import get_assignment_by_id
from db.crud.confidence_flags import (
    create_confidence_flag,
    delete_confidence_flag,
    get_confidence_flag_by_id,
    get_confidence_flags_by_transcription_id,
    update_confidence_flag,
)
from db.crud.grading import (
    delete_compile_result_by_submission_id,
    get_transcription_by_id,
    update_transcription_text,
)
from db.crud.questions import get_testcases_by_question_id
from db.crud.submissions import get_submission_by_id, update_submission_state
from db.models import SubmissionState, UserRole
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from schemas import ConfidenceFlagBase, ResolveFlagRequest, TestCase
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import get_current_user, require_role
from ..dependencies import get_db
from .helpers import start_job_process

logger = logging.getLogger(__name__)

router = APIRouter()


def apply_suggestion_to_text(
    transcribed_text: str,
    coordinates: str,
    suggestion: str,
) -> str:
    match = re.match(r"line:(\d+):word:(\d+)", coordinates)
    if not match:
        raise ValueError(f"Invalid coordinates format: {coordinates}")

    line_idx = int(match.group(1))
    word_idx = int(match.group(2))

    lines = transcribed_text.split("\n")
    if line_idx < 0 or line_idx >= len(lines):
        raise ValueError(f"Line index {line_idx} out of range (0-{len(lines) - 1})")

    target_line = lines[line_idx]
    tokens = re.findall(r"\S+", target_line)
    separators = re.split(r"\S+", target_line)

    if word_idx < 0 or word_idx >= len(tokens):
        raise ValueError(f"Word index {word_idx} out of range (0-{len(tokens) - 1})")

    tokens[word_idx] = suggestion

    rebuilt = ""
    for i, token in enumerate(tokens):
        rebuilt += separators[i] + token
    if len(separators) > len(tokens):
        rebuilt += separators[len(tokens)]

    lines[line_idx] = rebuilt
    return "\n".join(lines)


@router.post("/", response_model=ConfidenceFlagBase)
async def create_new_confidence_flag(
    transcription_id: int,
    text_segment: str,
    confidence_score: Decimal,
    coordinates: str | None = None,
    suggestions: str | None = None,
    session: AsyncSession = Depends(get_db),
    _current_user=Depends(require_role(UserRole.instructor)),
):
    logger.info(
        "Creating confidence flag for transcription %d (score=%s)",
        transcription_id,
        confidence_score,
    )
    try:
        flag = await create_confidence_flag(
            session=session,
            transcription_id=transcription_id,
            text_segment=text_segment,
            confidence_score=confidence_score,
            coordinates=coordinates,
            suggestions=suggestions,
        )
        logger.info(
            "Confidence flag created (id=%d) for transcription %d",
            flag.id,
            transcription_id,
        )
        return flag
    except IntegrityError:
        logger.error(
            "Failed to create confidence flag for transcription %d", transcription_id
        )
        raise HTTPException(
            status_code=400, detail="Failed to create confidence flag"
        ) from None


@router.get(
    "/transcription/{transcription_id}",
    response_model=list[ConfidenceFlagBase],
)
async def get_flags_for_transcription(
    transcription_id: int,
    session: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    logger.debug("Fetching confidence flags for transcription %d", transcription_id)
    return await get_confidence_flags_by_transcription_id(session, transcription_id)


@router.patch("/{flag_id}", response_model=ConfidenceFlagBase)
async def update_existing_confidence_flag(
    flag_id: int,
    text_segment: str | None = None,
    confidence_score: Decimal | None = None,
    coordinates: str | None = None,
    suggestions: str | None = None,
    session: AsyncSession = Depends(get_db),
    _current_user=Depends(require_role(UserRole.instructor)),
):
    logger.info("Updating confidence flag %d", flag_id)
    flag = await update_confidence_flag(
        session=session,
        flag_id=flag_id,
        text_segment=text_segment,
        confidence_score=confidence_score,
        coordinates=coordinates,
        suggestions=suggestions,
    )
    if not flag:
        logger.warning("Confidence flag not found: %d", flag_id)
        raise HTTPException(status_code=404, detail="Confidence flag not found")
    logger.info("Confidence flag %d updated successfully", flag_id)
    return flag


@router.post("/{flag_id}/resolve")
async def resolve_confidence_flag(
    flag_id: int,
    body: ResolveFlagRequest,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_db),
    _current_user=Depends(require_role(UserRole.instructor)),
):
    logger.info(
        "Resolving confidence flag %d with suggestion %r", flag_id, body.suggestion
    )

    flag = await get_confidence_flag_by_id(session, flag_id)
    if not flag:
        raise HTTPException(status_code=404, detail="Confidence flag not found")

    if not flag.coordinates:
        raise HTTPException(
            status_code=400,
            detail="Flag has no coordinates; cannot resolve automatically",
        )

    transcription = await get_transcription_by_id(session, flag.transcription_id)
    if not transcription or not transcription.transcribed_text:
        raise HTTPException(status_code=404, detail="Transcription not found or empty")

    try:
        corrected_text = apply_suggestion_to_text(
            transcription.transcribed_text, flag.coordinates, body.suggestion
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None

    await update_transcription_text(session, transcription.id, corrected_text)
    await delete_confidence_flag(session, flag_id)

    submission = await get_submission_by_id(session, transcription.submission_id)
    if not submission:
        raise HTTPException(status_code=404, detail="Associated submission not found")

    await delete_compile_result_by_submission_id(session, submission.id)
    await update_submission_state(session, submission.id, SubmissionState.processing)

    assignment = await get_assignment_by_id(session, submission.assignment_id)
    rubric_json = assignment.rubric_json if assignment else {}

    test_cases = await get_testcases_by_question_id(
        session, submission.question_id, submission.assignment_id
    )
    if not test_cases:
        test_cases_list = [TestCase(input="", expected_output="")]
    else:
        test_cases_list = [
            TestCase(input=tc.input, expected_output=tc.expected_output)
            for tc in test_cases
        ]

    background_tasks.add_task(
        start_job_process,
        submission_id=submission.id,
        question_id=submission.question_id,
        assignment_id=submission.assignment_id,
        student_id=submission.student_id,
        image_url=None,
        java_code=corrected_text,
        test_cases=test_cases_list,
        rubric_json=rubric_json,
    )

    logger.info(
        "Confidence flag %d resolved; re-grading submission %d",
        flag_id,
        submission.id,
    )
    return {
        "message": "Suggestion applied and re-grading started",
        "submission_id": submission.id,
    }


@router.delete("/{flag_id}")
async def remove_confidence_flag(
    flag_id: int,
    session: AsyncSession = Depends(get_db),
    _current_user=Depends(require_role(UserRole.instructor)),
):
    logger.info("Deleting confidence flag %d", flag_id)
    deleted = await delete_confidence_flag(session, flag_id)
    if not deleted:
        logger.warning("Confidence flag not found: %d", flag_id)
        raise HTTPException(status_code=404, detail="Confidence flag not found")
    logger.info("Confidence flag %d deleted successfully", flag_id)
    return {"message": "Confidence flag deleted successfully"}
