import pytest
from fastapi.testclient import TestClient

from app.auth.jwt_handler import create_access_token
from app.auth.password import hash_password
from app.core.config import settings
from app.database.session import SessionLocal
from app.main import app
from app.models.attendance_record import AttendanceRecord
from app.models.exercise import Exercise
from app.models.exercise_completion import ExerciseCompletion
from app.models.progress_photo import ProgressPhoto
from app.models.student_profile import StudentProfile
from app.models.training import Training
from app.models.training_day import TrainingDay
from app.models.training_exercise import TrainingExercise
from app.models.user import User
from app.models.workout_session import WorkoutSession
from app.utils.uuid import generate_uuid


def _purge_student(db, user_id: str) -> None:
    """Apaga em bloco (sem cascade_iterator do ORM) toda a arvore ligada a um
    aluno de teste, respeitando a ordem de FKs (filhos antes dos pais)."""
    training_ids = [t.id for t in db.query(Training.id).filter(Training.student_id == user_id)]
    day_ids = (
        [d.id for d in db.query(TrainingDay.id).filter(TrainingDay.training_id.in_(training_ids))]
        if training_ids
        else []
    )

    db.query(ExerciseCompletion).filter(
        ExerciseCompletion.workout_session_id.in_(
            db.query(WorkoutSession.id).filter(WorkoutSession.student_id == user_id)
        )
    ).delete(synchronize_session=False)
    db.query(WorkoutSession).filter(WorkoutSession.student_id == user_id).delete(synchronize_session=False)
    if day_ids:
        db.query(TrainingExercise).filter(TrainingExercise.training_day_id.in_(day_ids)).delete(synchronize_session=False)
        db.query(TrainingDay).filter(TrainingDay.training_id.in_(training_ids)).delete(synchronize_session=False)
    db.query(AttendanceRecord).filter(AttendanceRecord.student_id == user_id).delete(synchronize_session=False)
    db.query(ProgressPhoto).filter(ProgressPhoto.student_id == user_id).delete(synchronize_session=False)
    db.query(Training).filter(Training.student_id == user_id).delete(synchronize_session=False)
    db.query(StudentProfile).filter(StudentProfile.user_id == user_id).delete(synchronize_session=False)
    db.query(User).filter(User.id == user_id).delete(synchronize_session=False)
    db.commit()


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def admin(db):
    user = db.query(User).filter(User.email == settings.admin_email).first()
    assert user is not None, "admin seedado no startup do app nao encontrado"
    return user


@pytest.fixture
def admin_token(admin):
    token, _ = create_access_token(subject=admin.id, role="admin", admin_id=admin.id)
    return token


@pytest.fixture
def exercise(db, admin):
    item = Exercise(
        id=generate_uuid(),
        admin_id=admin.id,
        name=f"Supino Reto {generate_uuid()[:8]}",
        muscle_group="peito",
        default_sets=3,
        default_reps=10,
    )
    db.add(item)
    db.commit()
    yield item
    db.expire_all()
    db.query(Exercise).filter(Exercise.id == item.id).delete(synchronize_session=False)
    db.commit()


@pytest.fixture
def make_student(db, admin):
    created_ids = []

    def _make(full_name: str = "Aluno Teste"):
        suffix = generate_uuid()[:8]
        user = User(
            id=generate_uuid(),
            email=f"pytest.{suffix}@test.com",
            password_hash=hash_password("Teste123!"),
            role="student",
        )
        db.add(user)
        db.flush()

        profile = StudentProfile(user_id=user.id, admin_id=admin.id, full_name=full_name)
        db.add(profile)
        db.commit()

        token, _ = create_access_token(subject=user.id, role="student", admin_id=admin.id)
        created_ids.append(user.id)
        return user, token

    yield _make

    db.rollback()
    for user_id in created_ids:
        _purge_student(db, user_id)
