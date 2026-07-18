from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, require_role
from app.database.session import get_db
from app.schemas.workout import TrainingCategoryCreate, TrainingCategoryResponse, TrainingCategoryUpdate
from app.services import category_service

router = APIRouter()


@router.get("", response_model=list[TrainingCategoryResponse])
def list_training_categories(
    all: bool = False,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if all and user.role == "admin":
        return category_service.list_all_categories(db)
    return category_service.list_categories(db)


@router.post("", response_model=TrainingCategoryResponse, status_code=201)
def create_training_category(
    data: TrainingCategoryCreate, _user=Depends(require_role("admin")), db: Session = Depends(get_db)
):
    return category_service.create_category(db, data)


@router.put("/{category_id}", response_model=TrainingCategoryResponse)
def update_training_category(
    category_id: str,
    data: TrainingCategoryUpdate,
    _user=Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    return category_service.update_category(db, category_id, data)


@router.delete("/{category_id}", status_code=204)
def delete_training_category(
    category_id: str, _user=Depends(require_role("admin")), db: Session = Depends(get_db)
):
    category_service.delete_category(db, category_id)
