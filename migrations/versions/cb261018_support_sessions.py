"""Opt-in support sessions.

Revision ID: cb261018
Revises: abd20261018
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
revision = 'cb261018'
down_revision = 'abd20261018'
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('users', sa.Column('support_access_enabled', sa.Boolean(), server_default=sa.false(), nullable=False))
    op.create_table('support_sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('admin_user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('target_user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('code_hash', sa.String(64), nullable=False, unique=True),
        sa.Column('code_expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('session_expires_at', sa.DateTime(timezone=True)),
        sa.Column('consumed_at', sa.DateTime(timezone=True)),
        sa.Column('revoked_at', sa.DateTime(timezone=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))
    op.create_index('ix_support_sessions_admin_user_id', 'support_sessions', ['admin_user_id'])
    op.create_index('ix_support_sessions_target_user_id', 'support_sessions', ['target_user_id'])

def downgrade():
    op.drop_table('support_sessions')
    op.drop_column('users', 'support_access_enabled')
