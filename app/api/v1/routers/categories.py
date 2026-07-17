from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database.session import get_db
from app.schemas.workout import TrainingCategoryResponse
from app.services import category_service

router = APIRouter()


@router.get("", response_model=list[TrainingCategoryResponse])
def list_training_categories(_user=Depends(get_current_user), db: Session = Depends(get_db)):
    return category_service.list_categories(db)
