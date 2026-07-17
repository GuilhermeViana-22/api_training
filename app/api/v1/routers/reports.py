from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import require_role
from app.database.session import get_db
from app.schemas.report import (
    AttendanceReportResponse,
    ReportsOverviewResponse,
    StudentMonitoringDetailResponse,
    StudentMonitoringListResponse,
    StudentReportResponse,
)
from app.services import report_service

router = APIRouter()


@router.get("/overview", response_model=ReportsOverviewResponse)
def reports_overview(user=Depends(require_role("admin")), db: Session = Depends(get_db)):
    """KPIs gerais do dashboard."""
    return report_service.overview(db, user.id)


@router.get("/students", response_model=StudentMonitoringListResponse)
def list_students_monitoring(user=Depends(require_role("admin")), db: Session = Depends(get_db)):
    """
    Guia de relatórios — lista todos os alunos com resumo de acompanhamento.

    Retorna id, nome, treino ativo, frequência, fotos e evolução de peso.
    """
    return report_service.list_students_monitoring(db, user.id)


@router.get("/students/{student_id}/monitoring", response_model=StudentMonitoringDetailResponse)
def student_monitoring_detail(
    student_id: str,
    user=Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    """
    Acompanhamento individual completo do aluno.

    Inclui: treino por dia da semana, timeline de check-ins,
    fotos de evolução, histórico de peso e treinos anteriores.
    """
    return report_service.student_monitoring_detail(db, user.id, student_id)


@router.get("/students/{student_id}", response_model=StudentReportResponse)
def student_report(student_id: str, user=Depends(require_role("admin")), db: Session = Depends(get_db)):
    """Relatório resumido do aluno."""
    return report_service.student_report(db, user.id, student_id)


@router.get("/attendance", response_model=AttendanceReportResponse)
def attendance_report(
    start_date: str | None = None,
    end_date: str | None = None,
    student_id: str | None = None,
    user=Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    """Relatório agregado de frequência por aluno."""
    start = date.fromisoformat(start_date) if start_date else None
    end = date.fromisoformat(end_date) if end_date else None
    return report_service.attendance_report(db, user.id, start, end, student_id)
