import secrets

from datetime import (
    datetime,
    timedelta,
    timezone,
)

from flask import (
    Blueprint,
    current_app,
    jsonify,
    request,
)

from app.extensions import db
from app.models import (
    EmailVerificationCode,
    User,
)

from app.services.email_service import (
    send_email_verification_code,
)


email_verification_bp = Blueprint(
    "email_verification",
    __name__,
)


def _normalize_email(value):
    return str(
        value or ""
    ).strip().lower()


def _invalidate_unused_codes(
    user_id,
):
    codes = db.session.scalars(
        db.select(
            EmailVerificationCode
        ).where(
            EmailVerificationCode.user_id
            == user_id,

            EmailVerificationCode.used_at
            .is_(None),
        )
    ).all()

    now = datetime.now(
        timezone.utc
    )

    for code in codes:
        code.used_at = now


def issue_email_verification_code(
    user,
):
    if user.is_email_verified:
        return None

    _invalidate_unused_codes(
        user.id
    )

    code = (
        f"{secrets.randbelow(1000000):06d}"
    )

    verification_code = (
        EmailVerificationCode(
            user_id=user.id,

            code_hash=(
                EmailVerificationCode
                .hash_code(code)
            ),

            expires_at=(
                datetime.now(
                    timezone.utc
                )
                + timedelta(
                    minutes=15
                )
            ),
        )
    )

    db.session.add(
        verification_code
    )

    db.session.commit()

    try:
        send_email_verification_code(
            recipient=user.email,
            code=code,
        )

    except Exception:
        current_app.logger.exception(
            "Unable to send email "
            "verification code"
        )

        verification_code.used_at = (
            datetime.now(
                timezone.utc
            )
        )

        db.session.commit()

        raise

    return verification_code


@email_verification_bp.route(
    "/request",
    methods=["POST"],
)
def request_email_verification():
    data = request.get_json(
        silent=True
    ) or {}

    email = _normalize_email(
        data.get("email")
    )

    if not email:
        return jsonify({
            "message": (
                "Email is required"
            )
        }), 400

    user = db.session.scalar(
        db.select(User).where(
            User.email == email
        )
    )

    # Generic response prevents
    # account enumeration.
    generic_response = {
        "message": (
            "If the account exists and "
            "requires verification, a "
            "verification code has been sent."
        )
    }

    if (
        not user
        or not user.is_active
        or user.is_email_verified
    ):
        return jsonify(
            generic_response
        ), 200

    try:
        issue_email_verification_code(
            user
        )

    except Exception:
        # Do not expose provider details.
        return jsonify(
            generic_response
        ), 200

    return jsonify(
        generic_response
    ), 200


@email_verification_bp.route(
    "/confirm",
    methods=["POST"],
)
def confirm_email_verification():
    data = request.get_json(
        silent=True
    ) or {}

    email = _normalize_email(
        data.get("email")
    )

    code = str(
        data.get(
            "code",
            "",
        )
    ).strip()

    if not email:
        return jsonify({
            "message": (
                "Email is required"
            )
        }), 400

    if (
        len(code) != 6
        or not code.isdigit()
    ):
        return jsonify({
            "message": (
                "Verification code must "
                "contain 6 digits"
            )
        }), 400

    user = db.session.scalar(
        db.select(User).where(
            User.email == email
        )
    )

    if not user:
        return jsonify({
            "message": (
                "Invalid verification code"
            )
        }), 400

    if user.is_email_verified:
        return jsonify({
            "message": (
                "Email is already verified"
            ),
            "is_email_verified": True,
        }), 200

    verification_code = (
        db.session.scalar(
            db.select(
                EmailVerificationCode
            )
            .where(
                EmailVerificationCode
                .user_id
                == user.id,

                EmailVerificationCode
                .used_at
                .is_(None),
            )
            .order_by(
                EmailVerificationCode
                .created_at
                .desc()
            )
        )
    )

    if (
        not verification_code
        or not verification_code
            .is_usable
    ):
        return jsonify({
            "message": (
                "Verification code is "
                "invalid or expired"
            )
        }), 400

    if not verification_code.matches_code(
        code
    ):
        verification_code.attempts += 1

        db.session.commit()

        return jsonify({
            "message": (
                "Invalid verification code"
            )
        }), 400

    now = datetime.now(
        timezone.utc
    )

    verification_code.used_at = now

    user.is_email_verified = True
    user.email_verified_at = now

    _invalidate_unused_codes(
        user.id
    )

    db.session.commit()

    return jsonify({
        "message": (
            "Email verified successfully"
        ),
        "is_email_verified": True,
    }), 200