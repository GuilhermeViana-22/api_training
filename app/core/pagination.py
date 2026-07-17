from math import ceil
from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=20, ge=1, le=100)


class PaginationMeta(BaseModel):
    page: int
    limit: int
    total: int
    total_pages: int


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    pagination: PaginationMeta


def build_pagination(page: int, limit: int, total: int) -> PaginationMeta:
    total_pages = ceil(total / limit) if total else 0
    return PaginationMeta(page=page, limit=limit, total=total, total_pages=total_pages)
