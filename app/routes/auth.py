import hashlib

from datetime import (
    date,
    datetime,
    timezone,
)
from uuid import UUID

from flask import (
    Blueprint,
    current_app,
    jsonify,
    request,
)

from flask_jwt_extended import (
    create_access_token,
    get_jwt_identity,
    jwt_required,
)

from werkzeug.security import (
    check_password_hash,
    generate_password_hash,
)

from app.extensions import db
from app.models import (
    Person,
    User,
)


auth_bp = Blueprint(
    "auth",
    __name__,
)


def server_error_response(
    message,
    error,
):
    response = {
        "message": message
    }

    if current_app.config[
        "DEBUG"
    ]:
        response["error"] = str(
            error
        )

    return jsonify(
        response
    ), 500


def parse_birth_date(
    value,
):
    if not value:
        return None

    try:
        return date.fromisoformat(
            str(value)
        )

    except ValueError:
        return None


def hash_claim_code(
    claim_code,
):
    return hashlib.sha256(
        claim_code.encode(
            "utf-8"
        )
    ).hexdigest()


@auth_bp.route(
    "/register",
    methods=["POST"],
)
def register():
    data = request.get_json(
        silent=True
    )

    if not data:
        return jsonify({
            "message": (
                "Request body must be JSON"
            )
        }), 400

    email = str(
        data.get(
            "email",
            "",
        )
    ).strip().lower()

    password = str(
        data.get(
            "password",
            "",
        )
    )

    full_name = str(
        data.get(
            "full_name",
            "",
        )
    ).strip()

    phone_raw = data.get(
        "phone"
    )

    gender_raw = data.get(
        "gender"
    )

    nik_raw = data.get(
        "nik"
    )

    birth_date_raw = data.get(
        "birth_date"
    )

    claim_code_raw = data.get(
        "claim_code"
    )

    phone = (
        str(phone_raw).strip()
        if (
            phone_raw is not None
            and str(
                phone_raw
            ).strip()
        )
        else None
    )

    gender = (
        str(gender_raw)
        .strip()
        .lower()
        if (
            gender_raw is not None
            and str(
                gender_raw
            ).strip()
        )
        else None
    )

    nik = (
        str(nik_raw).strip()
        if (
            nik_raw is not None
            and str(
                nik_raw
            ).strip()
        )
        else None
    )

    claim_code = (
        str(claim_code_raw)
        .strip()
        if (
            claim_code_raw is not None
            and str(
                claim_code_raw
            ).strip()
        )
        else None
    )

    if not email:
        return jsonify({
            "message": (
                "Email is required"
            )
        }), 400

    if len(password) < 8:
        return jsonify({
            "message": (
                "Password must be at least "
                "8 characters"
            )
        }), 400

    existing_user = db.session.scalar(
        db.select(User).where(
            User.email == email
        )
    )

    if existing_user:
        return jsonify({
            "message": (
                "Email already registered"
            )
        }), 409

    if phone:
        existing_phone = (
            db.session.scalar(
                db.select(User).where(
                    User.phone == phone
                )
            )
        )

        if existing_phone:
            return jsonify({
                "message": (
                    "Phone number already "
                    "registered"
                )
            }), 409

    if nik:
        if (
            not nik.isdigit()
            or len(nik) != 16
        ):
            return jsonify({
                "message": (
                    "NIK must contain "
                    "16 digits"
                )
            }), 400

    birth_date = None

    if birth_date_raw:
        birth_date = (
            parse_birth_date(
                birth_date_raw
            )
        )

        if birth_date is None:
            return jsonify({
                "message": (
                    "birth_date must use "
                    "YYYY-MM-DD format"
                )
            }), 400

    try:
        claimed_person = None

        if claim_code:
            submitted_hash = (
                hash_claim_code(
                    claim_code
                )
            )

            claimed_person = (
                db.session.scalar(
                    db.select(
                        Person
                    ).where(
                        Person
                        .claim_code_hash
                        == submitted_hash
                    )
                )
            )

            if not claimed_person:
                return jsonify({
                    "message": (
                        "Invalid claim code"
                    )
                }), 400

            if (
                claimed_person.user_id
                is not None
            ):
                return jsonify({
                    "message": (
                        "This profile is "
                        "already claimed"
                    )
                }), 409

            expires_at = (
                claimed_person
                .claim_code_expires_at
            )

            if (
                expires_at is None
            ):
                return jsonify({
                    "message": (
                        "This claim code "
                        "has expired"
                    )
                }), 400

            now = datetime.now(
                timezone.utc
            )

            if (
                expires_at.tzinfo
                is None
            ):
                expires_at = (
                    expires_at.replace(
                        tzinfo=timezone.utc
                    )
                )

            if expires_at <= now:
                claimed_person.claim_code_hash = (
                    None
                )

                claimed_person.claim_code_expires_at = (
                    None
                )

                db.session.commit()

                return jsonify({
                    "message": (
                        "This claim code "
                        "has expired"
                    )
                }), 400

        if (
            not claim_code
            and not full_name
        ):
            return jsonify({
                "message": (
                    "Full name is required"
                )
            }), 400

        new_user = User(
            email=email,
            phone=phone,

            password_hash=(
                generate_password_hash(
                    password,
                    method=(
                        "pbkdf2:sha256"
                    ),
                )
            ),
        )

        db.session.add(
            new_user
        )

        db.session.flush()

        if claimed_person:
            claimed_person.user_id = (
                new_user.id
            )

            claimed_person.claim_code_hash = (
                None
            )

            claimed_person.claim_code_expires_at = (
                None
            )

            if birth_date is not None:
                claimed_person.birth_date = (
                    birth_date
                )

            if gender is not None:
                claimed_person.gender = (
                    gender
                )

            if nik is not None:
                existing_nik = (
                    db.session.scalar(
                        db.select(
                            Person
                        ).where(
                            Person.nik
                            == nik,

                            Person.id
                            != claimed_person.id,
                        )
                    )
                )

                if existing_nik:
                    db.session.rollback()

                    return jsonify({
                        "message": (
                            "NIK already "
                            "registered"
                        )
                    }), 409

                claimed_person.nik = (
                    nik
                )

            person = (
                claimed_person
            )

        else:
            if nik:
                existing_nik = (
                    db.session.scalar(
                        db.select(
                            Person
                        ).where(
                            Person.nik
                            == nik
                        )
                    )
                )

                if existing_nik:
                    db.session.rollback()

                    return jsonify({
                        "message": (
                            "NIK already "
                            "registered"
                        )
                    }), 409

            person = Person(
                user_id=(
                    new_user.id
                ),

                full_name=(
                    full_name
                ),

                birth_date=(
                    birth_date
                ),

                gender=(
                    gender
                ),

                nik=(
                    nik
                ),
            )

            db.session.add(
                person
            )

        db.session.commit()

        return jsonify({
            "message": (
                "Account registered "
                "successfully"
            ),

            "claimed_existing_profile": (
                claimed_person
                is not None
            ),

            "user": {
                "id": str(
                    new_user.id
                ),

                "email": (
                    new_user.email
                ),

                "phone": (
                    new_user.phone
                ),
            },

            "person": {
                "id": str(
                    person.id
                ),

                "full_name": (
                    person.full_name
                ),

                "birth_date": (
                    person.birth_date
                    .isoformat()
                    if person.birth_date
                    else None
                ),

                "gender": (
                    person.gender
                ),

                "has_account": True,
            },
        }), 201

    except Exception as error:
        db.session.rollback()

        return server_error_response(
            "Registration failed",
            error,
        )


