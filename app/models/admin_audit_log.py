import uuid
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import UUID
from app.extensions import db

class AdminAuditLog(db.Model):
    __tablename__ = "admin_audit_logs"
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    admin_user_id = db.Column(UUID(as_uuid=True), nullable=False, index=True)
    action = db.Column(db.String(60), nullable=False)
    target_id = db.Column(UUID(as_uuid=True), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, server_default=func.now())
