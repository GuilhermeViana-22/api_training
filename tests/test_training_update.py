"""
PUT /trainings/{id}/complete: substitui integralmente um treino (metadados +
dias + exercicios) em uma unica operacao — o mesmo shape de payload usado
pelo wizard na criacao (POST /trainings/complete), reaproveitado em modo
edicao. Bloqueado pela mesma regra do delete: treino active/completed com
interacao real do aluno (has_student_interaction) nao pode ser reescrito,
pra nao apagar TrainingExercise (e ExerciseCompletion em cascata) que o
aluno ja usou.
"""

from datetime import date, timedelta

import pytest

from app.models.attendance_record import AttendanceRecord
from app.utils.uuid import generate_uuid

API = "/api/v1"


@pytest.fixture
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


def _payload(student_id, exercise_id, title="Treino Pytest Update", day_of_week=0, sets=3, reps=10):
    today = date.today()
    return {
        "student_id": student_id,
        "title": title,
        "start_date": today.isoformat(),
        "end_date": (today + timedelta(days=60)).isoformat(),
        "days": [
            {
                "day_of_week": day_of_week,
                "label": "Treino A",
                "exercises": [{"exercise_id": exercise_id, "sets": sets, "reps": reps}],
            }
        ],
    }


class TestUpdateTrainingComplete:
    def test_updating_metadata_and_days_replaces_them(self, client, admin_headers, exercise, make_student):
        student, _ = make_student()
        created = client.post(
            f"{API}/trainings/complete", json=_payload(student.id, exercise.id), headers=admin_headers
        ).json()

        update_payload = _payload(student.id, exercise.id, title="Treino Editado", day_of_week=2, sets=5, reps=8)
        resp = client.put(f"{API}/trainings/{created['id']}/complete", json=update_payload, headers=admin_headers)
        assert resp.status_code == 200, resp.text
        body = resp.json()

        assert body["title"] == "Treino Editado"
        assert len(body["days"]) == 1
        assert body["days"][0]["day_of_week"] == 2
        assert body["days"][0]["exercises"][0]["sets"] == 5
        assert body["days"][0]["exercises"][0]["reps"] == 8

    def test_adding_a_second_day_and_removing_the_first_is_reflected(self, client, admin_headers, exercise, make_student):
        student, _ = make_student()
        created = client.post(
            f"{API}/trainings/complete", json=_payload(student.id, exercise.id, day_of_week=0), headers=admin_headers
        ).json()

        payload = _payload(student.id, exercise.id, day_of_week=0)
        payload["days"].append(
            {"day_of_week": 3, "label": "Treino B", "exercises": [{"exercise_id": exercise.id, "sets": 4, "reps": 12}]}
        )
        resp = client.put(f"{API}/trainings/{created['id']}/complete", json=payload, headers=admin_headers)
        assert resp.status_code == 200, resp.text
        assert {d["day_of_week"] for d in resp.json()["days"]} == {0, 3}

        # agora remove o dia 0, deixa so o 3 -> dia removido some de verdade
        payload2 = {**payload, "days": [payload["days"][1]]}
        resp2 = client.put(f"{API}/trainings/{created['id']}/complete", json=payload2, headers=admin_headers)
        assert resp2.status_code == 200, resp2.text
        assert {d["day_of_week"] for d in resp2.json()["days"]} == {3}

    def test_activating_on_update_completes_other_active_trainings_for_the_student(
        self, client, admin_headers, exercise, make_student
    ):
        student, _ = make_student()
        other_active = client.post(
            f"{API}/trainings/complete",
            json={**_payload(student.id, exercise.id, day_of_week=1), "activate": True},
            headers=admin_headers,
        ).json()
        draft = client.post(
            f"{API}/trainings/complete", json=_payload(student.id, exercise.id, day_of_week=4), headers=admin_headers
        ).json()

        payload = {**_payload(student.id, exercise.id, day_of_week=4), "activate": True}
        resp = client.put(f"{API}/trainings/{draft['id']}/complete", json=payload, headers=admin_headers)
        assert resp.status_code == 200, resp.text
        assert resp.json()["status"] == "active"

        other_detail = client.get(f"{API}/trainings/{other_active['id']}", headers=admin_headers).json()
        assert other_detail["status"] == "completed"

    def test_editing_a_training_the_student_already_interacted_with_is_blocked(
        self, client, db, admin, admin_headers, exercise, make_student
    ):
        student, _ = make_student()
        created = client.post(
            f"{API}/trainings/complete",
            json={**_payload(student.id, exercise.id), "activate": True},
            headers=admin_headers,
        ).json()
        db.add(
            AttendanceRecord(
                id=generate_uuid(), student_id=student.id, training_id=created["id"], check_in_date=date.today()
            )
        )
        db.commit()

        resp = client.put(
            f"{API}/trainings/{created['id']}/complete", json=_payload(student.id, exercise.id), headers=admin_headers
        )
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "TRAINING_LOCKED"

    def test_editing_an_active_training_with_no_interaction_is_allowed(
        self, client, admin_headers, exercise, make_student
    ):
        student, _ = make_student()
        created = client.post(
            f"{API}/trainings/complete",
            json={**_payload(student.id, exercise.id), "activate": True},
            headers=admin_headers,
        ).json()

        update_payload = _payload(student.id, exercise.id, title="Treino Ativo Editado")
        resp = client.put(f"{API}/trainings/{created['id']}/complete", json=update_payload, headers=admin_headers)
        assert resp.status_code == 200, resp.text
        assert resp.json()["title"] == "Treino Ativo Editado"
        assert resp.json()["status"] == "active"

    def test_updating_someone_elses_training_is_not_found(self, client, admin_headers, exercise, make_student):
        student, _ = make_student()
        resp = client.put(
            f"{API}/trainings/{generate_uuid()}/complete", json=_payload(student.id, exercise.id), headers=admin_headers
        )
        assert resp.status_code == 404
