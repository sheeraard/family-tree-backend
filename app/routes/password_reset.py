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

from werkzeug.security import (
    generate_password_hash,
)

from app.extensions import db

from app.models.user import (
    User,
)

from app.models.password_reset_code import (
    PasswordResetCode,
)

from app.services.email_service import (
    send_password_reset_code,
)


password_reset_bp = Blueprint(
    "password_reset",
    __name__,
)


RESET_CODE_LIFETIME_MINUTES = 15

MAX_RESET_ATTEMPTS = 5


def _generate_code():
    return (
        f"{secrets.randbelow(1000000):06d}"
    )


def _normalize_email(
    value,
):
    return str(
        value or ""
    ).strip().lower()


def _generic_reset_response():
    return {
        "message": (
            "If an account exists for "
            "that email, a password "
            "reset code will be sent."
        )
    }


@password_reset_bp.post(
    "/request"
)
def request_password_reset():
    data = (
        request.get_json(
            silent=True
        )
        or {}
    )

    email = _normalize_email(
        data.get("email")
    )

    if not email:
        return jsonify({
            "message": (
                "Email is required."
            )
        }), 400

    generic_response = (
        _generic_reset_response()
    )

    user = db.session.scalar(
        db.select(
            User
        ).where(
            User.email == email
        )
    )

    if (
        user is None
        or
        not user.is_active
    ):
        return jsonify(
            generic_response
        ), 200

    now = datetime.now(
        timezone.utc
    )

    active_codes = (
        db.session.scalars(
            db.select(
                PasswordResetCode
            ).where(
                PasswordResetCode
                    .user_id
                == user.id,

                PasswordResetCode
                    .used_at
                .is_(None),
            )
        )
        .all()
    )

    for reset_code in active_codes:
        reset_code.used_at = now

    code = _generate_code()

    reset_code = (
        PasswordResetCode(
            user_id=user.id,
            expires_at=(
                now
                + timedelta(
                    minutes=(
                        RESET_CODE_LIFETIME_MINUTES
                    )
                )
            ),
        )
    )

    reset_code.set_code(
        code
    )

    db.session.add(
        reset_code
    )

    try:
        db.session.commit()

    except Exception:
        db.session.rollback()

        current_app.logger.exception(
            "Unable to create "
            "password reset code"
        )

        return jsonify(
            generic_response
        ), 200

    try:
        send_password_reset_code(
            recipient=user.email,
            code=code,
        )

    except Exception:
        current_app.logger.exception(
            "Unable to send "
            "password reset email"
        )

        try:
            reset_code.used_at = (
                datetime.now(
                    timezone.utc
                )
            )

            db.session.commit()

        except Exception:
            db.session.rollback()

            current_app.logger.exception(
                "Unable to invalidate "
                "failed reset code"
            )

    return jsonify(
        generic_response
    ), 200


@password_reset_bp.post(
    "/confirm"
)
def confirm_password_reset():
    data = (
        request.get_json(
            silent=True
        )
        or {}
    )

    email = _normalize_email(
        data.get("email")
    )

    code = str(
        data.get(
            "code",
            "",
        )
    ).strip()

    new_password = str(
        data.get(
            "new_password",
            "",
        )
    )

    if not email:
        return jsonify({
            "message": (
                "Email is required."
            )
        }), 400

    if (
        len(code) != 6
        or
        not code.isdigit()
    ):
        return jsonify({
            "message": (
                "Reset code must "
                "contain 6 digits."
            )
        }), 400

    if len(new_password) < 8:
        return jsonify({
            "message": (
                "Password must be at "
                "least 8 characters."
            )
        }), 400

    user = db.session.scalar(
        db.select(
            User
        ).where(
            User.email == email
        )
    )

    if (
        user is None
        or
        not user.is_active
    ):
        return jsonify({
            "message": (
                "Invalid or expired "
                "reset code."
            )
        }), 400

    reset_code = (
        db.session.scalar(
            db.select(
                PasswordResetCode
            )
            .where(
                PasswordResetCode
                    .user_id
                == user.id,

                PasswordResetCode
                    .used_at
                .is_(None),
            )
            .order_by(
                PasswordResetCode
                    .created_at
                .desc()
            )
        )
    )

    if (
        reset_code is None
        or
        not reset_code.usable
    ):
        return jsonify({
            "message": (
                "Invalid or expired "
                "reset code."
            )
        }), 400

    if not reset_code.check_code(
        code
    ):
        reset_code.attempts += 1

        if (
            reset_code.attempts
            >= MAX_RESET_ATTEMPTS
        ):
            reset_code.used_at = (
                datetime.now(
                    timezone.utc
                )
            )

        db.session.commit()

        return jsonify({
            "message": (
                "Invalid or expired "
                "reset code."
            )
        }), 400

    user.password_hash = (
        generate_password_hash(
            new_password,
            method="pbkdf2:sha256",
        )
    )

    user.session_version = (
        user.session_version
        + 1
    )

    reset_code.used_at = (
        datetime.now(
            timezone.utc
        )
    )

    #
    # Invalidate every other outstanding
    # password reset code belonging to
    # this account.
    #

    other_codes = (
        db.session.scalars(
            db.select(
                PasswordResetCode
            ).where(
                PasswordResetCode
                    .user_id
                == user.id,

                PasswordResetCode
                    .id
                != reset_code.id,

                PasswordResetCode
                    .used_at
                .is_(None),
            )
        )
        .all()
    )

    for other_code in other_codes:
        other_code.used_at = (
            reset_code.used_at
        )

    db.session.commit()

    return jsonify({
        "message": (
            "Password has been reset "
            "successfully."
        )
    }), 200