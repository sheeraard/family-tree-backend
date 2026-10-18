import uuid
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import UUID
from app.extensions import db

class SupportSession(db.Model):
    __tablename__ = 'support_sessions'
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    admin_user_id = db.Column(UUID(as_uuid=True), nullable=False, index=True)
    target_user_id = db.Column(UUID(as_uuid=True), nullable=False, index=True)
    code_hash = db.Column(db.String(64), nullable=False, unique=True)
    code_expires_at = db.Column(db.DateTime(timezone=True), nullable=False)
    session_expires_at = db.Column(db.DateTime(timezone=True), nullable=True)
    consumed_at = db.Column(db.DateTime(timezone=True), nullable=True)
    revoked_at = db.Column(db.DateTime(timezone=True), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, server_default=func.now())