@auth_bp.route(
    "/login",
    methods=["POST"],
)
def login():
    data = request.get_json(
        silent=True
    )

    if not data:
        return jsonify({
            "message": (
                "Request body must be JSON"
            )
        }), 400

    email = str(
        data.get(
            "email",
            "",
        )
    ).strip().lower()

    password = str(
        data.get(
            "password",
            "",
        )
    )

    user = db.session.scalar(
        db.select(User).where(
            User.email == email
        )
    )

    if (
        not user
        or not check_password_hash(
            user.password_hash,
            password,
        )
    ):
        return jsonify({
            "message": (
                "Invalid email or password"
            )
        }), 401

    if not user.is_active:
        return jsonify({
            "message": (
                "Account is inactive"
            )
        }), 403

    access_token = (
        create_access_token(
            identity=str(
                user.id
            )
        )
    )

    return jsonify({
        "access_token": (
            access_token
        ),

        "token_type": (
            "Bearer"
        ),

        "user": {
            "id": str(
                user.id
            ),

            "email": (
                user.email
            ),
        },
    }), 200


@auth_bp.route(
    "/me",
    methods=["GET"],
)
@jwt_required()
def me():
    user_id = (
        get_jwt_identity()
    )

    try:
        user_uuid = UUID(
            str(user_id)
        )

    except (
        ValueError,
        TypeError,
    ):
        return jsonify({
            "message": (
                "Invalid user"
            )
        }), 401

    user = db.session.get(
        User,
        user_uuid,
    )

    if not user:
        return jsonify({
            "message": (
                "User not found"
            )
        }), 404

    person = (
        user.person
    )

    return jsonify({
        "user": {
            "id": str(
                user.id
            ),

            "email": (
                user.email
            ),

            "phone": (
                user.phone
            ),

            "is_active": (
                user.is_active
            ),
        },

        "person": {
            "id": str(
                person.id
            ),

            "full_name": (
                person.full_name
            ),

            "birth_date": (
                person.birth_date
                .isoformat()
                if person.birth_date
                else None
            ),

            "gender": (
                person.gender
            ),

            "photo_url": (
                person.photo_url
            ),

        } if person else None,
    }), 200