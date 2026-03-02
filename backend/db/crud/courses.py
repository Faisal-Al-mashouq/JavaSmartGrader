from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models import Course, User


async def create_course(
    session: AsyncSession,
    name: str,
    instructor_id: int,
    description: str | None = None,
) -> Course:
    course = Course(
        name=name,
        instructor_id=instructor_id,
        description=description,
    )
    session.add(course)
    await session.commit()
    await session.refresh(course)
    return course


async def get_course_by_id(session: AsyncSession, course_id: int) -> Course | None:
    result = await session.execute(select(Course).where(Course.id == course_id))
    return result.scalar_one_or_none()


async def get_courses_by_instructor_id(
    session: AsyncSession, instructor_id: int
) -> list[Course]:
    result = await session.execute(
        select(Course).where(Course.instructor_id == instructor_id)
    )
    return result.scalars().all()


async def update_course(
    session: AsyncSession, course_id: int, **fields
) -> Course | None:
    await session.execute(update(Course).where(Course.id == course_id).values(**fields))
    await session.commit()
    return await get_course_by_id(session, course_id)


async def delete_course(session: AsyncSession, course_id: int) -> bool:
    result = await session.execute(delete(Course).where(Course.id == course_id))
    await session.commit()
    return result.rowcount > 0


async def enroll_student(
    session: AsyncSession, course_id: int, student_id: int
) -> Course | None:
    result = await session.execute(
        select(Course)
        .where(Course.id == course_id)
        .options(selectinload(Course.students))
    )
    course = result.scalar_one_or_none()
    if course is None:
        return None
    student = await session.get(User, student_id)
    if student is None:
        return None
    course.students.append(student)
    await session.commit()
    return course


async def unenroll_student(
    session: AsyncSession, course_id: int, student_id: int
) -> Course | None:
    result = await session.execute(
        select(Course)
        .where(Course.id == course_id)
        .options(selectinload(Course.students))
    )
    course = result.scalar_one_or_none()
    if course is None:
        return None
    student = await session.get(User, student_id)
    if student is None or student not in course.students:
        return None
    course.students.remove(student)
    await session.commit()
    return course
