from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database.session import get_db
from app.schemas.auth import LoginRequest, LogoutRequest, MeResponse, RefreshRequest, RefreshResponse, TokenResponse
from app.services import auth_service

router = APIRouter()


@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    return auth_service.login(db, data)


@router.post("/refresh", response_model=RefreshResponse)
def refresh_token(data: RefreshRequest, db: Session = Depends(get_db)):
    return auth_service.refresh(db, data)


@router.post("/logout", status_code=204)
def logout(data: LogoutRequest, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    auth_service.logout(db, data)


@router.get("/me", response_model=MeResponse)
def me(user=Depends(get_current_user), db: Session = Depends(get_db)):
    return auth_service.get_me(db, user)
