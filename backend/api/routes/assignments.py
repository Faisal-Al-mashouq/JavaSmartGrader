from datetime import datetime

from db.crud.assignments import (
    create_assignment,
    create_testcase,
    delete_assignment,
    delete_testcase,
    get_assignment_by_id,
    get_assignments_by_instructor_id,
    get_testcases_by_assignment_id,
    update_assignment,
)
from db.models import UserRole
from fastapi import APIRouter, Depends, HTTPException
from schemas import AssignmentBase, TestcaseBase
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import get_current_user, require_role
from ..dependencies import get_db

router = APIRouter()


@router.post("/", response_model=AssignmentBase)
async def create_new_assignment(
    title: str,
    question: str,
    description: str | None = None,
    due_date: datetime | None = None,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(require_role(UserRole.instructor)),
):
    try:
        assignment = await create_assignment(
            session=session,
            instructor_id=current_user.id,
            title=title,
            question=question,
            description=description,
            due_date=due_date,
        )
        return assignment
    except IntegrityError:
        raise HTTPException(
            status_code=400, detail="Failed to create assignment"
        ) from None


@router.get("/instructors", response_model=list[AssignmentBase])
async def get_instructor_assignments(
    session: AsyncSession = Depends(get_db),
    current_user=Depends(require_role(UserRole.instructor)),
):
    return await get_assignments_by_instructor_id(session, current_user.id)


@router.get("/{assignment_id}", response_model=AssignmentBase)
async def get_assignment(
    assignment_id: int,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    assignment = await get_assignment_by_id(session, assignment_id)
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    elif (
        assignment.instructor_id != current_user.id
        and current_user.role != UserRole.student
    ):
        raise HTTPException(status_code=403, detail="Forbidden")
    return assignment


@router.put("/{assignment_id}", response_model=AssignmentBase)
async def update_assignment_details(
    assignment_id: int,
    title: str | None = None,
    question: str | None = None,
    description: str | None = None,
    due_date: datetime | None = None,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(require_role(UserRole.instructor)),
):
    assignment = await get_assignment_by_id(session, assignment_id)
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    if assignment.instructor_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden")

    fields = {
        k: v
        for k, v in {
            "title": title,
            "question": question,
            "description": description,
            "due_date": due_date,
        }.items()
        if v is not None
    }

    if not fields:
        raise HTTPException(status_code=400, detail="No fields provided for update")

    updated = await update_assignment(session, assignment_id, **fields)
    return updated


@router.delete("/{assignment_id}")
async def remove_assignment(
    assignment_id: int,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(require_role(UserRole.instructor)),
):
    assignment = await get_assignment_by_id(session, assignment_id)
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    if assignment.instructor_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden")
    await delete_assignment(session, assignment_id)
    return {"message": "Assignment deleted successfully"}


@router.post("/{assignment_id}/testcases")
async def add_testcase(
    assignment_id: int,
    input_data: str,
    expected_output: str,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(require_role(UserRole.instructor)),
):
    assignment = await get_assignment_by_id(session, assignment_id)
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    if assignment.instructor_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden")
    try:
        await create_testcase(session, assignment_id, input_data, expected_output)
        return {"message": "Testcase added successfully"}
    except IntegrityError:
        raise HTTPException(status_code=400, detail="Failed to add testcase") from None


@router.get("/{assignment_id}/testcases", response_model=list[TestcaseBase])
async def get_testcases(
    assignment_id: int,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(require_role(UserRole.instructor)),
):
    assignment = await get_assignment_by_id(session, assignment_id)
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    if assignment.instructor_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden")
    return await get_testcases_by_assignment_id(session, assignment_id)


@router.delete("/{assignment_id}/testcases")
async def remove_testcase(
    assignment_id: int,
    input_data: str,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(require_role(UserRole.instructor)),
):
    assignment = await get_assignment_by_id(session, assignment_id)
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    if assignment.instructor_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden")
    test_cases = await get_testcases_by_assignment_id(session, assignment_id)
    test_case = next((tc for tc in test_cases if tc.input == input_data), None)
    if not test_case:
        raise HTTPException(status_code=404, detail="Testcase not found")
    await delete_testcase(session, test_case.id)
    return {"message": "Testcase deleted successfully"}
