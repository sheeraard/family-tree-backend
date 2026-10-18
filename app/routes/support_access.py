"""Explicitly consented, restricted diagnostic access for debug builds."""
import hashlib
import os
import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt, create_access_token, verify_jwt_in_request
from sqlalchemy import select, update
from app.extensions import db, limiter
from app.models import User, SupportSession
from app.models.admin_audit_log import AdminAuditLog

support_bp = Blueprint('support', __name__)

def enabled():
    return os.environ.get('SUPPORT_LOGIN_ENABLED', '').lower() == 'true'

def utcnow():
    return datetime.now(timezone.utc)

def audit(actor_id, action, target_id):
    db.session.add(AdminAuditLog(admin_user_id=actor_id, action=action, target_id=target_id))

def _hash(code):
    return hashlib.sha256(code.encode('utf-8')).hexdigest()

@support_bp.post('/consent')
@jwt_required()
def consent():
    if get_jwt().get('support_session'):
        return jsonify(message='Support sessions cannot manage consent'), 403
    user = db.session.get(User, UUID(str(get_jwt_identity())))
    body = request.get_json(silent=True) or {}
    if type(body.get('enabled')) is not bool:
        return jsonify(message='enabled must be a boolean'), 400
    user.support_access_enabled = body['enabled']
    if not body['enabled']:
        db.session.execute(update(SupportSession).where(SupportSession.target_user_id == user.id, SupportSession.revoked_at.is_(None)).values(revoked_at=utcnow()))
    db.session.commit()
    return jsonify(enabled=user.support_access_enabled)

@support_bp.get('/consent')
@jwt_required()
def consent_status():
    if get_jwt().get('support_session'):
        return jsonify(enabled=False), 403
    user = db.session.get(User, UUID(str(get_jwt_identity())))
    return jsonify(enabled=user.support_access_enabled)

@support_bp.post('/exchange')
@limiter.limit('5 per minute; 15 per hour')
def exchange():
    if not enabled():
        return jsonify(message='Support access is disabled'), 404
    code = str((request.get_json(silent=True) or {}).get('code', '')).strip().upper().replace('-', '')
    if len(code) != 24 or not code.isalnum():
        return jsonify(message='Invalid or expired code'), 400
    # Row lock prevents concurrent exchanges of the same single-use code.
    entry = db.session.scalar(select(SupportSession).where(SupportSession.code_hash == _hash(code)).with_for_update())
    now = utcnow()
    if not entry or entry.revoked_at or entry.consumed_at or entry.code_expires_at <= now:
        db.session.rollback()
        return jsonify(message='Invalid or expired code'), 400
    target = db.session.get(User, entry.target_user_id)
    actor = db.session.get(User, entry.admin_user_id)
    if not target or not target.is_active or not target.is_email_verified or not target.support_access_enabled or not actor or not actor.is_active or actor.role != User.ROLE_SUPER_ADMIN:
        db.session.rollback()
        return jsonify(message='Access not authorized'), 403
    entry.consumed_at = now
    entry.session_expires_at = now + timedelta(minutes=15)
    audit(actor.id, 'support_session_started', target.id)
    db.session.commit()
    token = create_access_token(identity=str(target.id), expires_delta=timedelta(minutes=15), additional_claims={'support_session':str(entry.id),'support_admin':str(actor.id),'support_readonly':True})
    return jsonify(access_token=token, expires_in_seconds=900, target_email=target.email)

@support_bp.post('/end')
@jwt_required()
def end():
    claims = get_jwt()
    sid = claims.get('support_session')
    if not sid:
        return jsonify(message='Not a support session'), 400
    entry = db.session.get(SupportSession, UUID(sid))
    if entry and not entry.revoked_at:
        entry.revoked_at = utcnow()
        audit(entry.admin_user_id, 'support_session_ended', entry.target_user_id)
        db.session.commit()
    return jsonify(message='Ended')

@support_bp.before_app_request
def protect_support_sessions():
    if not request.path.startswith('/api/') or not request.headers.get('Authorization', '').lower().startswith('bearer '):
        return None
    # This also guards unrelated API blueprints with support JWTs.
    verify_jwt_in_request(optional=True)
    claims = get_jwt()
    sid = claims.get('support_session') if claims else None
    if not sid:
        return None
    if not enabled():
        return jsonify(message='Support access disabled'), 403
    try:
        entry = db.session.get(SupportSession, UUID(sid))
    except (ValueError, TypeError):
        return jsonify(message='Invalid support session'), 401
    now = utcnow()
    if (not entry or not entry.consumed_at or entry.revoked_at or not entry.session_expires_at or entry.session_expires_at <= now or str(entry.target_user_id) != str(get_jwt_identity()) or str(entry.admin_user_id) != str(claims.get('support_admin'))):
        return jsonify(message='Support session expired or revoked'), 401
    target = db.session.get(User, entry.target_user_id)
    actor = db.session.get(User, entry.admin_user_id)
    if not target or not target.support_access_enabled or not actor or actor.role != User.ROLE_SUPER_ADMIN or not actor.is_active:
        return jsonify(message='Support access revoked'), 403
    if request.method not in ('GET', 'HEAD', 'OPTIONS') and request.path != '/api/support/end':
        return jsonify(message='Support session is read-only'), 403
    # Exclude sensitive security endpoints even though they may be GET requests.
    if request.path.startswith(('/api/account', '/api/auth/email-verification', '/api/auth/password-reset')):
        return jsonify(message='This feature is unavailable in support mode'), 403
    return None
