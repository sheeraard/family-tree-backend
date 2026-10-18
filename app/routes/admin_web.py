"""Server-rendered administration, separate from the mobile application."""
import hmac
import os
import secrets
from datetime import datetime, timezone
from functools import wraps
from uuid import UUID

from flask import (Blueprint, abort, flash, redirect, render_template,
                   request, session, url_for)
from sqlalchemy import func, select
from werkzeug.security import check_password_hash

from app.extensions import db, limiter
from app.models import User, Product, Person, CultureContent, UmkmApplication

admin_web_bp = Blueprint("admin_web", __name__, template_folder="../templates")

# No user impersonation, raw SQL executor, credential disclosure, or password reset bypass.
READABLE_TABLES = {"users", "people", "products", "culture_contents", "umkm_applications",
                   "historical_people", "historical_relationships", "historical_tree_groups",
                   "relationships", "relationship_requests", "community_posts"}
REDACTED_COLUMNS = {"password_hash", "phone", "email", "birth_date", "claim_code_hash",
                    "document_url", "rejection_reason", "gender", "address", "contact",
                    "verification_code_hash", "code_hash", "reset_token_hash", "token_hash"}



def current_admin():
    raw = session.get("admin_user_id")
    if not raw:
        return None
    try:
        user = db.session.get(User, UUID(raw))
    except (ValueError, TypeError):
        return None
    if not user or not user.is_active or not user.is_admin or session.get("admin_session_version") != user.session_version:
        session.clear()
        return None
    return user


def guarded(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if current_admin() is None:
            return redirect(url_for("admin_web.login"))
        return view(*args, **kwargs)
    return wrapped


def csrf_token():
    if "admin_csrf" not in session:
        session["admin_csrf"] = secrets.token_urlsafe(32)
    return session["admin_csrf"]


def verify_csrf():
    supplied = request.form.get("csrf_token", "")
    if not hmac.compare_digest(supplied, session.get("admin_csrf", "")) or not supplied:
        abort(400, "Invalid form token")


@admin_web_bp.after_request
def secure_response(response):
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Content-Security-Policy"] = ("default-src 'none'; style-src 'self' 'unsafe-inline'; "
                                                   "form-action 'self'; base-uri 'none'; frame-ancestors 'none'")
    return response


@admin_web_bp.app_context_processor
def admin_template_values():
    if not request.path.startswith("/admin"):
        return {}
    return {"admin_user": current_admin(), "csrf_token": csrf_token}


@admin_web_bp.route("/login", methods=["GET", "POST"])
@limiter.limit("5 per minute", methods=["POST"])
def login():
    if request.method == "POST":
        verify_csrf()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = db.session.scalar(select(User).where(User.email == email))
        if (not user or not check_password_hash(user.password_hash, password)
                or not user.is_active or not user.is_email_verified or not user.is_admin):
            flash("Invalid credentials or insufficient admin permissions.", "error")
        else:
            session.clear()
            session["admin_user_id"] = str(user.id)
            session["admin_session_version"] = user.session_version
            session.permanent = False
            csrf_token()
            return redirect(url_for("admin_web.home"))
    return render_template("admin/dashboard.html", view="login")


@admin_web_bp.post("/logout")
@guarded
def logout():
    verify_csrf()
    session.clear()
    return redirect(url_for("admin_web.login"))


@admin_web_bp.get("/")
@guarded
def home():
    totals = {"users": db.session.scalar(select(func.count()).select_from(User)),
              "products": db.session.scalar(select(func.count()).select_from(Product)),
              "people": db.session.scalar(select(func.count()).select_from(Person)),
              "culture": db.session.scalar(select(func.count()).select_from(CultureContent)),
              "pending_umkm": db.session.scalar(select(func.count()).select_from(UmkmApplication).where(UmkmApplication.status == 'pending'))}
    recent = db.session.scalars(select(User).order_by(User.created_at.desc()).limit(8)).all()
    active_since = datetime.now(timezone.utc) - __import__("datetime").timedelta(minutes=5)
    active_recently = db.session.scalar(select(func.count()).select_from(User).where(User.last_seen_at >= active_since))
    totals["active_last_5_min"] = active_recently
    return render_template("admin/dashboard.html", view="home", totals=totals, users=recent)


