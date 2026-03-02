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

router = APIRouter()


async def _verify_instructor_owns_assignment(
    session, assignment_id: int, instructor_id: int
):
    assignment = await get_assignment_by_id(session, assignment_id)
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    course = await get_course_by_id(session, assignment.course_id)
    if not course or course.instructor_id != instructor_id:
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
    await _verify_instructor_owns_assignment(session, assignment_id, current_user.id)
    try:
        question = await create_question(
            session=session,
            assignment_id=assignment_id,
            question_text=question_text,
        )
        return question
    except IntegrityError:
        raise HTTPException(
            status_code=400, detail="Failed to create question"
        ) from None


@router.get("/", response_model=list[QuestionBase])
async def get_assignment_questions(
    assignment_id: int,
    session: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    assignment = await get_assignment_by_id(session, assignment_id)
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    return await get_questions_by_assignment_id(session, assignment_id)


@router.get("/{question_id}", response_model=QuestionBase)
async def get_question(
    assignment_id: int,
    question_id: int,
    session: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    question = await get_question_by_id(session, question_id, assignment_id)
    if not question:
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
    await _verify_instructor_owns_assignment(session, assignment_id, current_user.id)
    question = await get_question_by_id(session, question_id, assignment_id)
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    updated = await update_question(
        session, question_id, assignment_id, question_text=question_text
    )
    return updated


@router.delete("/{question_id}")
async def remove_question(
    assignment_id: int,
    question_id: int,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(require_role(UserRole.instructor)),
):
    await _verify_instructor_owns_assignment(session, assignment_id, current_user.id)
    deleted = await delete_question(session, question_id, assignment_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Question not found")
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
    await _verify_instructor_owns_assignment(session, assignment_id, current_user.id)
    question = await get_question_by_id(session, question_id, assignment_id)
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    try:
        await create_testcase(
            session, question_id, assignment_id, input_data, expected_output
        )
        return {"message": "Testcase added successfully"}
    except IntegrityError:
        raise HTTPException(status_code=400, detail="Failed to add testcase") from None


@router.get("/{question_id}/testcases", response_model=list[TestcaseBase])
async def get_testcases(
    assignment_id: int,
    question_id: int,
    session: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
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
    await _verify_instructor_owns_assignment(session, assignment_id, current_user.id)
    await delete_testcase(session, testcase_id)
    return {"message": "Testcase deleted successfully"}
