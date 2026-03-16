import logging

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import GenerateReport

logger = logging.getLogger(__name__)


async def create_generate_report(
    session: AsyncSession,
    assignment_id: int,
    report_text: str | None = None,
) -> GenerateReport:
    logger.info("Creating report for assignment %d", assignment_id)
    report = GenerateReport(
        assignment_id=assignment_id,
        report_text=report_text,
    )
    session.add(report)
    await session.commit()
    await session.refresh(report)
    logger.info("Report created (id=%d) for assignment %d", report.id, assignment_id)
    return report


async def get_generate_report_by_id(
    session: AsyncSession, report_id: int
) -> GenerateReport | None:
    logger.debug("Looking up report by id: %d", report_id)
    result = await session.execute(
        select(GenerateReport).where(GenerateReport.id == report_id)
    )
    return result.scalar_one_or_none()


async def get_generate_reports_by_assignment_id(
    session: AsyncSession, assignment_id: int
) -> list[GenerateReport]:
    logger.debug("Fetching reports for assignment %d", assignment_id)
    result = await session.execute(
        select(GenerateReport).where(GenerateReport.assignment_id == assignment_id)
    )
    return result.scalars().all()


async def update_generate_report(
    session: AsyncSession, report_id: int, report_text: str
) -> GenerateReport | None:
    logger.info("Updating report %d", report_id)
    await session.execute(
        update(GenerateReport)
        .where(GenerateReport.id == report_id)
        .values(report_text=report_text)
    )
    await session.commit()
    return await get_generate_report_by_id(session, report_id)


async def delete_generate_report(session: AsyncSession, report_id: int) -> bool:
    logger.info("Deleting report %d", report_id)
    result = await session.execute(
        delete(GenerateReport).where(GenerateReport.id == report_id)
    )
    await session.commit()
    deleted = result.rowcount > 0
    if deleted:
        logger.info("Report %d deleted", report_id)
    else:
        logger.warning("Report %d not found for deletion", report_id)
    return deleted
