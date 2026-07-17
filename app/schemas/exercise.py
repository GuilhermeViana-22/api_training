from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ExerciseCreate(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    description: str | None = None
    muscle_group: str | None = None
    category_id: str | None = None
    default_sets: int | None = Field(default=None, ge=1)
    default_reps: int | None = Field(default=None, ge=1)
    default_rest_seconds: int | None = Field(default=None, ge=0)


class ExerciseUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=150)
    description: str | None = None
    muscle_group: str | None = None
    category_id: str | None = None
    default_sets: int | None = Field(default=None, ge=1)
    default_reps: int | None = Field(default=None, ge=1)
    default_rest_seconds: int | None = Field(default=None, ge=0)


class ExerciseImageResponse(BaseModel):
    id: str
    url: str
    media_type: str = "image"
    sort_order: int = 0


class ExerciseListItem(BaseModel):
    id: str
    name: str
    description: str | None = None
    muscle_group: str | None = None
    category: dict | None = None
    default_sets: int | None = None
    default_reps: int | None = None
    default_rest_seconds: int | None = None
    images_count: int = 0
    created_at: datetime


class ExerciseDetailResponse(BaseModel):
    id: str
    name: str
    description: str | None = None
    muscle_group: str | None = None
    category: dict | None = None
    default_sets: int | None = None
    default_reps: int | None = None
    default_rest_seconds: int | None = None
    images: list[ExerciseImageResponse] = Field(default_factory=list)
    created_at: datetime
