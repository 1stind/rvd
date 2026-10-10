"""refactor_database_architecture

Revision ID: 9db3118321d8
Revises: 
Create Date: 2026-08-04 17:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9db3118321d8'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    event_status = sa.Enum("DRAFT", "PUBLISHED", "VOTING_OPEN", "VOTING_CLOSED", "FINISHED", "ARCHIVED", name="event_status")
    payment_status = sa.Enum("PENDING", "SETTLED", "SUCCESS", "FAILED", "EXPIRED", "CANCELED", name="payment_status")
    payment_gateway = sa.Enum("MIDTRANS", "MANUAL", "TRANSFER", name="payment_gateway")
    payment_channel = sa.Enum("QRIS", "BANK_TRANSFER", "E_WALLET", "CASH", name="payment_channel")
    queue_status = sa.Enum("WAITING", "ACTIVE", "EXPIRED", "RELEASED", name="queue_status")
    user_role = sa.Enum("ADMIN", "USER", name="user_role")
    audit_actor = sa.Enum("ADMIN", "USER", "SYSTEM", "WEBHOOK", name="audit_actor")

    # ### users ###
    op.create_table(
        'users',
        sa.Column('id', sa.String(length=40), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('role', user_role, nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_deleted_at'), 'users', ['deleted_at'], unique=False)

    # ### events ###
    op.create_table(
        'events',
        sa.Column('id', sa.String(length=40), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('slug', sa.String(length=100), nullable=True),
        sa.Column('banner_url', sa.String(length=500), nullable=True),
        sa.Column('timezone', sa.String(length=50), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=False),
        sa.Column('price_per_vote', sa.Integer(), nullable=True),
        sa.Column('max_vote_per_transaction', sa.Integer(), nullable=True),
        sa.Column('status', event_status, nullable=False),
        sa.Column('opens_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('closes_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_events_status'), 'events', ['status'], unique=False)
    op.create_index(op.f('ix_events_slug'), 'events', ['slug'], unique=True)
    op.create_index(op.f('ix_events_deleted_at'), 'events', ['deleted_at'], unique=False)

    # ### teams ###
    op.create_table(
        'teams',
        sa.Column('id', sa.String(length=40), nullable=False),
        sa.Column('event_id', sa.String(length=40), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('school', sa.String(length=200), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('logo_url', sa.String(length=500), nullable=True),
        sa.Column('sort_order', sa.Integer(), nullable=False),
        sa.Column('total_votes', sa.Integer(), nullable=False),
        sa.Column('supporter_count', sa.Integer(), nullable=False),
        sa.Column('current_rank', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['event_id'], ['events.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_teams_event_id'), 'teams', ['event_id'], unique=False)
    op.create_index(op.f('ix_teams_deleted_at'), 'teams', ['deleted_at'], unique=False)

    # ### vote_packages ###
    op.create_table(
        'vote_packages',
        sa.Column('id', sa.String(length=40), nullable=False),
        sa.Column('event_id', sa.String(length=40), nullable=False),
        sa.Column('code', sa.String(length=40), nullable=False),
        sa.Column('label', sa.String(length=80), nullable=False),
        sa.Column('price', sa.Integer(), nullable=False),
        sa.Column('votes', sa.Integer(), nullable=False),
        sa.Column('bonus_votes', sa.Integer(), nullable=False),
        sa.Column('unit_price', sa.Integer(), nullable=True),
        sa.Column('sort_order', sa.Integer(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['event_id'], ['events.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('event_id', 'code', name='uq_vote_package_event_code')
    )
    op.create_index(op.f('ix_vote_packages_event_id'), 'vote_packages', ['event_id'], unique=False)
    op.create_index(op.f('ix_vote_packages_deleted_at'), 'vote_packages', ['deleted_at'], unique=False)

    # ### payments ###
    op.create_table(
        'payments',
        sa.Column('id', sa.String(length=40), nullable=False),
        sa.Column('team_id', sa.String(length=40), nullable=False),
        sa.Column('event_id', sa.String(length=40), nullable=False),
        sa.Column('user_id', sa.String(length=40), nullable=True),
        sa.Column('supporter_name', sa.String(length=100), nullable=False),
        sa.Column('supporter_email', sa.String(length=255), nullable=True),
        sa.Column('supporter_phone', sa.String(length=20), nullable=False),
        sa.Column('is_anonymous', sa.Boolean(), nullable=False),
        sa.Column('package_id', sa.String(length=40), nullable=True),
        sa.Column('package_code', sa.String(length=40), nullable=False),
        sa.Column('package_label', sa.String(length=80), nullable=False),
        sa.Column('qty', sa.Integer(), nullable=False),
        sa.Column('amount', sa.Integer(), nullable=False),
        sa.Column('votes', sa.Integer(), nullable=False),
        sa.Column('vote_snapshot', sa.JSON(), nullable=False),
        sa.Column('status', payment_status, nullable=False),
        sa.Column('payment_gateway', payment_gateway, nullable=False),
        sa.Column('payment_channel', payment_channel, nullable=True),
        sa.Column('currency', sa.String(length=3), nullable=False),
        sa.Column('signature_key', sa.String(length=255), nullable=True),
        sa.Column('webhook_payload', sa.JSON(), nullable=True),
        sa.Column('webhook_received_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('settled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('midtrans_order_id', sa.String(length=100), nullable=True),
        sa.Column('midtrans_transaction_id', sa.String(length=100), nullable=True),
        sa.Column('midtrans_payload', sa.JSON(), nullable=True),
        sa.Column('idempotency_key', sa.String(length=64), nullable=True),
        sa.Column('paid_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['event_id'], ['events.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['package_id'], ['vote_packages.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['team_id'], ['teams.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('idempotency_key'),
        sa.CheckConstraint('amount >= 0', name='ck_payment_amount_non_negative'),
        sa.CheckConstraint('votes > 0', name='ck_payment_votes_positive'),
        sa.CheckConstraint('qty > 0', name='ck_payment_qty_positive'),
    )
    op.create_index(op.f('ix_payments_event_id'), 'payments', ['event_id'], unique=False)
    op.create_index(op.f('ix_payments_midtrans_order_id'), 'payments', ['midtrans_order_id'], unique=False)
    op.create_index(op.f('ix_payments_status'), 'payments', ['status'], unique=False)
    op.create_index(op.f('ix_payments_team_id'), 'payments', ['team_id'], unique=False)
    op.create_index(op.f('ix_payments_user_id'), 'payments', ['user_id'], unique=False)

    # ### vote_logs ###
    op.create_table(
        'vote_logs',
        sa.Column('id', sa.String(length=40), nullable=False),
        sa.Column('payment_id', sa.String(length=40), nullable=False),
        sa.Column('team_id', sa.String(length=40), nullable=False),
        sa.Column('event_id', sa.String(length=40), nullable=False),
        sa.Column('votes', sa.Integer(), nullable=False),
        sa.Column('payment_amount', sa.Integer(), nullable=False),
        sa.Column('package_code', sa.String(length=40), nullable=True),
        sa.Column('package_label', sa.String(length=80), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['event_id'], ['events.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['payment_id'], ['payments.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['team_id'], ['teams.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint('votes > 0', name='ck_vote_log_votes_positive'),
    )
    op.create_index(op.f('ix_vote_logs_event_id'), 'vote_logs', ['event_id'], unique=False)
    op.create_index(op.f('ix_vote_logs_payment_id'), 'vote_logs', ['payment_id'], unique=False)
    op.create_index(op.f('ix_vote_logs_team_id'), 'vote_logs', ['team_id'], unique=False)

    # ### audit_logs ###
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.String(length=40), nullable=False),
        sa.Column('actor_type', audit_actor, nullable=True),
        sa.Column('actor_name', sa.String(length=100), nullable=True),
        sa.Column('request_id', sa.String(length=40), nullable=True),
        sa.Column('action', sa.String(length=80), nullable=False),
        sa.Column('entity_type', sa.String(length=80), nullable=True),
        sa.Column('entity_id', sa.String(length=80), nullable=True),
        sa.Column('detail', sa.JSON(), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_audit_logs_action'), 'audit_logs', ['action'], unique=False)
    op.create_index(op.f('ix_audit_logs_actor_type'), 'audit_logs', ['actor_type'], unique=False)
    op.create_index(op.f('ix_audit_logs_request_id'), 'audit_logs', ['request_id'], unique=False)
    op.create_index(op.f('ix_audit_logs_created_at'), 'audit_logs', ['created_at'], unique=False)

    # ### queue_sessions ###
    op.create_table(
        'queue_sessions',
        sa.Column('id', sa.String(length=40), nullable=False),
        sa.Column('event_id', sa.String(length=40), nullable=False),
        sa.Column('session_token', sa.String(length=64), nullable=False),
        sa.Column('position', sa.Integer(), nullable=False),
        sa.Column('status', queue_status, nullable=False),
        sa.Column('entered_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('released_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['event_id'], ['events.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_queue_sessions_event_id'), 'queue_sessions', ['event_id'], unique=False)
    op.create_index(op.f('ix_queue_sessions_status'), 'queue_sessions', ['status'], unique=False)
    op.create_index('ix_queue_event_status', 'queue_sessions', ['event_id', 'status'], unique=False)
    op.create_index('ix_queue_position', 'queue_sessions', ['position'], unique=False)

    # ### leaderboard_snapshots ###
    op.create_table(
        'leaderboard_snapshots',
        sa.Column('id', sa.String(length=40), nullable=False),
        sa.Column('event_id', sa.String(length=40), nullable=False),
        sa.Column('team_id', sa.String(length=40), nullable=False),
        sa.Column('rank', sa.Integer(), nullable=False),
        sa.Column('total_votes', sa.Integer(), nullable=False),
        sa.Column('captured_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['event_id'], ['events.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['team_id'], ['teams.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_leaderboard_snapshots_event_id'), 'leaderboard_snapshots', ['event_id'], unique=False)
    op.create_index(op.f('ix_leaderboard_snapshots_team_id'), 'leaderboard_snapshots', ['team_id'], unique=False)
    op.create_index(op.f('ix_leaderboard_snapshots_captured_at'), 'leaderboard_snapshots', ['captured_at'], unique=False)

    # ### webhook_logs ###
    op.create_table(
        'webhook_logs',
        sa.Column('id', sa.String(length=40), nullable=False),
        sa.Column('payment_id', sa.String(length=40), nullable=False),
        sa.Column('provider', sa.String(length=40), nullable=False),
        sa.Column('payload', sa.JSON(), nullable=False),
        sa.Column('signature', sa.String(length=255), nullable=True),
        sa.Column('is_valid', sa.Boolean(), nullable=False),
        sa.Column('received_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.String(length=40), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['payment_id'], ['payments.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_webhook_logs_payment_id'), 'webhook_logs', ['payment_id'], unique=False)

    # ### system_settings ###
    op.create_table(
        'system_settings',
        sa.Column('key', sa.String(length=100), nullable=False),
        sa.Column('value', sa.String(length=500), nullable=True),
        sa.Column('description', sa.String(length=255), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('key')
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### end Alembic commands ###
    op.drop_table('system_settings')
    op.drop_index(op.f('ix_webhook_logs_payment_id'), table_name='webhook_logs')
    op.drop_table('webhook_logs')
    op.drop_index(op.f('ix_leaderboard_snapshots_captured_at'), table_name='leaderboard_snapshots')
    op.drop_index(op.f('ix_leaderboard_snapshots_team_id'), table_name='leaderboard_snapshots')
    op.drop_index(op.f('ix_leaderboard_snapshots_event_id'), table_name='leaderboard_snapshots')
    op.drop_table('leaderboard_snapshots')
    op.drop_index('ix_queue_position', table_name='queue_sessions')
    op.drop_index('ix_queue_event_status', table_name='queue_sessions')
    op.drop_index(op.f('ix_queue_sessions_status'), table_name='queue_sessions')
    op.drop_index(op.f('ix_queue_sessions_event_id'), table_name='queue_sessions')
    op.drop_table('queue_sessions')
    op.drop_index(op.f('ix_audit_logs_created_at'), table_name='audit_logs')
    op.drop_index(op.f('ix_audit_logs_request_id'), table_name='audit_logs')
    op.drop_index(op.f('ix_audit_logs_actor_type'), table_name='audit_logs')
    op.drop_index(op.f('ix_audit_logs_action'), table_name='audit_logs')
    op.drop_table('audit_logs')
    op.drop_index(op.f('ix_vote_logs_team_id'), table_name='vote_logs')
    op.drop_index(op.f('ix_vote_logs_payment_id'), table_name='vote_logs')
    op.drop_index(op.f('ix_vote_logs_event_id'), table_name='vote_logs')
    op.drop_table('vote_logs')
    op.drop_index(op.f('ix_payments_user_id'), table_name='payments')
    op.drop_index(op.f('ix_payments_team_id'), table_name='payments')
    op.drop_index(op.f('ix_payments_status'), table_name='payments')
    op.drop_index(op.f('ix_payments_midtrans_order_id'), table_name='payments')
    op.drop_index(op.f('ix_payments_event_id'), table_name='payments')
    op.drop_table('payments')
    op.drop_index(op.f('ix_vote_packages_deleted_at'), table_name='vote_packages')
    op.drop_index(op.f('ix_vote_packages_event_id'), table_name='vote_packages')
    op.drop_table('vote_packages')
    op.drop_index(op.f('ix_teams_deleted_at'), table_name='teams')
    op.drop_index(op.f('ix_teams_event_id'), table_name='teams')
    op.drop_table('teams')
    op.drop_index(op.f('ix_events_deleted_at'), table_name='events')
    op.drop_index(op.f('ix_events_slug'), table_name='events')
    op.drop_index(op.f('ix_events_status'), table_name='events')
    op.drop_table('events')
    op.drop_index(op.f('ix_users_deleted_at'), table_name='users')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')

    # ### drop enums ###
    op.execute("DROP TYPE IF EXISTS audit_actor CASCADE")
    op.execute("DROP TYPE IF EXISTS user_role CASCADE")
    op.execute("DROP TYPE IF EXISTS queue_status CASCADE")
    op.execute("DROP TYPE IF EXISTS payment_channel CASCADE")
    op.execute("DROP TYPE IF EXISTS payment_gateway CASCADE")
    op.execute("DROP TYPE IF EXISTS payment_status CASCADE")
    op.execute("DROP TYPE IF EXISTS event_status CASCADE")
    # ### end Alembic commands ###
