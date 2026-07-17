from pydantic import BaseModel, ConfigDict, EmailStr, Field


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: dict = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    error: ErrorDetail


class MessageResponse(BaseModel):
    message: str
