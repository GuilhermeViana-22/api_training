"""
Testa o agendamento de treinos de longa duracao (1 a 4+ meses): o admin
monta um treino com dias fixos da semana (Treino A/B/C/Full Body) e o
aluno precisa ver exatamente esses dias no dashboard (`GET /me/training`)
e no detalhe do dia (`GET /me/training/days/{dow}`), respeitando o
periodo `start_date`/`end_date` calculado a partir de hoje.

As datas de teste sao sempre ancoradas em `date.today()` (sem mock de
tempo) e as trainings sao montadas direto via ORM, batendo depois contra
a resposta da API.
"""

from datetime import date, timedelta

import pytest

from app.models.training import Training
from app.models.training_day import TrainingDay
from app.models.training_exercise import TrainingExercise
from app.utils.uuid import generate_uuid

DAY_NAMES = {
    0: "Segunda-feira",
    1: "Terça-feira",
    2: "Quarta-feira",
    3: "Quinta-feira",
    4: "Sexta-feira",
    5: "Sábado",
    6: "Domingo",
}

# 0=Segunda ... 4=Sexta, igual ao cenario descrito: "3 meses de segunda a sexta"
MON_FRI_SPLIT = {0: "Treino A", 1: "Treino B", 2: "Treino C", 3: "Full Body", 4: "Treino A"}


def create_training(db, admin, student, exercise, start_date, end_date, days_spec, status="active"):
    training = Training(
        id=generate_uuid(),
        admin_id=admin.id,
        student_id=student.id,
        title="Treino Pytest",
        start_date=start_date,
        end_date=end_date,
        status=status,
    )
    db.add(training)
    db.flush()

    for day_of_week, label in days_spec.items():
        day = TrainingDay(id=generate_uuid(), training_id=training.id, day_of_week=day_of_week, label=label)
        db.add(day)
        db.flush()
        db.add(
            TrainingExercise(
                id=generate_uuid(), training_day_id=day.id, exercise_id=exercise.id, sets=3, reps=10
            )
        )

    db.commit()
    db.refresh(training)
    return training


def count_weekday_occurrences(start: date, end: date, weekday: int) -> int:
    """Quantas vezes `weekday` (0=Segunda) cai entre start e end (inclusive)."""
    assert start <= end
    offset = (weekday - start.weekday()) % 7
    first_hit = start + timedelta(days=offset)
    if first_hit > end:
        return 0
    return (end - first_hit).days // 7 + 1


class TestDashboardAcrossDurations:
    """1, 2, 3 e 4 meses -> mesma estrutura semanal, datas certas, sem regressao."""

    @pytest.mark.parametrize("months", [1, 2, 3, 4])
    def test_dashboard_and_day_view_match_orm(self, client, db, admin, exercise, make_student, months):
        student, token = make_student()
        today = date.today()
        end = today + timedelta(days=30 * months)
        training = create_training(db, admin, student, exercise, today, end, MON_FRI_SPLIT)
        headers = {"Authorization": f"Bearer {token}"}

        resp = client.get("/api/v1/me/training", headers=headers)
        assert resp.status_code == 200, resp.text
        body = resp.json()

        assert body["start_date"] == today.isoformat()
        assert body["end_date"] == end.isoformat()
        assert body["status"] == "active"

        # a duracao do treino nao muda a QUANTIDADE de dias configurados:
        # e um template semanal, nao uma linha por data do calendario.
        assert len(body["days"]) == len(MON_FRI_SPLIT)
        returned_labels = {d["day_of_week"]: d["label"] for d in body["days"]}
        assert returned_labels == MON_FRI_SPLIT

        # cruza a resposta da API contra o banco via ORM
        db.expire_all()
        orm_days = db.query(TrainingDay).filter(TrainingDay.training_id == training.id).all()
        assert len(orm_days) == len(MON_FRI_SPLIT)
        assert {d.day_of_week: d.label for d in orm_days} == MON_FRI_SPLIT

        # cada dia configurado responde certo no detalhe
        for day_of_week, label in MON_FRI_SPLIT.items():
            day_resp = client.get(f"/api/v1/me/training/days/{day_of_week}", headers=headers)
            assert day_resp.status_code == 200, day_resp.text
            day_body = day_resp.json()
            assert day_body["label"] == label
            assert day_body["day_name"] == DAY_NAMES[day_of_week]
            assert len(day_body["exercises"]) == 1
            assert day_body["training"]["start_date"] == today.isoformat()
            assert day_body["training"]["end_date"] == end.isoformat()

        # dia nao configurado (sabado) tem que dar 404, nao vazar dado de outro dia
        not_configured = client.get("/api/v1/me/training/days/5", headers=headers)
        assert not_configured.status_code == 404

        # calculo de datas: quantas ocorrencias reais de cada dia da semana existem no periodo
        full_weeks = (30 * months) // 7
        for day_of_week in MON_FRI_SPLIT:
            occurrences = count_weekday_occurrences(today, end, day_of_week)
            assert full_weeks <= occurrences <= full_weeks + 2


