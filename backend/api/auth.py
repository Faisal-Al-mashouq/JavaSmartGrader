import os
from datetime import datetime, timedelta

from db.crud.users import get_user_by_id
from db.models import UserRole
from dotenv import load_dotenv
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from schemas import UserBase
from sqlalchemy.ext.asyncio import AsyncSession

from .dependencies import get_db

load_dotenv()
SECRET_KEY = os.getenv("JWT_SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

oauth_scheme = OAuth2PasswordBearer(tokenUrl="/users/login")


def create_access_token(data: dict) -> str:
    payload = data.copy()
    expire = datetime.now() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload.update({"exp": expire})
    encoded_jwt = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(
    token: str = Depends(oauth_scheme),
    session: AsyncSession = Depends(get_db),
) -> UserBase:
    try:
        decoded_token = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        sub = decoded_token.get("sub")
        if sub is None:
            raise HTTPException(status_code=401, detail="Invalid token") from None
        user = await get_user_by_id(session, int(sub))
        if user is None:
            raise HTTPException(status_code=401, detail="User not found") from None
        return UserBase(
            id=user.id, username=user.username, email=user.email, role=user.role
        )
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token") from None


def require_role(role: UserRole):
    async def role_checker(
        current_user: UserBase = Depends(get_current_user),
    ):
        if current_user.role != role:
            raise HTTPException(status_code=403, detail="Forbidden")
        return current_user

    return role_checker
