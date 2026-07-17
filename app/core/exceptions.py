from typing import Any


class AppError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 400,
        details: dict[str, Any] | None = None,
    ):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)


class BusinessError(AppError):
    pass


class NotFoundError(AppError):
    def __init__(self, message: str = "Recurso não encontrado.", details: dict[str, Any] | None = None):
        super().__init__("NOT_FOUND", message, 404, details)


class ForbiddenError(AppError):
    def __init__(self, message: str = "Você não tem permissão para este recurso."):
        super().__init__("FORBIDDEN", message, 403)


class UnauthorizedError(AppError):
    def __init__(self, code: str, message: str):
        super().__init__(code, message, 401)
