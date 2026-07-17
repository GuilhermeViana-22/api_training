"""student_profile_workout_categories

Revision ID: a1b2c3d4e5f6
Revises: fea423061f80
Create Date: 2026-07-16 23:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "fea423061f80"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "training_categories",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("slug", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )

    op.create_table(
        "workout_sessions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("student_id", sa.String(length=36), nullable=False),
        sa.Column("training_id", sa.String(length=36), nullable=False),
        sa.Column("training_day_id", sa.String(length=36), nullable=False),
        sa.Column("session_date", sa.Date(), nullable=False),
        sa.Column("status", sa.Enum("in_progress", "completed", name="workout_session_status"), nullable=False),
        sa.Column("started_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["student_id"], ["student_profiles.user_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["training_id"], ["trainings.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["training_day_id"], ["training_days.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_workout_sessions_session_date"), "workout_sessions", ["session_date"], unique=False)
    op.create_index(op.f("ix_workout_sessions_student_id"), "workout_sessions", ["student_id"], unique=False)

    op.create_table(
        "exercise_completions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("workout_session_id", sa.String(length=36), nullable=False),
        sa.Column("training_exercise_id", sa.String(length=36), nullable=False),
        sa.Column("completed_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["training_exercise_id"], ["training_exercises.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workout_session_id"], ["workout_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_exercise_completions_training_exercise_id"),
        "exercise_completions",
        ["training_exercise_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_exercise_completions_workout_session_id"),
        "exercise_completions",
        ["workout_session_id"],
        unique=False,
    )

    op.add_column("trainings", sa.Column("category_id", sa.String(length=36), nullable=True))
    op.create_index(op.f("ix_trainings_category_id"), "trainings", ["category_id"], unique=False)
    op.create_foreign_key(
        "fk_trainings_category_id", "trainings", "training_categories", ["category_id"], ["id"], ondelete="SET NULL"
    )

    op.add_column("exercises", sa.Column("category_id", sa.String(length=36), nullable=True))
    op.create_index(op.f("ix_exercises_category_id"), "exercises", ["category_id"], unique=False)
    op.create_foreign_key(
        "fk_exercises_category_id", "exercises", "training_categories", ["category_id"], ["id"], ondelete="SET NULL"
    )

    op.add_column("progress_photos", sa.Column("training_id", sa.String(length=36), nullable=True))
    op.add_column("progress_photos", sa.Column("day_of_week", sa.SmallInteger(), nullable=True))
    op.create_foreign_key(
        "fk_progress_photos_training_id", "progress_photos", "trainings", ["training_id"], ["id"], ondelete="SET NULL"
    )


def downgrade() -> None:
    op.drop_constraint("fk_progress_photos_training_id", "progress_photos", type_="foreignkey")
    op.drop_column("progress_photos", "day_of_week")
    op.drop_column("progress_photos", "training_id")

    op.drop_constraint("fk_exercises_category_id", "exercises", type_="foreignkey")
    op.drop_index(op.f("ix_exercises_category_id"), table_name="exercises")
    op.drop_column("exercises", "category_id")

    op.drop_constraint("fk_trainings_category_id", "trainings", type_="foreignkey")
    op.drop_index(op.f("ix_trainings_category_id"), table_name="trainings")
    op.drop_column("trainings", "category_id")

    op.drop_index(op.f("ix_exercise_completions_workout_session_id"), table_name="exercise_completions")
    op.drop_index(op.f("ix_exercise_completions_training_exercise_id"), table_name="exercise_completions")
    op.drop_table("exercise_completions")

    op.drop_index(op.f("ix_workout_sessions_student_id"), table_name="workout_sessions")
    op.drop_index(op.f("ix_workout_sessions_session_date"), table_name="workout_sessions")
    op.drop_table("workout_sessions")

    op.drop_table("training_categories")
