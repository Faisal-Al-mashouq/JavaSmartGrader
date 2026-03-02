from decimal import Decimal

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import ConfidenceFlag


async def create_confidence_flag(
    session: AsyncSession,
    transcription_id: int,
    text_segment: str,
    confidence_score: Decimal,
    coordinates: str | None = None,
    suggestions: str | None = None,
) -> ConfidenceFlag:
    flag = ConfidenceFlag(
        transcription_id=transcription_id,
        text_segment=text_segment,
        confidence_score=confidence_score,
        coordinates=coordinates,
        suggestions=suggestions,
    )
    session.add(flag)
    await session.commit()
    await session.refresh(flag)
    return flag


async def get_confidence_flags_by_transcription_id(
    session: AsyncSession, transcription_id: int
) -> list[ConfidenceFlag]:
    result = await session.execute(
        select(ConfidenceFlag).where(
            ConfidenceFlag.transcription_id == transcription_id
        )
    )
    return result.scalars().all()


async def delete_confidence_flag(session: AsyncSession, flag_id: int) -> bool:
    result = await session.execute(
        delete(ConfidenceFlag).where(ConfidenceFlag.id == flag_id)
    )
    await session.commit()
    return result.rowcount > 0
