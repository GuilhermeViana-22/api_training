"""add_gif_media_type

Revision ID: bfd2dce668d9
Revises: fea423061f80
Create Date: 2026-07-17 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bfd2dce668d9'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        'exercise_images',
        'media_type',
        existing_type=sa.Enum('image', 'video', name='media_type'),
        type_=sa.Enum('image', 'gif', 'video', name='media_type'),
        existing_nullable=False,
        existing_server_default=None,
    )
    op.create_index('ix_exercise_images_media_type', 'exercise_images', ['media_type'])


def downgrade() -> None:
    op.drop_index('ix_exercise_images_media_type', table_name='exercise_images')
    op.execute("UPDATE exercise_images SET media_type = 'image' WHERE media_type = 'gif'")
    op.alter_column(
        'exercise_images',
        'media_type',
        existing_type=sa.Enum('image', 'gif', 'video', name='media_type'),
        type_=sa.Enum('image', 'video', name='media_type'),
        existing_nullable=False,
        existing_server_default=None,
    )
