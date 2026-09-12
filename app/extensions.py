from uuid import UUID

from flask import (
    jsonify,
    request,
)

from flask_jwt_extended import (
    JWTManager,
)

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy


def get_rate_limit_address():
    railway_ip = (
        request.headers.get(
            "X-Real-IP",
            "",
        )
        .strip()
    )

    if railway_ip:
        return railway_ip

    return get_remote_address()


db = SQLAlchemy()

migrate = Migrate()

jwt = JWTManager()


@jwt.additional_claims_loader
def add_session_version(
    identity,
):
    from app.models.user import (
        User,
    )

    try:
        user_uuid = UUID(
            str(identity)
        )

    except (
        ValueError,
        TypeError,
    ):
        return {
            "session_version": -1
        }

    user = db.session.get(
        User,
        user_uuid,
    )

    if user is None:
        return {
            "session_version": -1
        }

    return {
        "session_version": (
            user.session_version
        )
    }


@jwt.token_verification_loader
def verify_token_session(
    jwt_header,
    jwt_payload,
):
    del jwt_header

    from app.models.user import (
        User,
    )

    identity = jwt_payload.get(
        "sub"
    )

    token_session_version = (
        jwt_payload.get(
            "session_version"
        )
    )

    try:
        user_uuid = UUID(
            str(identity)
        )

    except (
        ValueError,
        TypeError,
    ):
        return False

    user = db.session.get(
        User,
        user_uuid,
    )

    if user is None:
        return False

    if not user.is_active:
        return False

    if not user.is_email_verified:
        return False

    return (
        token_session_version
        == user.session_version
    )


@jwt.token_verification_failed_loader
def token_verification_failed(
    jwt_header,
    jwt_payload,
):
    del jwt_header
    del jwt_payload

    return jsonify({
        "message": (
            "Session is no longer valid. "
            "Please log in again."
        )
    }), 401


limiter = Limiter(
    key_func=get_rate_limit_address,
    default_limits=[
        "300 per minute",
        "5000 per hour",
    ],
)