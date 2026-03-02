from db.crud.courses import (
    create_course,
    delete_course,
    enroll_student,
    get_course_by_id,
    get_courses_by_instructor_id,
    unenroll_student,
    update_course,
)
from db.crud.users import get_user_by_id
from db.models import UserRole
from fastapi import APIRouter, Depends, HTTPException
from schemas import CourseBase
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import get_current_user, require_role
from ..dependencies import get_db

router = APIRouter()


@router.post("/", response_model=CourseBase)
async def create_new_course(
    name: str,
    description: str | None = None,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(require_role(UserRole.instructor)),
):
    try:
        course = await create_course(
            session=session,
            name=name,
            instructor_id=current_user.id,
            description=description,
        )
        return course
    except IntegrityError:
        raise HTTPException(
            status_code=400, detail="Course name already exists"
        ) from None


@router.get("/me", response_model=list[CourseBase])
async def get_my_courses(
    session: AsyncSession = Depends(get_db),
    current_user=Depends(require_role(UserRole.instructor)),
):
    return await get_courses_by_instructor_id(session, current_user.id)


@router.get("/{course_id}", response_model=CourseBase)
async def get_course(
    course_id: int,
    session: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    course = await get_course_by_id(session, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    return course


@router.put("/{course_id}", response_model=CourseBase)
async def update_course_details(
    course_id: int,
    name: str | None = None,
    description: str | None = None,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(require_role(UserRole.instructor)),
):
    course = await get_course_by_id(session, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    if course.instructor_id != current_user.id:
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
        return updated
    except IntegrityError:
        raise HTTPException(
            status_code=400, detail="Course name already exists"
        ) from None


@router.delete("/{course_id}")
async def remove_course(
    course_id: int,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(require_role(UserRole.instructor)),
):
    course = await get_course_by_id(session, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    if course.instructor_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden")
    await delete_course(session, course_id)
    return {"message": "Course deleted successfully"}


@router.post("/{course_id}/enroll/{student_id}")
async def enroll_student_in_course(
    course_id: int,
    student_id: int,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(require_role(UserRole.instructor)),
):
    course = await get_course_by_id(session, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    if course.instructor_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden")
    user = await get_user_by_id(session, student_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.role != UserRole.student:
        raise HTTPException(status_code=400, detail="User is not a student")
    try:
        result = await enroll_student(session, course_id, student_id)
        if not result:
            raise HTTPException(status_code=400, detail="Failed to enroll student")
        return {"message": "Student enrolled successfully"}
    except IntegrityError:
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
    course = await get_course_by_id(session, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    if course.instructor_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden")
    user = await get_user_by_id(session, student_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.role != UserRole.student:
        raise HTTPException(status_code=400, detail="User is not a student")
    result = await unenroll_student(session, course_id, student_id)
    if not result:
        raise HTTPException(
            status_code=404, detail="Student is not enrolled in this course"
        )
    return {"message": "Student unenrolled successfully"}
