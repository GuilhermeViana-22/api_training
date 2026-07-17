from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.models.admin_profile import AdminProfile
from app.models.user import User
from app.utils.uuid import generate_uuid


class UserRepository:
    def get_by_id(self, db: Session, user_id: str) -> User | None:
        return db.get(User, user_id)

    def get_by_email(self, db: Session, email: str) -> User | None:
        return db.query(User).filter(func.lower(User.email) == email.lower()).first()

    def email_exists(self, db: Session, email: str) -> bool:
        return self.get_by_email(db, email) is not None

    def create_user(self, db: Session, email: str, password_hash: str, role: str) -> User:
        user = User(id=generate_uuid(), email=email.lower(), password_hash=password_hash, role=role)
        db.add(user)
        db.flush()
        return user

    def create_admin_profile(self, db: Session, user_id: str, full_name: str, **kwargs) -> AdminProfile:
        profile = AdminProfile(user_id=user_id, full_name=full_name, **kwargs)
        db.add(profile)
        db.flush()
        return profile

    def get_with_profile(self, db: Session, user_id: str) -> User | None:
        return (
            db.query(User)
            .options(joinedload(User.admin_profile), joinedload(User.student_profile))
            .filter(User.id == user_id)
            .first()
        )

    def update_email(self, db: Session, user_id: str, email: str) -> None:
        user = db.get(User, user_id)
        if user:
            user.email = email.lower()
            db.flush()

    def update_password(self, db: Session, user_id: str, password_hash: str) -> None:
        user = db.get(User, user_id)
        if user:
            user.password_hash = password_hash
            db.flush()

    def admin_exists(self, db: Session) -> bool:
        return db.query(User.id).filter(User.role == "admin").first() is not None
