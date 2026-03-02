from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import GenerateReport


async def create_generate_report(
    session: AsyncSession,
    assignment_id: int,
    report_text: str | None = None,
) -> GenerateReport:
    report = GenerateReport(
        assignment_id=assignment_id,
        report_text=report_text,
    )
    session.add(report)
    await session.commit()
    await session.refresh(report)
    return report


async def get_generate_report_by_id(
    session: AsyncSession, report_id: int
) -> GenerateReport | None:
    result = await session.execute(
        select(GenerateReport).where(GenerateReport.id == report_id)
    )
    return result.scalar_one_or_none()


async def get_generate_reports_by_assignment_id(
    session: AsyncSession, assignment_id: int
) -> list[GenerateReport]:
    result = await session.execute(
        select(GenerateReport).where(GenerateReport.assignment_id == assignment_id)
    )
    return result.scalars().all()


async def update_generate_report(
    session: AsyncSession, report_id: int, report_text: str
) -> GenerateReport | None:
    await session.execute(
        update(GenerateReport)
        .where(GenerateReport.id == report_id)
        .values(report_text=report_text)
    )
    await session.commit()
    return await get_generate_report_by_id(session, report_id)


async def delete_generate_report(session: AsyncSession, report_id: int) -> bool:
    result = await session.execute(
        delete(GenerateReport).where(GenerateReport.id == report_id)
    )
    await session.commit()
    return result.rowcount > 0
