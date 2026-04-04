import logging

import bcrypt
from db.crud.users import (
    create_user,
    delete_user,
    get_user_by_username,
    list_users_by_role,
    update_user_email,
)
from db.models import UserRole
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from schemas import RegisterRequest, UserBase
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import create_access_token, get_current_user, require_role
from ..dependencies import get_db

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/register", response_model=UserBase)
async def register_user(
    body: RegisterRequest,
    session: AsyncSession = Depends(get_db),
):
    logger.info("Registering new user: %s (role=%s)", body.username, body.role)
    try:
        password_hash = bcrypt.hashpw(body.password.encode(), bcrypt.gensalt()).decode()
        new_user = await create_user(
            session=session,
            username=body.username,
            password_hash=password_hash,
            email=body.email,
            role=body.role,
        )
        logger.info(
            "User registered successfully: %s (id=%d)", new_user.username, new_user.id
        )
        return new_user
    except IntegrityError:
        logger.warning(
            "Registration failed - duplicate username or email: %s", body.username
        )
        raise HTTPException(
            status_code=409, detail="Username or email already exists"
        ) from None


@router.post("/login")
async def login_user(
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: AsyncSession = Depends(get_db),
):
    logger.info("Login attempt for user: %s", form_data.username)
    user = await get_user_by_username(session, form_data.username)
    if not user or not bcrypt.checkpw(
        form_data.password.encode(), user.password_hash.encode()
    ):
        logger.warning("Failed login attempt for user: %s", form_data.username)
        raise HTTPException(status_code=401, detail="Invalid username or password")
    token = create_access_token({"sub": str(user.id), "role": user.role.value})
    logger.info("User logged in successfully: %s (id=%d)", user.username, user.id)
    return {"access_token": token, "token_type": "bearer"}


@router.get("/me", response_model=UserBase)
async def get_user(
    current_user=Depends(get_current_user),
):
    logger.debug("Fetching current user profile: %s", current_user.username)
    return current_user


@router.get("/students", response_model=list[UserBase])
async def list_students(
    session: AsyncSession = Depends(get_db),
    _current_user=Depends(require_role(UserRole.instructor)),
):
    logger.debug("Listing all student accounts (instructor)")
    return await list_users_by_role(session, UserRole.student)


@router.patch("/me/email")
async def update_email(
    new_email: str,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    logger.info("User %s updating email to %s", current_user.username, new_email)
    result = await update_user_email(
        session=session, username=current_user.username, new_email=new_email
    )
    if result:
        logger.info("Email updated successfully for user: %s", current_user.username)
        return {"message": "Email updated successfully"}
    else:
        logger.error(
            "Failed to update email - user not found: %s", current_user.username
        )
        raise HTTPException(status_code=404, detail="User not found")


@router.delete("/me")
async def delete_account(
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    logger.info("User %s requesting account deletion", current_user.username)
    try:
        result = await delete_user(session=session, username=current_user.username)
    except IntegrityError:
        logger.warning(
            "Cannot delete user %s: has dependent records", current_user.username
        )
        raise HTTPException(
            status_code=409,
            detail="Cannot delete account: you still have courses or submissions. Remove them first.",
        ) from None
    if result:
        logger.info("Account deleted successfully: %s", current_user.username)
        return {"message": "User deleted successfully"}
    else:
        logger.error(
            "Failed to delete account - user not found: %s", current_user.username
        )
        raise HTTPException(status_code=404, detail="User not found")
