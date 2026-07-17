from datetime import UTC, datetime, timedelta
from hashlib import sha256
from typing import Any

from jose import JWTError, jwt

from app.core.config import settings
from app.utils.uuid import generate_uuid


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def create_access_token(subject: str, role: str, admin_id: str) -> tuple[str, int]:
    expires_minutes = settings.access_token_expire_minutes
    expire = _utcnow() + timedelta(minutes=expires_minutes)
    payload = {
        "sub": subject,
        "role": role,
        "admin_id": admin_id,
        "type": "access",
        "exp": expire,
        "iat": _utcnow(),
    }
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return token, expires_minutes * 60


def create_refresh_token(subject: str) -> tuple[str, str, datetime]:
    token_id = generate_uuid()
    expire = _utcnow() + timedelta(days=settings.refresh_token_expire_days)
    payload = {
        "sub": subject,
        "type": "refresh",
        "jti": token_id,
        "exp": expire,
        "iat": _utcnow(),
    }
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return token, token_id, expire


def decode_token(token: str) -> dict[str, Any] | None:
    try:
        return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError:
        return None


def hash_token(token: str) -> str:
    return sha256(token.encode()).hexdigest()
