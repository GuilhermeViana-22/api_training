from datetime import date

from sqlalchemy.orm import Session

from app.auth.password import hash_password, verify_password
from app.core.exceptions import BusinessError, NotFoundError
from app.repositories.student_repository import StudentRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth import MeResponse
from app.schemas.profile import EmailChangeRequest, PasswordChangeRequest, ProfileUpdateRequest
from app.services import auth_service

user_repo = UserRepository()
student_repo = StudentRepository()


def update_profile(db: Session, user_id: str, data: ProfileUpdateRequest) -> MeResponse:
    user = user_repo.get_with_profile(db, user_id)
    if user is None or user.role != "student" or user.student_profile is None:
        raise NotFoundError()

    payload = data.model_dump(exclude_unset=True)
    if "birth_date" in payload and payload["birth_date"]:
        payload["birth_date"] = date.fromisoformat(payload["birth_date"])

    student_repo.update_profile(db, user.student_profile, **payload)
    db.commit()
    return auth_service.get_me(db, user)


def change_password(db: Session, user_id: str, data: PasswordChangeRequest) -> dict:
    user = user_repo.get_by_id(db, user_id)
    if user is None:
        raise NotFoundError()

    if not verify_password(data.current_password, user.password_hash):
        raise BusinessError("INVALID_PASSWORD", "Senha atual incorreta.", 422)

    user_repo.update_password(db, user_id, hash_password(data.new_password))
    db.commit()
    return {"message": "Senha alterada com sucesso."}


def change_email(db: Session, user_id: str, data: EmailChangeRequest) -> MeResponse:
    user = user_repo.get_with_profile(db, user_id)
    if user is None:
        raise NotFoundError()

    if not verify_password(data.password, user.password_hash):
        raise BusinessError("INVALID_PASSWORD", "Senha incorreta.", 422)

    new_email = data.new_email.lower()
    if new_email == user.email.lower():
        raise BusinessError("EMAIL_UNCHANGED", "O novo email é igual ao atual.", 422)

    if user_repo.email_exists(db, new_email):
        raise BusinessError("EMAIL_EXISTS", "Este email já está em uso.", 409)

    user_repo.update_email(db, user_id, new_email)
    db.commit()
    user = user_repo.get_with_profile(db, user_id)
    return auth_service.get_me(db, user)
