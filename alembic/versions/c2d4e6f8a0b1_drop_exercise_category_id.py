"""drop_exercise_category_id

Revision ID: c2d4e6f8a0b1
Revises: bfd2dce668d9
Create Date: 2026-07-17 21:50:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c2d4e6f8a0b1"
down_revision: Union[str, None] = "bfd2dce668d9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("fk_exercises_category_id", "exercises", type_="foreignkey")
    op.drop_index(op.f("ix_exercises_category_id"), table_name="exercises")
    op.drop_column("exercises", "category_id")


def downgrade() -> None:
    op.add_column("exercises", sa.Column("category_id", sa.String(length=36), nullable=True))
    op.create_index(op.f("ix_exercises_category_id"), "exercises", ["category_id"], unique=False)
    op.create_foreign_key(
        "fk_exercises_category_id", "exercises", "training_categories", ["category_id"], ["id"], ondelete="SET NULL"
    )
