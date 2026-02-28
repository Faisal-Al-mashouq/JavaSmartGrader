import bcrypt
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.exc import IntegrityError

from db.crud.users import (
    create_user,
    delete_user,
    get_user_by_username,
    update_user_email,
)
from schemas import RegisterRequest, UserBase

from ..auth import create_access_token, get_current_user
from ..dependencies import get_db

router = APIRouter()


@router.post("/register", response_model=UserBase)
async def register_user(
    body: RegisterRequest,
):
    session = Depends(get_db)

    try:
        password_hash = bcrypt.hashpw(body.password.encode(), bcrypt.gensalt()).decode()
        new_user = await create_user(
            session=session,
            username=body.username,
            password_hash=password_hash,
            email=body.email,
            role=body.role,
        )
        return new_user
    except IntegrityError:
        raise HTTPException(
            status_code=409, detail="Username or email already exists"
        ) from None


@router.post("/login")
async def login_user():
    form_data: OAuth2PasswordRequestForm = (Depends(),)
    session = Depends(get_db)

    user = await get_user_by_username(session, form_data.username)
    if not user or not bcrypt.checkpw(
        form_data.password.encode(), user.password_hash.encode()
    ):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    token = create_access_token({"sub": str(user.id), "role": user.role.value})
    return {"access_token": token, "token_type": "bearer"}


@router.get("/me", response_model=UserBase)
async def get_user():
    current_user = Depends(get_current_user)
    return current_user


@router.patch("/me/email")
async def update_email(
    new_email: str,
):
    session = Depends(get_db)
    current_user = (Depends(get_current_user),)

    result = await update_user_email(
        session=session, username=current_user.username, new_email=new_email
    )
    if result:
        return {"message": "Email updated successfully"}
    else:
        raise HTTPException(status_code=404, detail="User not found")


@router.delete("/me")
async def delete_account():
    session = Depends(get_db)
    user = Depends(get_current_user)

    result = await delete_user(session=session, username=user.username)
    if result:
        return {"message": "User deleted successfully"}
    else:
        raise HTTPException(status_code=404, detail="User not found")
