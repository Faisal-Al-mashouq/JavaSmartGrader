from decimal import Decimal

from db.crud.confidence_flags import (
    create_confidence_flag,
    delete_confidence_flag,
    get_confidence_flags_by_transcription_id,
)
from db.models import UserRole
from fastapi import APIRouter, Depends, HTTPException
from schemas import ConfidenceFlagBase
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import get_current_user, require_role
from ..dependencies import get_db

router = APIRouter()


@router.post("/", response_model=ConfidenceFlagBase)
async def create_new_confidence_flag(
    transcription_id: int,
    text_segment: str,
    confidence_score: Decimal,
    coordinates: str | None = None,
    suggestions: str | None = None,
    session: AsyncSession = Depends(get_db),
    _current_user=Depends(require_role(UserRole.instructor)),
):
    try:
        flag = await create_confidence_flag(
            session=session,
            transcription_id=transcription_id,
            text_segment=text_segment,
            confidence_score=confidence_score,
            coordinates=coordinates,
            suggestions=suggestions,
        )
        return flag
    except IntegrityError:
        raise HTTPException(
            status_code=400, detail="Failed to create confidence flag"
        ) from None


@router.get(
    "/transcription/{transcription_id}",
    response_model=list[ConfidenceFlagBase],
)
async def get_flags_for_transcription(
    transcription_id: int,
    session: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    return await get_confidence_flags_by_transcription_id(session, transcription_id)


@router.delete("/{flag_id}")
async def remove_confidence_flag(
    flag_id: int,
    session: AsyncSession = Depends(get_db),
    _current_user=Depends(require_role(UserRole.instructor)),
):
    deleted = await delete_confidence_flag(session, flag_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Confidence flag not found")
    return {"message": "Confidence flag deleted successfully"}
