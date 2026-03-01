from pydantic import BaseModel

from db.models import UserRole


class UserBase(BaseModel):
    id: int
    username: str
    email: str
    role: UserRole

    model_config = {"from_attributes": True}


class RegisterRequest(BaseModel):
    username: str
    password: str
    email: str
    role: UserRole


class LoginRequest(BaseModel):
    username: str
    password: str
