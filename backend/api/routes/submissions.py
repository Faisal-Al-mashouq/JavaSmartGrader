from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError

from db.crud.submissions import (
    create_submission,
    delete_submission,
    get_submission_by_id,
    get_submissions_by_assignment_id,
    get_submissions_by_student_id,
    update_submission_state,
)
from db.models import SubmissionState, UserRole
from schemas import SubmissionBase

from ..auth import get_current_user, require_role
from ..dependencies import get_db

router = APIRouter()


@router.post("/", response_model=SubmissionBase)
async def submit_answer(
    assignment_id: int,
    image_url: str | None = None,
):
    session = Depends(get_db)
    current_user = Depends(require_role(UserRole.student))

    try:
        submission = await create_submission(
            session=session,
            assignment_id=assignment_id,
            student_id=current_user.id,
            image_url=image_url,
        )
        return submission
    except IntegrityError:
        raise HTTPException(
            status_code=400, detail="Failed to create submission"
        ) from None


@router.get("/me", response_model=list[SubmissionBase])
async def get_student_submissions():
    session = (Depends(get_db),)
    current_user = (Depends(get_current_user),)

    return await get_submissions_by_student_id(session, current_user.id)


@router.get("/{submission_id}", response_model=SubmissionBase)
async def get_submission(
    submission_id: int,
):
    session = (Depends(get_db),)
    current_user = (Depends(get_current_user),)

    submission = await get_submission_by_id(session, submission_id)
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    elif (
        submission.student_id != current_user.id
        and current_user.role != UserRole.instructor
    ):
        raise HTTPException(status_code=403, detail="Forbidden")

    return submission


@router.get("/assignment/{assignment_id}", response_model=list[SubmissionBase])
async def get_assignment_submissions(
    assignment_id: int,
):
    session = Depends(get_db)
    Depends(require_role(UserRole.instructor))
    return await get_submissions_by_assignment_id(session, assignment_id)


@router.put("/{submission_id}/state", response_model=SubmissionBase)
async def change_submission_state(
    submission_id: int,
    new_state: SubmissionState,
):
    session = Depends(get_db)
    Depends(require_role(UserRole.instructor))
    submission = await update_submission_state(session, submission_id, new_state)
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    return submission


@router.delete("/{submission_id}")
async def remove_submission(
    submission_id: int,
):
    session = Depends(get_db)
    current_user = Depends(require_role(UserRole.student))

    submisson = await get_submission_by_id(session, submission_id)
    if not submisson:
        raise HTTPException(status_code=404, detail="Submission not found")
    elif submisson.student_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden")
    success = await delete_submission(session, submission_id)
    if not success:
        raise HTTPException(status_code=404, detail="Submission not found")
    return {"message": "Submission deleted successfully"}
