from datetime import datetime

from sqlalchemy.orm import Session

from app.models.refresh_token import RefreshToken
from app.utils.uuid import generate_uuid


class RefreshTokenRepository:
    def create(self, db: Session, user_id: str, token_hash: str, expires_at: datetime, token_id: str | None = None) -> RefreshToken:
        token = RefreshToken(
            id=token_id or generate_uuid(),
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        db.add(token)
        db.flush()
        return token

    def get_valid(self, db: Session, token_id: str, token_hash: str) -> RefreshToken | None:
        token = db.get(RefreshToken, token_id)
        if token is None or token.token_hash != token_hash or token.revoked_at is not None:
            return None
        if token.expires_at < datetime.utcnow():
            return None
        return token

    def revoke(self, db: Session, token: RefreshToken) -> None:
        token.revoked_at = datetime.utcnow()
