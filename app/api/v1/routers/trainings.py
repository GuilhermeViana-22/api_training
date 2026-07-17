from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import require_role
from app.core.pagination import PaginatedResponse
from app.database.session import get_db
from app.schemas.training import (
    TrainingCompleteCreate,
    TrainingCreate,
    TrainingDayCreate,
    TrainingDayResponse,
    TrainingDayUpdate,
    TrainingDetailResponse,
    TrainingExerciseCreate,
    TrainingExerciseResponse,
    TrainingExerciseUpdate,
    TrainingListItem,
    TrainingUpdate,
)
from app.services import training_service

router = APIRouter()


@router.get("", response_model=PaginatedResponse[TrainingListItem])
def list_trainings(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    student_id: str | None = Query(None, description="Filtrar treinos de um aluno específico"),
    status: str | None = Query(None, description="draft | active | completed | cancelled"),
    user=Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    return training_service.list_trainings(db, user.id, page, limit, student_id, status)


@router.post("/complete", response_model=TrainingDetailResponse, status_code=201)
def create_training_complete(
    data: TrainingCompleteCreate,
    user=Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    """
    Cadastra treino completo para um aluno em uma única requisição.

    Envia student_id, datas, dias da semana (0=Seg ... 6=Dom) e exercícios de cada dia.
    Cada aluno possui treino independente vinculado pelo student_id.
    """
    return training_service.create_training_complete(db, user.id, data)


@router.post("", response_model=TrainingDetailResponse, status_code=201)
def create_training(data: TrainingCreate, user=Depends(require_role("admin")), db: Session = Depends(get_db)):
    """Cria treino vazio (draft) — use POST /complete para cadastro com dias e exercícios."""
    return training_service.create_training(db, user.id, data)


@router.get("/{training_id}", response_model=TrainingDetailResponse)
def get_training(training_id: str, user=Depends(require_role("admin")), db: Session = Depends(get_db)):
    return training_service.get_training(db, user.id, training_id)


@router.put("/{training_id}", response_model=TrainingDetailResponse)
def update_training(
    training_id: str, data: TrainingUpdate, user=Depends(require_role("admin")), db: Session = Depends(get_db)
):
    return training_service.update_training(db, user.id, training_id, data)


@router.post("/{training_id}/activate", response_model=TrainingDetailResponse)
def activate_training(training_id: str, user=Depends(require_role("admin")), db: Session = Depends(get_db)):
    """Ativa treino do aluno (completa treino ativo anterior automaticamente)."""
    return training_service.activate_training(db, user.id, training_id)


@router.delete("/{training_id}", status_code=204)
def delete_training(training_id: str, user=Depends(require_role("admin")), db: Session = Depends(get_db)):
    training_service.delete_training(db, user.id, training_id)


@router.post("/{training_id}/days", response_model=TrainingDayResponse, status_code=201)
def add_training_day(
    training_id: str, data: TrainingDayCreate, user=Depends(require_role("admin")), db: Session = Depends(get_db)
):
    return training_service.add_day(db, user.id, training_id, data)


@router.put("/{training_id}/days/{day_id}", response_model=TrainingDayResponse)
def update_training_day(
    training_id: str,
    day_id: str,
    data: TrainingDayUpdate,
    user=Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    return training_service.update_day(db, user.id, training_id, day_id, data)


@router.delete("/{training_id}/days/{day_id}", status_code=204)
def delete_training_day(
    training_id: str, day_id: str, user=Depends(require_role("admin")), db: Session = Depends(get_db)
):
    training_service.delete_day(db, user.id, training_id, day_id)


@router.post("/{training_id}/days/{day_id}/exercises", response_model=TrainingExerciseResponse, status_code=201)
def add_training_exercise(
    training_id: str,
    day_id: str,
    data: TrainingExerciseCreate,
    user=Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    return training_service.add_exercise_to_day(db, user.id, training_id, day_id, data)


@router.put(
    "/{training_id}/days/{day_id}/exercises/{entry_id}",
    response_model=TrainingExerciseResponse,
)
def update_training_exercise(
    training_id: str,
    day_id: str,
    entry_id: str,
    data: TrainingExerciseUpdate,
    user=Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    return training_service.update_exercise_entry(db, user.id, training_id, day_id, entry_id, data)


@router.delete("/{training_id}/days/{day_id}/exercises/{entry_id}", status_code=204)
def delete_training_exercise(
    training_id: str,
    day_id: str,
    entry_id: str,
    user=Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    training_service.delete_exercise_entry(db, user.id, training_id, day_id, entry_id)