@admin_web_bp.get("/users")
@guarded
def users():
    page = max(1, request.args.get("page", 1, type=int))
    q = request.args.get("q", "").strip()[:100]
    stmt = select(User)
    active_only = request.args.get("active") == "1"
    if active_only:
        stmt = stmt.where(User.last_seen_at >= datetime.now(timezone.utc) - __import__("datetime").timedelta(minutes=5))
    if q:
        stmt = stmt.where(User.email.ilike("%" + q.replace("%", "\\%").replace("_", "\\_") + "%", escape="\\"))
    data = db.paginate(stmt.order_by(User.created_at.desc()), page=page, per_page=25, error_out=False)
    return render_template("admin/dashboard.html", view="users", pagination=data, q=q, active_only=active_only)


@admin_web_bp.post("/users/<uuid:user_id>/update")
@guarded
def update_user(user_id):
    verify_csrf()
    actor = current_admin()
    target = db.session.get(User, user_id)
    if not target:
        abort(404)
    action = request.form.get("action", "")
    if action not in {"activate", "deactivate", "make_member", "make_umkm"}:
        abort(400)
    if actor.id == target.id or target.is_admin:
        abort(403, "Admin accounts cannot be modified from this screen")
    if action == "activate":
        target.is_active = True
    elif action == "deactivate":
        target.is_active = False
    elif action == "make_member":
        target.role = User.ROLE_MEMBER
    elif action == "make_umkm":
        target.role = User.ROLE_UMKM
    # All existing JWTs are revoked via the existing session_version verification callback.
    target.session_version = (target.session_version or 0) + 1
    log_admin_action(actor, action, target.id)
    db.session.commit()
    flash("Account updated successfully.", "success")
    return redirect(url_for("admin_web.users", q=request.form.get("q", "")))


def log_admin_action(actor, action, target_id):
    from app.models.admin_audit_log import AdminAuditLog
    db.session.add(AdminAuditLog(admin_user_id=actor.id, action=action,
                                 target_id=target_id))


@admin_web_bp.get("/applications")
@guarded
def applications():
    rows = db.session.scalars(select(UmkmApplication).order_by(UmkmApplication.created_at.desc()).limit(100)).all()
    return render_template("admin/dashboard.html", view="applications", applications=rows)


@admin_web_bp.post("/applications/<uuid:application_id>/review")
@guarded
def review_application(application_id):
    verify_csrf()
    actor = current_admin()
    entry = db.session.get(UmkmApplication, application_id)
    if not entry:
        abort(404)
    decision = request.form.get("decision")
    if decision not in {"approved", "rejected"} or entry.status != "pending":
        abort(400)
    applicant = db.session.get(User, entry.user_id)
    if decision == "approved":
        if not applicant or not applicant.is_active or applicant.role != User.ROLE_MEMBER or applicant.id == actor.id:
            abort(409, "Applicant is not eligible")
        applicant.role = User.ROLE_UMKM
        applicant.session_version = (applicant.session_version or 0) + 1
    entry.status = decision
    entry.reviewed_by = actor.id
    entry.reviewed_at = datetime.now(timezone.utc)
    entry.rejection_reason = (request.form.get("reason", "")[:500] or None) if decision == "rejected" else None
    log_admin_action(actor, "umkm_" + decision, entry.user_id)
    db.session.commit()
    flash("Application reviewed.", "success")
    return redirect(url_for("admin_web.applications"))


@admin_web_bp.get("/database")
@guarded
def database():
    """Read-only, allowlisted, paginated table inspector; never executes supplied SQL."""
    table_name = request.args.get("table", "users")
    if table_name not in READABLE_TABLES:
        abort(400)
    table = db.metadata.tables.get(table_name)
    if table is None:
        abort(404)
    columns = [c for c in table.columns if c.name.lower() not in REDACTED_COLUMNS
               and not any(word in c.name.lower() for word in ("secret", "password", "token", "hash", "code"))]
    # Prevent accidental disclosure of third-party genealogy or account information.
    if table_name in {"users", "people", "relationships", "relationship_requests", "community_posts"}:
        columns = [c for c in columns if c.name in {"id", "role", "is_active", "is_email_verified", "created_at", "updated_at", "status", "user_id", "type"}]
    # Restrict all other tables to operational fields, not free-form genealogical narratives.
    else:
        columns = [c for c in columns if c.name in {
            "id", "user_id", "seller_user_id", "business_name", "business_category", "name", "category",
            "price", "is_active", "status", "created_at", "updated_at", "reviewed_at", "title", "type"}]
    page = min(1000, max(1, request.args.get("page", 1, type=int)))
    rows = db.session.execute(select(*columns).select_from(table).limit(30).offset((page-1)*30)).all() if columns else []
    return render_template("admin/dashboard.html", view="database", tables=sorted(READABLE_TABLES),
                           selected_table=table_name, columns=[c.name for c in columns], rows=rows, page=page)


