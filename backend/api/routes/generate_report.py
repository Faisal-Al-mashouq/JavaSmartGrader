import logging

from db.crud.assignments import get_assignment_by_id
from db.crud.courses import get_course_by_id
from db.crud.generate_report import (
    create_generate_report,
    delete_generate_report,
    get_generate_report_by_id,
    get_generate_reports_by_assignment_id,
    update_generate_report,
)
from db.models import UserRole
from fastapi import APIRouter, Depends, HTTPException
from schemas import GenerateReportBase
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


@router.post("/assignment/{assignment_id}", response_model=GenerateReportBase)
async def create_new_report(
    assignment_id: int,
    report_text: str | None = None,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(require_role(UserRole.instructor)),
):
    logger.info(
        "Instructor %d creating report for assignment %d",
        current_user.id,
        assignment_id,
    )
    await _verify_instructor_owns_assignment(session, assignment_id, current_user.id)
    try:
        report = await create_generate_report(
            session=session,
            assignment_id=assignment_id,
            report_text=report_text,
        )
        logger.info(
            "Report created (id=%d) for assignment %d", report.id, assignment_id
        )
        return report
    except IntegrityError:
        logger.error("Failed to create report for assignment %d", assignment_id)
        raise HTTPException(status_code=400, detail="Failed to create report") from None


@router.get("/assignment/{assignment_id}", response_model=list[GenerateReportBase])
async def get_reports_for_assignment(
    assignment_id: int,
    session: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    logger.debug("Fetching reports for assignment %d", assignment_id)
    assignment = await get_assignment_by_id(session, assignment_id)
    if not assignment:
        logger.warning("Assignment not found: %d", assignment_id)
        raise HTTPException(status_code=404, detail="Assignment not found")
    return await get_generate_reports_by_assignment_id(session, assignment_id)


@router.get("/{report_id}", response_model=GenerateReportBase)
async def get_report(
    report_id: int,
    session: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    logger.debug("Fetching report %d", report_id)
    report = await get_generate_report_by_id(session, report_id)
    if not report:
        logger.warning("Report not found: %d", report_id)
        raise HTTPException(status_code=404, detail="Report not found")
    return report


@router.put("/{report_id}", response_model=GenerateReportBase)
async def update_report(
    report_id: int,
    report_text: str,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(require_role(UserRole.instructor)),
):
    logger.info("Instructor %d updating report %d", current_user.id, report_id)
    report = await get_generate_report_by_id(session, report_id)
    if not report:
        logger.warning("Report not found for update: %d", report_id)
        raise HTTPException(status_code=404, detail="Report not found")
    # Verify instructor owns the assignment
    await _verify_instructor_owns_assignment(
        session, report.assignment_id, current_user.id
    )
    updated = await update_generate_report(session, report_id, report_text)
    logger.info("Report %d updated successfully", report_id)
    return updated


@router.delete("/{report_id}")
async def remove_report(
    report_id: int,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(require_role(UserRole.instructor)),
):
    logger.info("Instructor %d deleting report %d", current_user.id, report_id)
    report = await get_generate_report_by_id(session, report_id)
    if not report:
        logger.warning("Report not found for deletion: %d", report_id)
        raise HTTPException(status_code=404, detail="Report not found")
    await _verify_instructor_owns_assignment(
        session, report.assignment_id, current_user.id
    )
    await delete_generate_report(session, report_id)
    logger.info("Report %d deleted successfully", report_id)
    return {"message": "Report deleted successfully"}
