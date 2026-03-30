import logging

from db.crud.courses import (
    create_course,
    delete_course,
    enroll_student,
    get_course_by_id,
    get_course_students,
    get_courses_by_instructor_id,
    get_courses_by_student_id,
    is_student_enrolled,
    unenroll_student,
    update_course,
)
from db.crud.users import get_user_by_id
from db.models import UserRole
from fastapi import APIRouter, Depends, HTTPException
from schemas import CourseBase, UserBase
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import get_current_user, require_role
from ..dependencies import get_db

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/", response_model=CourseBase)
async def create_new_course(
    name: str,
    description: str | None = None,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(require_role(UserRole.instructor)),
):
    logger.info("Instructor %d creating course: %s", current_user.id, name)
    try:
        course = await create_course(
            session=session,
            name=name,
            instructor_id=current_user.id,
            description=description,
        )
        logger.info("Course created successfully: %s (id=%d)", course.name, course.id)
        return course
    except IntegrityError:
        logger.warning("Course creation failed - duplicate name: %s", name)
        raise HTTPException(
            status_code=400, detail="Course name already exists"
        ) from None


@router.get("/me", response_model=list[CourseBase])
async def get_my_courses(
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if current_user.role == UserRole.instructor:
        logger.debug("Fetching courses for instructor %d", current_user.id)
        return await get_courses_by_instructor_id(session, current_user.id)
    if current_user.role == UserRole.student:
        logger.debug("Fetching enrolled courses for student %d", current_user.id)
        return await get_courses_by_student_id(session, current_user.id)
    raise HTTPException(status_code=403, detail="Forbidden")


@router.get("/{course_id}", response_model=CourseBase)
async def get_course(
    course_id: int,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    logger.debug("Fetching course %d", course_id)
    course = await get_course_by_id(session, course_id)
    if not course:
        logger.warning("Course not found: %d", course_id)
        raise HTTPException(status_code=404, detail="Course not found")
    if current_user.role == UserRole.student:
        if not await is_student_enrolled(session, current_user.id, course_id):
            raise HTTPException(status_code=403, detail="Forbidden")
    return course


@router.get("/{course_id}/students", response_model=list[UserBase])
async def list_course_students(
    course_id: int,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(require_role(UserRole.instructor)),
):
    course = await get_course_by_id(session, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    if course.instructor_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden")
    return await get_course_students(session, course_id)


@router.put("/{course_id}", response_model=CourseBase)
async def update_course_details(
    course_id: int,
    name: str | None = None,
    description: str | None = None,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(require_role(UserRole.instructor)),
):
    logger.info("Instructor %d updating course %d", current_user.id, course_id)
    course = await get_course_by_id(session, course_id)
    if not course:
        logger.warning("Course not found for update: %d", course_id)
        raise HTTPException(status_code=404, detail="Course not found")
    if course.instructor_id != current_user.id:
        logger.warning(
            "Instructor %d forbidden from updating course %d",
            current_user.id,
            course_id,
        )
        raise HTTPException(status_code=403, detail="Forbidden")

    fields = {
        k: v
        for k, v in {"name": name, "description": description}.items()
        if v is not None
    }
    if not fields:
        raise HTTPException(status_code=400, detail="No fields provided for update")

    try:
        updated = await update_course(session, course_id, **fields)
        logger.info("Course %d updated successfully", course_id)
        return updated
    except IntegrityError:
        logger.warning("Course update failed - duplicate name for course %d", course_id)
        raise HTTPException(
            status_code=400, detail="Course name already exists"
        ) from None


@router.delete("/{course_id}")
async def remove_course(
    course_id: int,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(require_role(UserRole.instructor)),
):
    logger.info("Instructor %d deleting course %d", current_user.id, course_id)
    course = await get_course_by_id(session, course_id)
    if not course:
        logger.warning("Course not found for deletion: %d", course_id)
        raise HTTPException(status_code=404, detail="Course not found")
    if course.instructor_id != current_user.id:
        logger.warning(
            "Instructor %d forbidden from deleting course %d",
            current_user.id,
            course_id,
        )
        raise HTTPException(status_code=403, detail="Forbidden")
    await delete_course(session, course_id)
    logger.info("Course %d deleted successfully", course_id)
    return {"message": "Course deleted successfully"}


@router.post("/{course_id}/enroll/{student_id}")
async def enroll_student_in_course(
    course_id: int,
    student_id: int,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(require_role(UserRole.instructor)),
):
    logger.info("Enrolling student %d in course %d", student_id, course_id)
    course = await get_course_by_id(session, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    if course.instructor_id != current_user.id:
        logger.warning(
            "Instructor %d forbidden from enrolling in course %d",
            current_user.id,
            course_id,
        )
        raise HTTPException(status_code=403, detail="Forbidden")
    user = await get_user_by_id(session, student_id)
    if not user:
        logger.warning("Student not found for enrollment: %d", student_id)
        raise HTTPException(status_code=404, detail="User not found")
    if user.role != UserRole.student:
        logger.warning("User %d is not a student, cannot enroll", student_id)
        raise HTTPException(status_code=400, detail="User is not a student")
    try:
        result = await enroll_student(session, course_id, student_id)
        if not result:
            logger.error(
                "Failed to enroll student %d in course %d", student_id, course_id
            )
            raise HTTPException(status_code=400, detail="Failed to enroll student")
        logger.info(
            "Student %d enrolled in course %d successfully", student_id, course_id
        )
        return {"message": "Student enrolled successfully"}
    except IntegrityError:
        logger.warning(
            "Student %d already enrolled in course %d", student_id, course_id
        )
        raise HTTPException(
            status_code=409, detail="Student is already enrolled in this course"
        ) from None


@router.delete("/{course_id}/enroll/{student_id}")
async def unenroll_student_from_course(
    course_id: int,
    student_id: int,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(require_role(UserRole.instructor)),
):
    logger.info("Unenrolling student %d from course %d", student_id, course_id)
    course = await get_course_by_id(session, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    if course.instructor_id != current_user.id:
        logger.warning(
            "Instructor %d forbidden from unenrolling in course %d",
            current_user.id,
            course_id,
        )
        raise HTTPException(status_code=403, detail="Forbidden")
    user = await get_user_by_id(session, student_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.role != UserRole.student:
        raise HTTPException(status_code=400, detail="User is not a student")
    result = await unenroll_student(session, course_id, student_id)
    if not result:
        logger.warning("Student %d not enrolled in course %d", student_id, course_id)
        raise HTTPException(
            status_code=404, detail="Student is not enrolled in this course"
        )
    logger.info(
        "Student %d unenrolled from course %d successfully", student_id, course_id
    )
    return {"message": "Student unenrolled successfully"}
