from sqlalchemy.orm import Session

from app.repositories.exercise_repository import ExerciseRepository
from app.repositories.student_repository import StudentRepository
from app.repositories.training_repository import TrainingRepository
from app.schemas.search import SearchResponse, SearchResultItem

student_repo = StudentRepository()
exercise_repo = ExerciseRepository()
training_repo = TrainingRepository()

MIN_QUERY_LENGTH = 2
RESULTS_PER_TYPE = 5


def search(db: Session, admin_id: str, query: str) -> SearchResponse:
    """
    Busca global do personal trainer (alunos, exercicios, treinos).

    Regras:
    - Escopo sempre restrito ao admin autenticado (nunca cruza dados de outro personal).
    - Query com menos de MIN_QUERY_LENGTH caracteres retorna lista vazia (evita varrer a base à toa).
    - Registros com soft-delete (deleted_at) nunca aparecem.
    - Até RESULTS_PER_TYPE resultados por tipo, ordenados alfabeticamente/mais recentes.
    - Cada item já traz o nome da rota do frontend (Vue Router) para navegação direta.
    """
    term = query.strip()
    if len(term) < MIN_QUERY_LENGTH:
        return SearchResponse(query=term, items=[])

    items: list[SearchResultItem] = []

    for profile in student_repo.search_by_name(db, admin_id, term, RESULTS_PER_TYPE):
        items.append(
            SearchResultItem(
                id=profile.user_id,
                type="student",
                title=profile.full_name,
                subtitle=profile.user.email,
                route_name="admin-student-detail",
                route_params={"id": profile.user_id},
            )
        )

    for exercise in exercise_repo.search_by_name(db, admin_id, term, RESULTS_PER_TYPE):
        items.append(
            SearchResultItem(
                id=exercise.id,
                type="exercise",
                title=exercise.name,
                subtitle=exercise.muscle_group,
                route_name="admin-exercise-detail",
                route_params={"id": exercise.id},
            )
        )

    for training in training_repo.search_by_title(db, admin_id, term, RESULTS_PER_TYPE):
        items.append(
            SearchResultItem(
                id=training.id,
                type="training",
                title=training.title,
                subtitle=training.student.full_name if training.student else None,
                route_name="admin-training-detail",
                route_params={"id": training.id},
            )
        )

    return SearchResponse(query=term, items=items)