class TestPeriodBoundaries:
    """Fora do periodo (antes de comecar ou depois de terminar) o aluno nao pode ver o treino."""

    @pytest.mark.parametrize("months", [1, 3])
    def test_training_not_yet_started_is_hidden(self, client, db, admin, exercise, make_student, months):
        student, token = make_student()
        start = date.today() + timedelta(days=10)
        end = start + timedelta(days=30 * months)
        create_training(db, admin, student, exercise, start, end, MON_FRI_SPLIT)

        headers = {"Authorization": f"Bearer {token}"}
        assert client.get("/api/v1/me/training", headers=headers).status_code == 404
        assert client.get("/api/v1/me/training/days/0", headers=headers).status_code == 404

    @pytest.mark.parametrize("months", [1, 3])
    def test_training_already_ended_is_hidden(self, client, db, admin, exercise, make_student, months):
        student, token = make_student()
        end = date.today() - timedelta(days=1)
        start = end - timedelta(days=30 * months)
        create_training(db, admin, student, exercise, start, end, MON_FRI_SPLIT)

        headers = {"Authorization": f"Bearer {token}"}
        assert client.get("/api/v1/me/training", headers=headers).status_code == 404
        assert client.get("/api/v1/me/training/days/0", headers=headers).status_code == 404

    def test_training_covering_today_exactly_at_edges_is_visible(self, client, db, admin, exercise, make_student):
        """start_date == hoje e end_date == hoje sao inclusivos nas duas pontas."""
        student, token = make_student()
        today = date.today()
        create_training(db, admin, student, exercise, today, today, {today.weekday(): "Treino A"})

        headers = {"Authorization": f"Bearer {token}"}
        resp = client.get("/api/v1/me/training", headers=headers)
        assert resp.status_code == 200, resp.text
        assert resp.json()["start_date"] == resp.json()["end_date"] == today.isoformat()


def test_today_resolves_correctly_in_three_month_mon_fri_plan(client, db, admin, exercise, make_student):
    """Reproduz o cenario descrito: 3 meses, segunda a sexta -> hoje aparece certinho pro aluno."""
    student, token = make_student()
    today = date.today()
    if today.weekday() >= 5:
        pytest.skip("cenario segunda-sexta nao se aplica em fim de semana")

    create_training(db, admin, student, exercise, today, today + timedelta(days=90), MON_FRI_SPLIT)

    headers = {"Authorization": f"Bearer {token}"}
    resp = client.get(f"/api/v1/me/training/days/{today.weekday()}", headers=headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["label"] == MON_FRI_SPLIT[today.weekday()]
    assert body["day_name"] == DAY_NAMES[today.weekday()]
    assert body["day_completed"] is False
    assert body["checked_in_today"] is False
