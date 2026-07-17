from collections.abc import Callable

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.auth.jwt_handler import decode_token
from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.database.session import get_db
from app.models.user import User
from app.repositories.user_repository import UserRepository

security = HTTPBearer(auto_error=False)
user_repository = UserRepository()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None or not credentials.credentials:
        raise UnauthorizedError("NOT_AUTHENTICATED", "Token de autenticação ausente.")

    payload = decode_token(credentials.credentials)
    if payload is None or payload.get("type") != "access":
        raise UnauthorizedError("TOKEN_INVALID", "Token inválido.")

    user = user_repository.get_by_id(db, payload["sub"])
    if user is None or not user.is_active or user.deleted_at is not None:
        raise UnauthorizedError("USER_INACTIVE", "Usuário inativo. Contate o administrador.")

    return user


def require_role(*roles: str) -> Callable:
    async def role_checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise ForbiddenError()
        return user

    return role_checker
