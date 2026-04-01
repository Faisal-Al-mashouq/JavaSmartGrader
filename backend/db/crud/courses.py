import logging

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models import Course, User
from ..models.main_db import course_students

logger = logging.getLogger(__name__)


async def create_course(
    session: AsyncSession,
    name: str,
    instructor_id: int,
    description: str | None = None,
) -> Course:
    logger.info("Creating course: '%s' (instructor_id=%d)", name, instructor_id)
    course = Course(
        name=name,
        instructor_id=instructor_id,
        description=description,
    )
    session.add(course)
    await session.commit()
    await session.refresh(course)
    logger.info("Course created: '%s' (id=%d)", course.name, course.id)
    return course


async def get_course_by_id(session: AsyncSession, course_id: int) -> Course | None:
    logger.debug("Looking up course by id: %d", course_id)
    result = await session.execute(select(Course).where(Course.id == course_id))
    return result.scalar_one_or_none()


async def get_course_students(session: AsyncSession, course_id: int) -> list[User]:
    result = await session.execute(
        select(Course)
        .where(Course.id == course_id)
        .options(selectinload(Course.students))
    )
    course = result.scalar_one_or_none()
    if course is None:
        return []
    return list(course.students)


async def get_courses_by_instructor_id(
    session: AsyncSession, instructor_id: int
) -> list[Course]:
    logger.debug("Fetching courses for instructor %d", instructor_id)
    result = await session.execute(
        select(Course).where(Course.instructor_id == instructor_id)
    )
    return result.scalars().all()


async def get_courses_by_student_id(
    session: AsyncSession, student_id: int
) -> list[Course]:
    logger.debug("Fetching enrolled courses for student %d", student_id)
    result = await session.execute(
        select(User)
        .where(User.id == student_id)
        .options(selectinload(User.enrolled_courses))
    )
    user = result.scalar_one_or_none()
    if user is None:
        return []
    return list(user.enrolled_courses)


async def is_student_enrolled(
    session: AsyncSession, student_id: int, course_id: int
) -> bool:
    result = await session.execute(
        select(course_students.c.course_id).where(
            course_students.c.course_id == course_id,
            course_students.c.student_id == student_id,
        )
    )
    return result.first() is not None


async def update_course(
    session: AsyncSession, course_id: int, **fields
) -> Course | None:
    logger.info("Updating course %d with fields: %s", course_id, list(fields.keys()))
    await session.execute(update(Course).where(Course.id == course_id).values(**fields))
    await session.commit()
    return await get_course_by_id(session, course_id)


async def delete_course(session: AsyncSession, course_id: int) -> bool:
    logger.info("Deleting course %d", course_id)
    result = await session.execute(delete(Course).where(Course.id == course_id))
    await session.commit()
    deleted = result.rowcount > 0
    if deleted:
        logger.info("Course %d deleted", course_id)
    else:
        logger.warning("Course %d not found for deletion", course_id)
    return deleted


async def enroll_student(
    session: AsyncSession, course_id: int, student_id: int
) -> Course | None:
    logger.info("Enrolling student %d in course %d", student_id, course_id)
    result = await session.execute(
        select(Course)
        .where(Course.id == course_id)
        .options(selectinload(Course.students))
    )
    course = result.scalar_one_or_none()
    if course is None:
        logger.warning("Course %d not found for enrollment", course_id)
        return None
    student = await session.get(User, student_id)
    if student is None:
        logger.warning("Student %d not found for enrollment", student_id)
        return None
    course.students.append(student)
    await session.commit()
    logger.info("Student %d enrolled in course %d", student_id, course_id)
    return course


async def unenroll_student(
    session: AsyncSession, course_id: int, student_id: int
) -> Course | None:
    logger.info("Unenrolling student %d from course %d", student_id, course_id)
    result = await session.execute(
        select(Course)
        .where(Course.id == course_id)
        .options(selectinload(Course.students))
    )
    course = result.scalar_one_or_none()
    if course is None:
        logger.warning("Course %d not found for unenrollment", course_id)
        return None
    student = await session.get(User, student_id)
    if student is None or student not in course.students:
        logger.warning(
            "Student %d not found or not enrolled in course %d", student_id, course_id
        )
        return None
    course.students.remove(student)
    await session.commit()
    logger.info("Student %d unenrolled from course %d", student_id, course_id)
    return course
