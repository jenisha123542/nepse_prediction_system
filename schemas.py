from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime
from models import RoleEnum

# --- Auth Schemas ---

class UserRegister(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: Optional[RoleEnum] = RoleEnum.user

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserOut(BaseModel):
    id: int
    name: str
    email: str
    role: RoleEnum
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserOut

class TokenData(BaseModel):
    id: Optional[int] = None
    role: Optional[str] = None