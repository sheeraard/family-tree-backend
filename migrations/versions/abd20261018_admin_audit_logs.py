"""Add web admin audit logging.
Revision ID: abd20261018
Revises: 809bf6b7e406, 9e0817b1943f
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
revision = 'abd20261018'
down_revision = ('809bf6b7e406', '9e0817b1943f')
branch_labels = None
depends_on = None

def upgrade():
    op.create_table('admin_audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('admin_user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('action', sa.String(60), nullable=False),
        sa.Column('target_id', postgresql.UUID(as_uuid=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'))
    op.create_index('ix_admin_audit_logs_admin_user_id', 'admin_audit_logs', ['admin_user_id'])
    op.add_column('users', sa.Column('last_seen_at', sa.DateTime(timezone=True), nullable=True))
    op.create_index('ix_users_last_seen_at', 'users', ['last_seen_at'])

def downgrade():
    op.drop_index('ix_users_last_seen_at', table_name='users')
    op.drop_column('users', 'last_seen_at')
    op.drop_index('ix_admin_audit_logs_admin_user_id', table_name='admin_audit_logs')
    op.drop_table('admin_audit_logs')
