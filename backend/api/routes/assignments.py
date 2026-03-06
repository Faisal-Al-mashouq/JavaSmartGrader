import logging
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


@router.post("/", response_model=AssignmentBase)
async def create_new_assignment(
    course_id: int,
    rubric_json: dict,
    title: str,
    description: str | None = None,
    due_date: datetime | None = None,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(require_role(UserRole.instructor)),
):
    logger.info(
        "Instructor %d creating assignment '%s' for course %d",
        current_user.id,
        title,
        course_id,
    )
    course = await get_course_by_id(session, course_id)
    if not course:
        logger.warning("Course not found: %d", course_id)
        raise HTTPException(status_code=404, detail="Course not found")
    if course.instructor_id != current_user.id:
        logger.warning(
            "Instructor %d forbidden from creating assignment in course %d",
            current_user.id,
            course_id,
        )
        raise HTTPException(status_code=403, detail="Forbidden")
    try:
        assignment = await create_assignment(
            session=session,
            course_id=course_id,
            rubric_json=rubric_json,
            title=title,
            description=description,
            due_date=due_date,
        )
        logger.info(
            "Assignment created: '%s' (id=%d) in course %d",
            assignment.title,
            assignment.id,
            course_id,
        )
        return assignment
    except IntegrityError:
        logger.error("Failed to create assignment '%s' in course %d", title, course_id)
        raise HTTPException(
            status_code=400, detail="Failed to create assignment"
        ) from None


@router.get("/course/{course_id}", response_model=list[AssignmentBase])
async def get_course_assignments(
    course_id: int,
    session: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    logger.debug("Fetching assignments for course %d", course_id)
    return await get_assignments_by_course_id(session, course_id)


@router.get("/{assignment_id}", response_model=AssignmentBase)
async def get_assignment(
    assignment_id: int,
    session: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    logger.debug("Fetching assignment %d", assignment_id)
    assignment = await get_assignment_by_id(session, assignment_id)
    if not assignment:
        logger.warning("Assignment not found: %d", assignment_id)
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
    logger.info("Instructor %d updating assignment %d", current_user.id, assignment_id)
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
    logger.info("Assignment %d updated successfully", assignment_id)
    return updated


@router.delete("/{assignment_id}")
async def remove_assignment(
    assignment_id: int,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(require_role(UserRole.instructor)),
):
    logger.info("Instructor %d deleting assignment %d", current_user.id, assignment_id)
    await _verify_instructor_owns_assignment(session, assignment_id, current_user.id)
    await delete_assignment(session, assignment_id)
    logger.info("Assignment %d deleted successfully", assignment_id)
    return {"message": "Assignment deleted successfully"}
