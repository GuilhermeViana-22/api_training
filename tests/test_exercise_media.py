"""
Valida o modelo de midia por exercicio que sustenta o wizard de treino do
frontend: cada exercicio tem sua propria galeria de fotos/videos/gifs,
independente de outros exercicios, e essa galeria e reaproveitada
automaticamente em qualquer treino/dia que referencie o mesmo exercicio
(nao existe copia de midia por instancia de treino).

Cenario motivador (pedido explicito do usuario): se um dia de treino tem 6
exercicios de peito diferentes, cada um tem sua propria foto — subir uma
foto no Supino nao deve aparecer no Crucifixo. Mas se o MESMO exercicio
(mesmo exercise_id) aparece em dois dias diferentes, a foto ja enviada
aparece pre-preenchida automaticamente no segundo uso, sem re-upload.
"""

from datetime import date, timedelta
from io import BytesIO

import pytest
from PIL import Image

from app.models.exercise import Exercise
from app.utils.uuid import generate_uuid

API = "/api/v1"


def _fake_image_bytes(color=(255, 0, 0)) -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (10, 10), color=color).save(buffer, format="JPEG")
    return buffer.getvalue()


def _upload(client, headers, exercise_id, filename="foto.jpg", color=(255, 0, 0), sort_order=None):
    files = {"file": (filename, _fake_image_bytes(color), "image/jpeg")}
    data = {"sort_order": str(sort_order)} if sort_order is not None else None
    return client.post(f"{API}/exercises/{exercise_id}/images", files=files, data=data, headers=headers)


@pytest.fixture
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture
def make_exercise(db, admin):
    created_ids = []

    def _make(name: str, muscle_group: str = "peito"):
        item = Exercise(
            id=generate_uuid(),
            admin_id=admin.id,
            name=f"{name} {generate_uuid()[:8]}",
            muscle_group=muscle_group,
            default_sets=3,
            default_reps=10,
        )
        db.add(item)
        db.commit()
        db.refresh(item)
        created_ids.append(item.id)
        return item

    yield _make

    db.expire_all()
    # ExerciseImage tem ON DELETE CASCADE em exercise_id: apagar o exercicio
    # ja remove as midias associadas junto.
    db.query(Exercise).filter(Exercise.id.in_(created_ids)).delete(synchronize_session=False)
    db.commit()


class TestMediaIsScopedPerExercise:
    """6 exercicios diferentes no mesmo dia = 6 galerias de midia independentes."""

    def test_uploading_to_one_exercise_does_not_leak_into_another(self, client, admin_headers, make_exercise):
        supino = make_exercise("Supino Reto")
        crucifixo = make_exercise("Crucifixo")

        upload_resp = _upload(client, admin_headers, supino.id)
        assert upload_resp.status_code == 201, upload_resp.text
        uploaded = upload_resp.json()
        assert uploaded["media_type"] == "image"

        supino_detail = client.get(f"{API}/exercises/{supino.id}", headers=admin_headers).json()
        crucifixo_detail = client.get(f"{API}/exercises/{crucifixo.id}", headers=admin_headers).json()

        assert [img["id"] for img in supino_detail["images"]] == [uploaded["id"]]
        assert crucifixo_detail["images"] == []

    def test_six_different_exercises_each_keep_their_own_single_photo(self, client, admin_headers, make_exercise):
        names = ["Supino Reto", "Supino Inclinado", "Crucifixo", "Crossover", "Peck Deck", "Flexao"]
        exercises = [make_exercise(name) for name in names]

        uploaded_ids = {}
        for ex in exercises:
            resp = _upload(client, admin_headers, ex.id, filename=f"{ex.name}.jpg")
            assert resp.status_code == 201, resp.text
            uploaded_ids[ex.id] = resp.json()["id"]

        for ex in exercises:
            detail = client.get(f"{API}/exercises/{ex.id}", headers=admin_headers).json()
            assert [img["id"] for img in detail["images"]] == [uploaded_ids[ex.id]]


