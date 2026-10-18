"""Track recent authenticated API activity, without logging content or IP addresses."""
from datetime import datetime, timedelta, timezone
from uuid import UUID
from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
from sqlalchemy import update, or_
from app.extensions import db
from app.models.user import User

activity_bp = Blueprint("admin_activity", __name__)

@activity_bp.after_app_request
def track_authenticated_requests(response):
    if not request.path.startswith("/api/") or not request.headers.get("Authorization", "").lower().startswith("bearer "):
        return response
    if response.status_code >= 400:
        return response
    try:
        verify_jwt_in_request()
        identity = UUID(str(get_jwt_identity()))
        now = datetime.now(timezone.utc)
        db.session.execute(update(User).where(
            User.id == identity,
            or_(User.last_seen_at.is_(None), User.last_seen_at < now - timedelta(seconds=60))
        ).values(last_seen_at=now))
        db.session.commit()
    except Exception:
        db.session.rollback()
        # Never turn an otherwise successful application request into an error just for presence tracking.
    return response
