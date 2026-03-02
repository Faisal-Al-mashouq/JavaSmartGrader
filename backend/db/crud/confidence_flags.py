import logging
from decimal import Decimal

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import ConfidenceFlag

logger = logging.getLogger(__name__)


async def create_confidence_flag(
    session: AsyncSession,
    transcription_id: int,
    text_segment: str,
    confidence_score: Decimal,
    coordinates: str | None = None,
    suggestions: str | None = None,
) -> ConfidenceFlag:
    logger.info(
        "Creating confidence flag for transcription %d (score=%s)",
        transcription_id,
        confidence_score,
    )
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
    logger.info(
        "Confidence flag created (id=%d) for transcription %d",
        flag.id,
        transcription_id,
    )
    return flag


async def get_confidence_flags_by_transcription_id(
    session: AsyncSession, transcription_id: int
) -> list[ConfidenceFlag]:
    logger.debug("Fetching confidence flags for transcription %d", transcription_id)
    result = await session.execute(
        select(ConfidenceFlag).where(
            ConfidenceFlag.transcription_id == transcription_id
        )
    )
    return result.scalars().all()


async def delete_confidence_flag(session: AsyncSession, flag_id: int) -> bool:
    logger.info("Deleting confidence flag %d", flag_id)
    result = await session.execute(
        delete(ConfidenceFlag).where(ConfidenceFlag.id == flag_id)
    )
    await session.commit()
    deleted = result.rowcount > 0
    if deleted:
        logger.info("Confidence flag %d deleted", flag_id)
    else:
        logger.warning("Confidence flag %d not found for deletion", flag_id)
    return deleted
