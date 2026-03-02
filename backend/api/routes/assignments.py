from datetime import datetime

from db.crud.assignments import (
    create_assignment,
    delete_assignment,
    get_assignment_by_id,
    get_assignments_by_course_id,
    update_assignment,
)
from db.crud.courses import get_course_by_id
from db.models import UserRole
from fastapi import APIRouter, Depends, HTTPException
from schemas import AssignmentBase
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


@router.post("/", response_model=AssignmentBase)
async def create_new_assignment(
    course_id: int,
    title: str,
    description: str | None = None,
    due_date: datetime | None = None,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(require_role(UserRole.instructor)),
):
    course = await get_course_by_id(session, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    if course.instructor_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden")
    try:
        assignment = await create_assignment(
            session=session,
            course_id=course_id,
            title=title,
            description=description,
            due_date=due_date,
        )
        return assignment
    except IntegrityError:
        raise HTTPException(
            status_code=400, detail="Failed to create assignment"
        ) from None


@router.get("/course/{course_id}", response_model=list[AssignmentBase])
async def get_course_assignments(
    course_id: int,
    session: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    return await get_assignments_by_course_id(session, course_id)


@router.get("/{assignment_id}", response_model=AssignmentBase)
async def get_assignment(
    assignment_id: int,
    session: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    assignment = await get_assignment_by_id(session, assignment_id)
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    return assignment


@router.put("/{assignment_id}", response_model=AssignmentBase)
async def update_assignment_details(
    assignment_id: int,
    title: str | None = None,
    description: str | None = None,
    due_date: datetime | None = None,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(require_role(UserRole.instructor)),
):
    await _verify_instructor_owns_assignment(session, assignment_id, current_user.id)

    fields = {
        k: v
        for k, v in {
            "title": title,
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
    await _verify_instructor_owns_assignment(session, assignment_id, current_user.id)
    await delete_assignment(session, assignment_id)
    return {"message": "Assignment deleted successfully"}
