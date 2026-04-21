import logging
from datetime import UTC, datetime

from db.crud.assignments import (
    create_assignment,
    delete_assignment,
    get_assignment_by_id,
    get_assignments_by_course_id,
    update_assignment,
)
from db.crud.courses import get_course_by_id, is_student_enrolled
from db.models import UserRole
from fastapi import APIRouter, Depends, HTTPException
from schemas import AssignmentBase, RubricUpdate
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import get_current_user, require_role
from ..dependencies import get_db

logger = logging.getLogger(__name__)

router = APIRouter()


def _is_visible_to_students(assignment) -> bool:
    if assignment.visible_at is None:
        return True
    return assignment.visible_at <= datetime.now(UTC)


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
    visible_at: datetime | None = None,
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
            visible_at=visible_at,
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
    current_user=Depends(get_current_user),
):
    logger.debug("Fetching assignments for course %d", course_id)
    if current_user.role == UserRole.student:
        if not await is_student_enrolled(session, current_user.id, course_id):
            logger.warning(
                "Student %d not enrolled in course %d", current_user.id, course_id
            )
            raise HTTPException(status_code=403, detail="Forbidden")
    assignments = await get_assignments_by_course_id(session, course_id)
    if current_user.role == UserRole.student:
        assignments = [a for a in assignments if _is_visible_to_students(a)]
    return assignments


@router.get("/{assignment_id}", response_model=AssignmentBase)
async def get_assignment(
    assignment_id: int,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    logger.debug("Fetching assignment %d", assignment_id)
    assignment = await get_assignment_by_id(session, assignment_id)
    if not assignment:
        logger.warning("Assignment not found: %d", assignment_id)
        raise HTTPException(status_code=404, detail="Assignment not found")
    if current_user.role == UserRole.student:
        if not await is_student_enrolled(
            session, current_user.id, assignment.course_id
        ):
            logger.warning(
                "Student %d forbidden from assignment %d",
                current_user.id,
                assignment_id,
            )
            raise HTTPException(status_code=403, detail="Forbidden")
        if not _is_visible_to_students(assignment):
            raise HTTPException(status_code=403, detail="Assignment not yet visible")
    return assignment


@router.put("/{assignment_id}", response_model=AssignmentBase)
async def update_assignment_details(
    assignment_id: int,
    title: str | None = None,
    description: str | None = None,
    due_date: datetime | None = None,
    visible_at: datetime | None = None,
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
            "visible_at": visible_at,
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
    try:
        await delete_assignment(session, assignment_id)
    except IntegrityError:
        logger.warning(
            "Cannot delete assignment %d: has dependent records", assignment_id
        )
        raise HTTPException(
            status_code=409,
            detail="Cannot delete assignment: it still has dependent records",
        ) from None
    logger.info("Assignment %d deleted successfully", assignment_id)
    return {"message": "Assignment deleted successfully"}


@router.get("/{assignment_id}/rubric")
async def get_assignment_rubric(
    assignment_id: int,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(require_role(UserRole.instructor)),
):
    logger.debug("Fetching rubric for assignment %d", assignment_id)
    assignment = await _verify_instructor_owns_assignment(
        session, assignment_id, current_user.id
    )
    return {"criteria": assignment.rubric_json.get("criteria", [])}


@router.put("/{assignment_id}/rubric")
async def update_assignment_rubric(
    assignment_id: int,
    body: RubricUpdate,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(require_role(UserRole.instructor)),
):
    logger.info(
        "Instructor %d updating rubric for assignment %d",
        current_user.id,
        assignment_id,
    )
    await _verify_instructor_owns_assignment(session, assignment_id, current_user.id)
    rubric_json = {"criteria": [c.model_dump() for c in body.criteria]}
    updated = await update_assignment(session, assignment_id, rubric_json=rubric_json)
    logger.info("Rubric updated for assignment %d", assignment_id)
    return {"criteria": updated.rubric_json.get("criteria", [])}