class TestMediaReusedAcrossTrainingOccurrences:
    """Mesmo exercicio em dois dias/treinos -> mesma midia aparece nos dois, sem novo upload."""

    def test_same_exercise_in_two_days_shares_the_uploaded_photo(
        self, client, db, admin, admin_headers, make_exercise, make_student
    ):
        supino = make_exercise("Supino Reto")
        student, _ = make_student()

        upload_resp = _upload(client, admin_headers, supino.id)
        assert upload_resp.status_code == 201, upload_resp.text
        media = upload_resp.json()

        today = date.today()
        payload = {
            "student_id": student.id,
            "title": "Treino Pytest Midia",
            "start_date": today.isoformat(),
            "end_date": (today + timedelta(days=60)).isoformat(),
            "days": [
                {
                    "day_of_week": 0,
                    "label": "Treino A",
                    "exercises": [{"exercise_id": supino.id, "sets": 4, "reps": 10}],
                },
                {
                    "day_of_week": 3,
                    "label": "Treino B",
                    "exercises": [{"exercise_id": supino.id, "sets": 3, "reps": 12}],
                },
            ],
        }
        create_resp = client.post(f"{API}/trainings/complete", json=payload, headers=admin_headers)
        assert create_resp.status_code == 201, create_resp.text
        training = create_resp.json()

        detail_resp = client.get(f"{API}/trainings/{training['id']}", headers=admin_headers)
        assert detail_resp.status_code == 200, detail_resp.text
        detail = detail_resp.json()

        assert len(detail["days"]) == 2
        for day in detail["days"]:
            assert len(day["exercises"]) == 1
            exercise_entry = day["exercises"][0]
            assert exercise_entry["exercise_id"] == supino.id
            assert [img["url"] for img in exercise_entry["images"]] == [
                f"/api/v1/uploads/{media['url'].split('/uploads/', 1)[1]}"
            ]

    def test_deleting_the_image_removes_it_from_every_day_that_references_the_exercise(
        self, client, db, admin, admin_headers, make_exercise, make_student
    ):
        supino = make_exercise("Supino Reto")
        student, _ = make_student()
        media = _upload(client, admin_headers, supino.id).json()

        today = date.today()
        payload = {
            "student_id": student.id,
            "title": "Treino Pytest Delete",
            "start_date": today.isoformat(),
            "end_date": (today + timedelta(days=30)).isoformat(),
            "days": [
                {"day_of_week": 0, "exercises": [{"exercise_id": supino.id, "sets": 3, "reps": 10}]},
                {"day_of_week": 2, "exercises": [{"exercise_id": supino.id, "sets": 3, "reps": 10}]},
            ],
        }
        training = client.post(f"{API}/trainings/complete", json=payload, headers=admin_headers).json()

        del_resp = client.delete(f"{API}/exercises/{supino.id}/images/{media['id']}", headers=admin_headers)
        assert del_resp.status_code == 204

        detail = client.get(f"{API}/trainings/{training['id']}", headers=admin_headers).json()
        for day in detail["days"]:
            assert day["exercises"][0]["images"] == []


class TestFeaturedMedia:
    """Marcar uma midia com a estrela de destaque a torna a capa do exercicio em todo lugar."""

    def test_featuring_an_image_puts_it_first_regardless_of_upload_order(self, client, admin_headers, make_exercise):
        supino = make_exercise("Supino Reto")

        first = _upload(client, admin_headers, supino.id, filename="primeira.jpg", sort_order=0).json()
        second = _upload(client, admin_headers, supino.id, filename="segunda.jpg", sort_order=1).json()

        detail_before = client.get(f"{API}/exercises/{supino.id}", headers=admin_headers).json()
        assert [img["id"] for img in detail_before["images"]] == [first["id"], second["id"]]
        assert all(not img["is_featured"] for img in detail_before["images"])

        feature_resp = client.post(
            f"{API}/exercises/{supino.id}/images/{second['id']}/feature", headers=admin_headers
        )
        assert feature_resp.status_code == 200, feature_resp.text
        detail_after = feature_resp.json()

        assert [img["id"] for img in detail_after["images"]] == [second["id"], first["id"]]
        assert detail_after["images"][0]["is_featured"] is True
        assert detail_after["images"][1]["is_featured"] is False

    def test_featuring_a_new_image_unfeatures_the_previous_one(self, client, admin_headers, make_exercise):
        supino = make_exercise("Supino Reto")
        first = _upload(client, admin_headers, supino.id, filename="primeira.jpg", sort_order=0).json()
        second = _upload(client, admin_headers, supino.id, filename="segunda.jpg", sort_order=1).json()

        client.post(f"{API}/exercises/{supino.id}/images/{first['id']}/feature", headers=admin_headers)
        client.post(f"{API}/exercises/{supino.id}/images/{second['id']}/feature", headers=admin_headers)

        detail = client.get(f"{API}/exercises/{supino.id}", headers=admin_headers).json()
        featured_ids = [img["id"] for img in detail["images"] if img["is_featured"]]
        assert featured_ids == [second["id"]]

    def test_training_detail_shows_the_featured_image_first_for_the_shared_exercise(
        self, client, admin_headers, make_exercise, make_student
    ):
        supino = make_exercise("Supino Reto")
        student, _ = make_student()
        first = _upload(client, admin_headers, supino.id, filename="primeira.jpg", sort_order=0).json()
        second = _upload(client, admin_headers, supino.id, filename="segunda.jpg", sort_order=1).json()
        client.post(f"{API}/exercises/{supino.id}/images/{second['id']}/feature", headers=admin_headers)

        today = date.today()
        payload = {
            "student_id": student.id,
            "title": "Treino Pytest Destaque",
            "start_date": today.isoformat(),
            "end_date": (today + timedelta(days=30)).isoformat(),
            "days": [{"day_of_week": 0, "exercises": [{"exercise_id": supino.id, "sets": 3, "reps": 10}]}],
        }
        training = client.post(f"{API}/trainings/complete", json=payload, headers=admin_headers).json()

        detail = client.get(f"{API}/trainings/{training['id']}", headers=admin_headers).json()
        images = detail["days"][0]["exercises"][0]["images"]
        assert images[0]["url"].endswith(second["url"].rsplit("/", 1)[-1])
        assert images[1]["url"].endswith(first["url"].rsplit("/", 1)[-1])


class TestMediaUploadLimit:
    def test_sixth_upload_is_rejected_and_gallery_stays_at_five(self, client, admin_headers, make_exercise):
        supino = make_exercise("Supino Reto")

        for _ in range(5):
            resp = _upload(client, admin_headers, supino.id)
            assert resp.status_code == 201, resp.text

        sixth = _upload(client, admin_headers, supino.id)
        assert sixth.status_code == 400
        assert sixth.json()["error"]["code"] == "VALIDATION_ERROR"

        detail = client.get(f"{API}/exercises/{supino.id}", headers=admin_headers).json()
        assert len(detail["images"]) == 5