@admin_web_bp.get("/audit")
@guarded
def audit():
    from app.models.admin_audit_log import AdminAuditLog
    rows = db.session.scalars(select(AdminAuditLog).order_by(AdminAuditLog.created_at.desc()).limit(100)).all()
    return render_template("admin/dashboard.html", view="audit", logs=rows)


@admin_web_bp.get("/products")
@guarded
def products():
    pagination = db.paginate(select(Product).order_by(Product.created_at.desc()),
                             page=max(1, request.args.get("page", 1, type=int)), per_page=30, error_out=False)
    return render_template("admin/dashboard.html", view="products", pagination=pagination)


@admin_web_bp.post("/products/<uuid:product_id>/visibility")
@guarded
def product_visibility(product_id):
    verify_csrf()
    product = db.session.get(Product, product_id)
    if product is None:
        abort(404)
    product.is_active = not product.is_active
    log_admin_action(current_admin(), "product_enable" if product.is_active else "product_disable", product.id)
    db.session.commit()
    flash("Product visibility updated.", "success")
    return redirect(url_for("admin_web.products"))


@admin_web_bp.get("/culture")
@guarded
def culture():
    pagination = db.paginate(select(CultureContent).order_by(CultureContent.created_at.desc()),
                             page=max(1, request.args.get("page", 1, type=int)), per_page=30, error_out=False)
    return render_template("admin/dashboard.html", view="culture", pagination=pagination)


@admin_web_bp.post("/culture/<uuid:content_id>/visibility")
@guarded
def culture_visibility(content_id):
    verify_csrf()
    content = db.session.get(CultureContent, content_id)
    if content is None:
        abort(404)
    content.is_published = not content.is_published
    log_admin_action(current_admin(), "culture_publish" if content.is_published else "culture_unpublish", content.id)
    db.session.commit()
    flash("Culture visibility updated.", "success")
    return redirect(url_for("admin_web.culture"))


@admin_web_bp.post('/users/<uuid:user_id>/support-code')
@guarded
@limiter.limit('10 per hour')
def support_code(user_id):
    from datetime import timedelta
    from app.routes.support_access import enabled, _hash, utcnow, support_authorized
    from app.models.support_session import SupportSession
    verify_csrf()
    actor = current_admin()
    target = db.session.get(User, user_id)
    if not enabled() or actor.role != User.ROLE_SUPER_ADMIN:
        abort(403, 'Support access is disabled or requires a super administrator')
    if not target or not target.is_active or not target.is_email_verified or not support_authorized(target):
        abort(403, 'Account is not eligible for a support session')
    code = secrets.token_hex(12).upper()
    entry = SupportSession(admin_user_id=actor.id, target_user_id=target.id, code_hash=_hash(code), code_expires_at=utcnow() + timedelta(minutes=5))
    db.session.add(entry)
    log_admin_action(actor, 'support_code_created', target.id)
    db.session.commit()
    return render_template('admin/support_code.html', code=code, target=target)


@admin_web_bp.post('/support/<uuid:session_id>/revoke')
@guarded
def revoke_support(session_id):
    from app.models.support_session import SupportSession
    from app.routes.support_access import utcnow
    verify_csrf()
    actor = current_admin()
    if actor.role != User.ROLE_SUPER_ADMIN:
        abort(403)
    entry = db.session.get(SupportSession, session_id)
    if not entry:
        abort(404)
    entry.revoked_at = utcnow()
    log_admin_action(actor, 'support_session_revoked', entry.target_user_id)
    db.session.commit()
    return redirect(url_for('admin_web.support_sessions'))


@admin_web_bp.get('/support')
@guarded
def support_sessions():
    from app.models.support_session import SupportSession
    if current_admin().role != User.ROLE_SUPER_ADMIN:
        abort(403)
    entries = db.session.scalars(select(SupportSession).order_by(SupportSession.created_at.desc()).limit(50)).all()
    return render_template('admin/dashboard.html', view='support', support_sessions=entries)
