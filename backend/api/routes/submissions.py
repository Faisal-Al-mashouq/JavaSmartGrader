import logging

from db.crud.courses import is_student_enrolled
from db.crud.submissions import (
    create_submission,
    delete_submission,
    get_submission_by_id,
    get_submissions_by_assignment_id,
    get_submissions_by_student_id,
    set_submission_image_url,
    update_submission_state,
)
from db.models import SubmissionState, UserRole
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from schemas import SubmissionBase, TestCase
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import get_current_user, require_role
from ..dependencies import get_db
from ..s3 import save_file
from .assignments import get_assignment_by_id
from .helpers import start_job_process
from .questions import get_question_by_id, get_testcases_by_question_id

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/", response_model=SubmissionBase)
async def submit_answer(
    question_id: int = Form(),
    assignment_id: int = Form(),
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_db),
    current_user=Depends(require_role(UserRole.student)),
):
    logger.info(
        "Student %d submitting answer for assignment %d", current_user.id, assignment_id
    )
    try:
        assignment = await get_assignment_by_id(session, assignment_id)
        if not assignment:
            raise HTTPException(status_code=404, detail="Assignment not found")
        if not await is_student_enrolled(
            session, current_user.id, assignment.course_id
        ):
            raise HTTPException(status_code=403, detail="Forbidden")
        rubric_json = assignment.rubric_json
        if not rubric_json:
            raise HTTPException(status_code=404, detail="Rubric not found")
        test_cases = await get_testcases_by_question_id(
            session, question_id, assignment_id
        )
        if not test_cases:
            test_cases = [TestCase(input="", expected_output="")]
        question = await get_question_by_id(session, question_id, assignment_id)
        if not question:
            raise HTTPException(status_code=404, detail="Question not found")

        logger.debug("Creating submission for question %d", question_id)
        submission = await create_submission(
            session=session,
            question_id=question_id,
            assignment_id=assignment_id,
            student_id=current_user.id,
        )
        image_url = await save_file(file, submission.id)
        await set_submission_image_url(session, submission.id, image_url)
        java_code = ""  # TODO: Implement Editable Java Code Editor
        await start_job_process(
            submission_id=submission.id,
            question_id=question_id,
            assignment_id=assignment_id,
            student_id=current_user.id,
            image_url=image_url,
            java_code=java_code,
            test_cases=[
                TestCase(input=tc.input, expected_output=tc.expected_output)
                for tc in test_cases
            ],
            rubric_json=rubric_json,
        )
        logger.info(
            "Submission created (id=%d) by student %d for assignment %d",
            submission.id,
            current_user.id,
            assignment_id,
        )
        return submission
    except IntegrityError:
        logger.error(
            "Failed to create submission for student %d, assignment %d",
            current_user.id,
            assignment_id,
        )
        raise HTTPException(
            status_code=400, detail="Failed to create submission"
        ) from None


@router.get("/me", response_model=list[SubmissionBase])
async def get_student_submissions(
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    logger.debug("Fetching submissions for student %d", current_user.id)
    return await get_submissions_by_student_id(session, current_user.id)


@router.get("/{submission_id}", response_model=SubmissionBase)
async def get_submission(
    submission_id: int,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    logger.debug("Fetching submission %d", submission_id)
    submission = await get_submission_by_id(session, submission_id)
    if not submission:
        logger.warning("Submission not found: %d", submission_id)
        raise HTTPException(status_code=404, detail="Submission not found")
    elif (
        submission.student_id != current_user.id
        and current_user.role != UserRole.instructor
    ):
        logger.warning(
            "User %d forbidden from accessing submission %d",
            current_user.id,
            submission_id,
        )
        raise HTTPException(status_code=403, detail="Forbidden")

    return submission


@router.get("/assignment/{assignment_id}", response_model=list[SubmissionBase])
async def get_assignment_submissions(
    assignment_id: int,
    session: AsyncSession = Depends(get_db),
    _current_user=Depends(require_role(UserRole.instructor)),
):
    logger.debug("Fetching submissions for assignment %d", assignment_id)
    return await get_submissions_by_assignment_id(session, assignment_id)


@router.put("/{submission_id}/state", response_model=SubmissionBase)
async def change_submission_state(
    submission_id: int,
    new_state: SubmissionState,
    session: AsyncSession = Depends(get_db),
    _current_user=Depends(require_role(UserRole.instructor)),
):
    logger.info("Changing submission %d state to %s", submission_id, new_state.value)
    submission = await update_submission_state(session, submission_id, new_state)
    if not submission:
        logger.warning("Submission not found for state change: %d", submission_id)
        raise HTTPException(status_code=404, detail="Submission not found")
    logger.info("Submission %d state changed to %s", submission_id, new_state.value)
    return submission


@router.delete("/{submission_id}")
async def remove_submission(
    submission_id: int,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(require_role(UserRole.student)),
):
    logger.info("Student %d deleting submission %d", current_user.id, submission_id)
    submission = await get_submission_by_id(session, submission_id)
    if not submission:
        logger.warning("Submission not found for deletion: %d", submission_id)
        raise HTTPException(status_code=404, detail="Submission not found")
    elif submission.student_id != current_user.id:
        logger.warning(
            "Student %d forbidden from deleting submission %d",
            current_user.id,
            submission_id,
        )
        raise HTTPException(status_code=403, detail="Forbidden")
    success = await delete_submission(session, submission_id)
    if not success:
        raise HTTPException(status_code=404, detail="Submission not found")
    logger.info("Submission %d deleted successfully", submission_id)
    return {"message": "Submission deleted successfully"}
