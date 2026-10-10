"""voting hot path: previous_rank, one vote log per payment, payment lookup indexes

- teams.previous_rank replaces the per-vote leaderboard_snapshots rows as the
  source of the rank trend (one row per team instead of one per team per vote).
- vote_logs.payment_id becomes unique so a duplicated webhook can never grant
  the same payment twice.
- composite indexes for the per-phone pending check and the successful-payment
  listings.

Revision ID: b7c8d9e0f1a2
Revises: a1b2c3d4e5f6
Create Date: 2026-10-10 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b7c8d9e0f1a2'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('teams', sa.Column('previous_rank', sa.Integer(), nullable=True))

    op.drop_index('ix_vote_logs_payment_id', table_name='vote_logs')
    op.create_index('ix_vote_logs_payment_id', 'vote_logs', ['payment_id'], unique=True)

    op.create_index(
        'ix_payments_event_phone_status', 'payments', ['event_id', 'supporter_phone', 'status']
    )
    op.create_index(
        'ix_payments_event_status_created', 'payments', ['event_id', 'status', 'created_at']
    )


def downgrade() -> None:
    op.drop_index('ix_payments_event_status_created', table_name='payments')
    op.drop_index('ix_payments_event_phone_status', table_name='payments')
    op.drop_index('ix_vote_logs_payment_id', table_name='vote_logs')
    op.create_index('ix_vote_logs_payment_id', 'vote_logs', ['payment_id'], unique=False)
    op.drop_column('teams', 'previous_rank')
