from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.exceptions import AppError


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(_request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "details": exc.details,
                }
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
        details: dict[str, list[str]] = {}
        for error in exc.errors():
            field = ".".join(str(part) for part in error.get("loc", []) if part != "body")
            details.setdefault(field or "body", []).append(error.get("msg", "Valor inválido."))
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Erro de validação nos campos enviados.",
                    "details": details,
                }
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(_request: Request, exc: Exception) -> JSONResponse:
        from app.core.config import settings

        message = str(exc) if settings.app_debug else "Erro interno do servidor."
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": message,
                    "details": {},
                }
            },
        )
