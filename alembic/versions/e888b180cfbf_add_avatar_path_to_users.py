"""add_avatar_path_to_users

Revision ID: e888b180cfbf
Revises: d3e5f7a9b1c2
Create Date: 2026-07-18 23:04:53.995704

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e888b180cfbf'
down_revision: Union[str, None] = 'd3e5f7a9b1c2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('avatar_path', sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'avatar_path')
