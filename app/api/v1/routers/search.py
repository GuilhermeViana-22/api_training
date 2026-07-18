from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import require_role
from app.database.session import get_db
from app.schemas.search import SearchResponse
from app.services import search_service

router = APIRouter()


@router.get("", response_model=SearchResponse)
def global_search(
    q: str = Query("", max_length=100),
    user=Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    """Busca global do personal trainer entre alunos, exercicios e treinos (Ctrl+K do sidebar)."""
    return search_service.search(db, user.id, q)
