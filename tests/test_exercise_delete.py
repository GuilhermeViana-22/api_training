"""
Regressao: DELETE /exercises/{id} quebrava com 500 pra qualquer exercicio,
pois is_in_active_training() tentava juntar TrainingExercise -> Training
por uma coluna (training_id) que nao existe em TrainingExercise (o certo e
TrainingExercise.training_day_id -> TrainingDay.training_id).
"""

from datetime import date, timedelta

import pytest

from app.models.exercise import Exercise
from app.models.training import Training
from app.models.training_day import TrainingDay
from app.models.training_exercise import TrainingExercise
from app.utils.uuid import generate_uuid

API = "/api/v1"


@pytest.fixture
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture
def make_exercise(db, admin):
    created_ids = []

    def _make(name: str):
        item = Exercise(id=generate_uuid(), admin_id=admin.id, name=f"{name} {generate_uuid()[:8]}", muscle_group="peito")
        db.add(item)
        db.commit()
        db.refresh(item)
        created_ids.append(item.id)
        return item

    yield _make

    db.expire_all()
    db.query(Exercise).filter(Exercise.id.in_(created_ids)).delete(synchronize_session=False)
    db.commit()


class TestDeleteExercise:
    def test_deleting_an_unused_exercise_succeeds(self, client, admin_headers, make_exercise):
        exercise = make_exercise("Rosca Direta")

        resp = client.delete(f"{API}/exercises/{exercise.id}", headers=admin_headers)
        assert resp.status_code == 204

        assert client.get(f"{API}/exercises/{exercise.id}", headers=admin_headers).status_code == 404

    def test_deleting_an_exercise_used_in_an_active_training_is_blocked(
        self, client, db, admin, admin_headers, make_exercise, make_student
    ):
        exercise = make_exercise("Agachamento")
        student, _ = make_student()
        training = Training(
            id=generate_uuid(),
            admin_id=admin.id,
            student_id=student.id,
            title="Treino Pytest Exercise Delete",
            start_date=date.today(),
            end_date=date.today() + timedelta(days=30),
            status="active",
        )
        db.add(training)
        db.flush()
        day = TrainingDay(id=generate_uuid(), training_id=training.id, day_of_week=0, label="Treino A")
        db.add(day)
        db.flush()
        db.add(TrainingExercise(id=generate_uuid(), training_day_id=day.id, exercise_id=exercise.id, sets=3, reps=10))
        db.commit()

        resp = client.delete(f"{API}/exercises/{exercise.id}", headers=admin_headers)
        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "EXERCISE_IN_USE"

        assert client.get(f"{API}/exercises/{exercise.id}", headers=admin_headers).status_code == 200

    def test_deleting_an_exercise_used_only_in_a_draft_training_succeeds(
        self, client, db, admin, admin_headers, make_exercise, make_student
    ):
        exercise = make_exercise("Leg Press")
        student, _ = make_student()
        training = Training(
            id=generate_uuid(),
            admin_id=admin.id,
            student_id=student.id,
            title="Treino Pytest Draft",
            start_date=date.today(),
            end_date=date.today() + timedelta(days=30),
            status="draft",
        )
        db.add(training)
        db.flush()
        day = TrainingDay(id=generate_uuid(), training_id=training.id, day_of_week=0, label="Treino A")
        db.add(day)
        db.flush()
        db.add(TrainingExercise(id=generate_uuid(), training_day_id=day.id, exercise_id=exercise.id, sets=3, reps=10))
        db.commit()

        resp = client.delete(f"{API}/exercises/{exercise.id}", headers=admin_headers)
        assert resp.status_code == 204
