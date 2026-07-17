import re
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class StudentCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str = Field(min_length=2, max_length=150)
    phone: str | None = None
    birth_date: date | None = None
    height_cm: float | None = Field(default=None, gt=0, le=300)
    weight_kg: float | None = Field(default=None, gt=0, le=500)
    goal: str | None = None
    notes: str | None = None

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        if not re.search(r"[A-Za-z]", value) or not re.search(r"\d", value):
            raise ValueError("Senha deve conter letra e número.")
        return value


class StudentUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=150)
    phone: str | None = None
    birth_date: date | None = None
    height_cm: float | None = Field(default=None, gt=0, le=300)
    weight_kg: float | None = Field(default=None, gt=0, le=500)
    goal: str | None = None
    notes: str | None = None


class StudentStatusUpdate(BaseModel):
    is_active: bool


class ActiveTrainingSummary(BaseModel):
    id: str
    title: str
    start_date: date
    end_date: date
    status: str


class StudentListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: EmailStr
    full_name: str
    phone: str | None = None
    is_active: bool
    active_training: ActiveTrainingSummary | None = None
    created_at: datetime


class StudentDetailResponse(BaseModel):
    id: str
    email: EmailStr
    full_name: str
    phone: str | None = None
    birth_date: date | None = None
    height_cm: float | None = None
    weight_kg: float | None = None
    goal: str | None = None
    notes: str | None = None
    is_active: bool
    trainings_count: int = 0
    last_check_in: date | None = None
    created_at: datetime
