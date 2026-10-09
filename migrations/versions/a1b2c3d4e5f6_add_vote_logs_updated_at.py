"""add_vote_logs_updated_at

Revision ID: a1b2c3d4e5f6
Revises: 9db3118321d8
Create Date: 2026-08-30 00:51:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '9db3118321d8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    # Add updated_at column if it doesn't exist
    result = bind.execute(
        sa.text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name = 'vote_logs' AND column_name = 'updated_at'"
        )
    ).fetchone()

    if not result:
        op.add_column(
            'vote_logs',
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())
        )


def downgrade() -> None:
    bind = op.get_bind()
    result = bind.execute(
        sa.text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name = 'vote_logs' AND column_name = 'updated_at'"
        )
    ).fetchone()

    if result:
        op.drop_column('vote_logs', 'updated_at')
