from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    email: EmailStr
    secret: str = Field(..., min_length=8)
    full_name: str | None = Field(default=None, max_length=120)


class UserRead(BaseModel):
    id: int
    email: EmailStr
    full_name: str | None = None
    is_active: bool

    model_config = {"from_attributes": True}


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
