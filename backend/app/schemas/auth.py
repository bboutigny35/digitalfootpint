from pydantic import BaseModel, ConfigDict, EmailStr, Field


class Credentials(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=256)


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    email: EmailStr
    is_admin: bool


class SessionRead(BaseModel):
    user: UserRead
    csrf_token: str


class CsrfRead(BaseModel):
    csrf_token: str


class UserCreate(Credentials):
    is_admin: bool = False
