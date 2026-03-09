import logging

from db.crud.assignments import get_assignment_by_id
from db.crud.courses import get_course_by_id
from db.crud.questions import (
    create_question,
    create_testcase,
    delete_question,
    delete_testcase,
    get_question_by_id,
    get_questions_by_assignment_id,
    get_testcases_by_question_id,
    update_question,
)
from db.models import UserRole
from fastapi import APIRouter, Depends, HTTPException
from schemas import QuestionBase, TestcaseBase
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import get_current_user, require_role
from ..dependencies import get_db

logger = logging.getLogger(__name__)

router = APIRouter()


async def _verify_instructor_owns_assignment(
    session, assignment_id: int, instructor_id: int
):
    assignment = await get_assignment_by_id(session, assignment_id)
    if not assignment:
        logger.warning("Assignment not found: %d", assignment_id)
        raise HTTPException(status_code=404, detail="Assignment not found")
    course = await get_course_by_id(session, assignment.course_id)
    if not course or course.instructor_id != instructor_id:
        logger.warning(
            "Instructor %d forbidden from accessing assignment %d",
            instructor_id,
            assignment_id,
        )
        raise HTTPException(status_code=403, detail="Forbidden")
    return assignment


# --- Question CRUD ---


@router.post("/", response_model=QuestionBase)
async def create_new_question(
    assignment_id: int,
    question_text: str,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(require_role(UserRole.instructor)),
):
    logger.info(
        "Instructor %d creating question for assignment %d",
        current_user.id,
        assignment_id,
    )
    await _verify_instructor_owns_assignment(session, assignment_id, current_user.id)
    try:
        question = await create_question(
            session=session,
            assignment_id=assignment_id,
            question_text=question_text,
        )
        logger.info(
            "Question created (id=%d) for assignment %d", question.id, assignment_id
        )
        return question
    except IntegrityError as exc:
        await session.rollback()
        logger.exception(
            "Failed to create question for assignment %d: %s",
            assignment_id,
            exc,
        )
        raise HTTPException(
            status_code=400, detail="Failed to create question"
        ) from None


@router.get("/", response_model=list[QuestionBase])
async def get_assignment_questions(
    assignment_id: int,
    session: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    logger.debug("Fetching questions for assignment %d", assignment_id)
    assignment = await get_assignment_by_id(session, assignment_id)
    if not assignment:
        logger.warning("Assignment not found: %d", assignment_id)
        raise HTTPException(status_code=404, detail="Assignment not found")
    return await get_questions_by_assignment_id(session, assignment_id)


@router.get("/{question_id}", response_model=QuestionBase)
async def get_question(
    assignment_id: int,
    question_id: int,
    session: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    logger.debug("Fetching question %d for assignment %d", question_id, assignment_id)
    question = await get_question_by_id(session, question_id, assignment_id)
    if not question:
        logger.warning(
            "Question %d not found in assignment %d", question_id, assignment_id
        )
        raise HTTPException(status_code=404, detail="Question not found")
    return question


@router.put("/{question_id}", response_model=QuestionBase)
async def update_question_details(
    assignment_id: int,
    question_id: int,
    question_text: str,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(require_role(UserRole.instructor)),
):
    logger.info(
        "Instructor %d updating question %d in assignment %d",
        current_user.id,
        question_id,
        assignment_id,
    )
    await _verify_instructor_owns_assignment(session, assignment_id, current_user.id)
    question = await get_question_by_id(session, question_id, assignment_id)
    if not question:
        logger.warning(
            "Question %d not found in assignment %d", question_id, assignment_id
        )
        raise HTTPException(status_code=404, detail="Question not found")
    updated = await update_question(
        session, question_id, assignment_id, question_text=question_text
    )
    logger.info("Question %d updated successfully", question_id)
    return updated


@router.delete("/{question_id}")
async def remove_question(
    assignment_id: int,
    question_id: int,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(require_role(UserRole.instructor)),
):
    logger.info(
        "Instructor %d deleting question %d from assignment %d",
        current_user.id,
        question_id,
        assignment_id,
    )
    await _verify_instructor_owns_assignment(session, assignment_id, current_user.id)
    deleted = await delete_question(session, question_id, assignment_id)
    if not deleted:
        logger.warning(
            "Question %d not found in assignment %d for deletion",
            question_id,
            assignment_id,
        )
        raise HTTPException(status_code=404, detail="Question not found")
    logger.info("Question %d deleted successfully", question_id)
    return {"message": "Question deleted successfully"}


# --- Testcase CRUD ---


@router.post("/{question_id}/testcases")
async def add_testcase(
    assignment_id: int,
    question_id: int,
    input_data: str,
    expected_output: str,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(require_role(UserRole.instructor)),
):
    logger.info(
        "Adding testcase for question %d in assignment %d", question_id, assignment_id
    )
    await _verify_instructor_owns_assignment(session, assignment_id, current_user.id)
    question = await get_question_by_id(session, question_id, assignment_id)
    if not question:
        logger.warning(
            "Question %d not found in assignment %d", question_id, assignment_id
        )
        raise HTTPException(status_code=404, detail="Question not found")
    try:
        await create_testcase(
            session, question_id, assignment_id, input_data, expected_output
        )
        logger.info("Testcase added for question %d", question_id)
        return {"message": "Testcase added successfully"}
    except IntegrityError:
        logger.error("Failed to add testcase for question %d", question_id)
        raise HTTPException(status_code=400, detail="Failed to add testcase") from None


@router.get("/{question_id}/testcases", response_model=list[TestcaseBase])
async def get_testcases(
    assignment_id: int,
    question_id: int,
    session: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    logger.debug(
        "Fetching testcases for question %d in assignment %d",
        question_id,
        assignment_id,
    )
    question = await get_question_by_id(session, question_id, assignment_id)
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    return await get_testcases_by_question_id(session, question_id, assignment_id)


@router.delete("/{question_id}/testcases/{testcase_id}")
async def remove_testcase(
    assignment_id: int,
    question_id: int,
    testcase_id: int,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(require_role(UserRole.instructor)),
):
    logger.info(
        "Deleting testcase %d for question %d in assignment %d",
        testcase_id,
        question_id,
        assignment_id,
    )
    await _verify_instructor_owns_assignment(session, assignment_id, current_user.id)
    await delete_testcase(session, testcase_id)
    logger.info("Testcase %d deleted successfully", testcase_id)
    return {"message": "Testcase deleted successfully"}
