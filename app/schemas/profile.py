from pydantic import BaseModel, EmailStr, Field


class ProfileUpdateRequest(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=150)
    phone: str | None = None
    birth_date: str | None = None
    height_cm: float | None = Field(default=None, gt=0, le=300)
    weight_kg: float | None = Field(default=None, gt=0, le=500)
    goal: str | None = None


class PasswordChangeRequest(BaseModel):
    current_password: str = Field(min_length=1)
    new_password: str = Field(min_length=8)


class EmailChangeRequest(BaseModel):
    new_email: EmailStr
    password: str = Field(min_length=1, description="Senha atual para confirmar")
