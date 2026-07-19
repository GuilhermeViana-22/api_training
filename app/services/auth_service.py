from sqlalchemy.orm import Session

from app.auth.jwt_handler import create_access_token, create_refresh_token, decode_token, hash_token
from app.auth.password import hash_password, verify_password
from app.core.config import settings
from app.core.exceptions import BusinessError, UnauthorizedError
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth import (
    AdminProfileResponse,
    LoginRequest,
    MeResponse,
    RefreshRequest,
    RefreshResponse,
    StudentProfileResponse,
    TokenResponse,
)
from app.utils.media import build_upload_url

user_repo = UserRepository()
refresh_repo = RefreshTokenRepository()


def _resolve_admin_id(db: Session, user) -> str:
    if user.role == "admin":
        return user.id
    user = user_repo.get_with_profile(db, user.id)
    if user and user.student_profile:
        return user.student_profile.admin_id
    return user.id if user else ""


def login(db: Session, data: LoginRequest) -> TokenResponse:
    user = user_repo.get_by_email(db, data.email)
    if user is None or not verify_password(data.password, user.password_hash):
        raise UnauthorizedError("INVALID_CREDENTIALS", "Email ou senha inválidos.")
    if not user.is_active or user.deleted_at is not None:
        raise UnauthorizedError("USER_INACTIVE", "Usuário inativo. Contate o administrador.")

    admin_id = _resolve_admin_id(db, user)
    access_token, expires_in = create_access_token(user.id, user.role, admin_id)
    refresh_token, token_id, expires_at = create_refresh_token(user.id)
    refresh_repo.create(db, user.id, hash_token(refresh_token), expires_at, token_id)
    db.commit()

    return TokenResponse(access_token=access_token, refresh_token=refresh_token, expires_in=expires_in)


def refresh(db: Session, data: RefreshRequest) -> RefreshResponse:
    payload = decode_token(data.refresh_token)
    if payload is None or payload.get("type") != "refresh":
        raise UnauthorizedError("TOKEN_INVALID", "Refresh token inválido.")

    token = refresh_repo.get_valid(db, payload["jti"], hash_token(data.refresh_token))
    if token is None:
        raise UnauthorizedError("TOKEN_REVOKED", "Refresh token revogado ou expirado.")

    user = user_repo.get_by_id(db, payload["sub"])
    if user is None or not user.is_active or user.deleted_at is not None:
        raise UnauthorizedError("USER_INACTIVE", "Usuário inativo.")

    admin_id = _resolve_admin_id(db, user)
    access_token, expires_in = create_access_token(user.id, user.role, admin_id)
    return RefreshResponse(access_token=access_token, expires_in=expires_in)


def logout(db: Session, data: RefreshRequest) -> None:
    payload = decode_token(data.refresh_token)
    if payload is None or payload.get("type") != "refresh":
        raise UnauthorizedError("TOKEN_INVALID", "Refresh token inválido.")

    token = refresh_repo.get_valid(db, payload["jti"], hash_token(data.refresh_token))
    if token is None:
        raise UnauthorizedError("TOKEN_REVOKED", "Refresh token revogado ou expirado.")

    refresh_repo.revoke(db, token)
    db.commit()


def get_me(db: Session, user) -> MeResponse:
    user = user_repo.get_with_profile(db, user.id)
    if user.role == "admin":
        profile = AdminProfileResponse(
            full_name=user.admin_profile.full_name,
            cref=user.admin_profile.cref,
            phone=user.admin_profile.phone,
            bio=user.admin_profile.bio,
            avatar_url=build_upload_url(user.avatar_path),
        )
    else:
        sp = user.student_profile
        profile = StudentProfileResponse(
            full_name=sp.full_name,
            phone=sp.phone,
            birth_date=sp.birth_date.isoformat() if sp.birth_date else None,
            height_cm=float(sp.height_cm) if sp.height_cm is not None else None,
            weight_kg=float(sp.weight_kg) if sp.weight_kg is not None else None,
            goal=sp.goal,
            avatar_url=build_upload_url(user.avatar_path),
        )

    return MeResponse(
        id=user.id,
        email=user.email,
        role=user.role,
        is_active=user.is_active,
        profile=profile,
        created_at=user.created_at,
    )


def seed_admin(db: Session) -> None:
    if user_repo.admin_exists(db):
        return

    user = user_repo.create_user(db, settings.admin_email, hash_password(settings.admin_password), "admin")
    user_repo.create_admin_profile(db, user.id, full_name="Administrador")
    db.commit()
