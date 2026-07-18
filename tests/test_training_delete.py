"""
Exclusao de treino: o que trava a exclusao nao e o status (active/completed)
em si, e sim o aluno ja ter interagido com o plano (check-in ou treino
registrado). Um treino active/completed sem nenhuma interacao ainda pode
ser excluido normalmente — so vira "travado" quando ha historico real do
aluno associado a ele.
"""

from datetime import date, timedelta

import pytest

from app.models.attendance_record import AttendanceRecord
from app.models.training import Training
from app.models.training_day import TrainingDay
from app.models.training_exercise import TrainingExercise
from app.models.workout_session import WorkoutSession
from app.utils.uuid import generate_uuid

API = "/api/v1"


@pytest.fixture
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


def _create_training(db, admin, student, exercise, status="draft"):
    training = Training(
        id=generate_uuid(),
        admin_id=admin.id,
        student_id=student.id,
        title="Treino Pytest Delete",
        start_date=date.today(),
        end_date=date.today() + timedelta(days=30),
        status=status,
    )
    db.add(training)
    db.flush()
    day = TrainingDay(id=generate_uuid(), training_id=training.id, day_of_week=0, label="Treino A")
    db.add(day)
    db.flush()
    entry = TrainingExercise(id=generate_uuid(), training_day_id=day.id, exercise_id=exercise.id, sets=3, reps=10)
    db.add(entry)
    db.commit()
    db.refresh(training)
    return training, day


class TestDeleteTraining:
    def test_deleting_a_draft_training_removes_it(self, client, db, admin, admin_headers, exercise, make_student):
        student, _ = make_student()
        training, _day = _create_training(db, admin, student, exercise, status="draft")

        resp = client.delete(f"{API}/trainings/{training.id}", headers=admin_headers)
        assert resp.status_code == 204

        assert client.get(f"{API}/trainings/{training.id}", headers=admin_headers).status_code == 404

    def test_deleting_an_active_training_with_no_student_interaction_is_allowed(
        self, db, admin, admin_headers, client, exercise, make_student
    ):
        """Treino active recem-criado, aluno nunca fez check-in nem registrou treino -> pode excluir."""
        student, _ = make_student()
        training, _day = _create_training(db, admin, student, exercise, status="active")

        resp = client.delete(f"{API}/trainings/{training.id}", headers=admin_headers)
        assert resp.status_code == 204

        assert client.get(f"{API}/trainings/{training.id}", headers=admin_headers).status_code == 404

    def test_deleting_an_active_training_with_checkin_is_blocked(
        self, db, admin, admin_headers, client, exercise, make_student
    ):
        student, _ = make_student()
        training, _day = _create_training(db, admin, student, exercise, status="active")
        db.add(
            AttendanceRecord(
                id=generate_uuid(), student_id=student.id, training_id=training.id, check_in_date=date.today()
            )
        )
        db.commit()

        resp = client.delete(f"{API}/trainings/{training.id}", headers=admin_headers)
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "TRAINING_LOCKED"
        assert client.get(f"{API}/trainings/{training.id}", headers=admin_headers).status_code == 200

    def test_deleting_a_completed_training_with_workout_session_is_blocked(
        self, db, admin, admin_headers, client, exercise, make_student
    ):
        student, _ = make_student()
        training, day = _create_training(db, admin, student, exercise, status="completed")
        db.add(
            WorkoutSession(
                id=generate_uuid(),
                student_id=student.id,
                training_id=training.id,
                training_day_id=day.id,
                session_date=date.today(),
                status="completed",
            )
        )
        db.commit()

        resp = client.delete(f"{API}/trainings/{training.id}", headers=admin_headers)
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "TRAINING_LOCKED"
        assert client.get(f"{API}/trainings/{training.id}", headers=admin_headers).status_code == 200

    def test_deleting_someone_elses_training_is_not_found(self, client, admin_headers):
        resp = client.delete(f"{API}/trainings/{generate_uuid()}", headers=admin_headers)
        assert resp.status_code == 404
