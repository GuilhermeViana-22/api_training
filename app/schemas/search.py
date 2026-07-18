from typing import Literal

from pydantic import BaseModel


class SearchResultItem(BaseModel):
    id: str
    type: Literal["student", "exercise", "training"]
    title: str
    subtitle: str | None = None
    route_name: str
    route_params: dict[str, str]


class SearchResponse(BaseModel):
    query: str
    items: list[SearchResultItem]
