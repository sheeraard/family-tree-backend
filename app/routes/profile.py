from datetime import date
from io import BytesIO
from pathlib import Path
from uuid import UUID, uuid4

from flask import (
    Blueprint,
    current_app,
    jsonify,
    request,
    send_from_directory,
)
from flask_jwt_extended import (
    get_jwt_identity,
    jwt_required,
)
from PIL import (
    Image,
    ImageOps,
    UnidentifiedImageError,
)

from app.extensions import (
    db,
    limiter,
)
from app.models import (
    Person,
    User,
)


profile_bp = Blueprint(
    "profile",
    __name__,
)


MAX_PROFILE_PHOTO_BYTES = (
    5
    * 1024
    * 1024
)

MAX_PROFILE_PHOTO_DIMENSION = (
    1600
)

PROFILE_PHOTO_URL_PREFIX = (
    "/api/profile/photos/"
)


def server_error_response(
    message,
    error,
):
    response = {
        "message": message,
    }

    if current_app.config[
        "DEBUG"
    ]:
        response[
            "error"
        ] = str(
            error
        )

    return jsonify(
        response
    ), 500


def get_current_user():
    user_id = (
        get_jwt_identity()
    )

    try:
        user_uuid = UUID(
            str(
                user_id
            )
        )

    except (
        ValueError,
        TypeError,
    ):
        return None

    return db.session.get(
        User,
        user_uuid,
    )


def get_profile_photo_directory():
    directory = (
        Path(
            current_app.root_path
        ).parent
        / "uploads"
        / "profile_photos"
    )

    directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    return directory


def serialize_profile(
    user,
    person,
):
    return {
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
            "nik": (
                person.nik
            ),
            "photo_url": (
                person.photo_url
            ),
        },
    }


def delete_local_profile_photo(
    photo_url,
):
    if not photo_url:
        return

    if not photo_url.startswith(
        PROFILE_PHOTO_URL_PREFIX
    ):
        return

    filename = photo_url[
        len(
            PROFILE_PHOTO_URL_PREFIX
        ):
    ]

    if (
        not filename
        or Path(
            filename
        ).name
        != filename
    ):
        return

    path = (
        get_profile_photo_directory()
        / filename
    )

    try:
        path.unlink(
            missing_ok=True
        )

    except OSError:
        current_app.logger.warning(
            (
                "Could not delete old "
                "profile photo: %s"
            ),
            path,
        )


@profile_bp.route(
    "/me",
    methods=["GET"],
)
@jwt_required()
def get_profile():
    user = get_current_user()

    if not user:
        return jsonify({
            "message": (
                "Invalid token identity"
            )
        }), 401

    person = user.person

    if not person:
        return jsonify({
            "message": (
                "Person profile not found"
            )
        }), 404

    return jsonify(
        serialize_profile(
            user,
            person,
        )
    ), 200


@profile_bp.route(
    "/me",
    methods=["PATCH"],
)
@jwt_required()
def update_profile():
    user = get_current_user()

    if not user:
        return jsonify({
            "message": (
                "Invalid token identity"
            )
        }), 401

    person = user.person

    if not person:
        return jsonify({
            "message": (
                "Person profile not found"
            )
        }), 404

    data = request.get_json(
        silent=True
    )

    if not data:
        return jsonify({
            "message": (
                "Request body must be JSON"
            )
        }), 400

    if "full_name" in data:
        full_name = str(
            data[
                "full_name"
            ]
        ).strip()

        if not full_name:
            return jsonify({
                "message": (
                    "Full name cannot "
                    "be empty"
                )
            }), 400

        person.full_name = (
            full_name
        )

    if "phone" in data:
        phone_raw = (
            data[
                "phone"
            ]
        )

        if (
            phone_raw is None
            or str(
                phone_raw
            ).strip()
            == ""
        ):
            phone = None

        else:
            phone = str(
                phone_raw
            ).strip()

        if phone != user.phone:
            existing_phone = (
                db.session.scalar(
                    db.select(
                        User
                    ).where(
                        User.phone
                        == phone
                    )
                )
                if phone
                else None
            )

            if existing_phone:
                return jsonify({
                    "message": (
                        "Phone number is "
                        "already registered"
                    )
                }), 409

        user.phone = phone

    if "gender" in data:
        gender_raw = (
            data[
                "gender"
            ]
        )

        if (
            gender_raw is None
            or str(
                gender_raw
            ).strip()
            == ""
        ):
            person.gender = None

        else:
            person.gender = (
                str(
                    gender_raw
                )
                .strip()
                .lower()
            )

    if "nik" in data:
        nik_raw = (
            data[
                "nik"
            ]
        )

        if (
            nik_raw is None
            or str(
                nik_raw
            ).strip()
            == ""
        ):
            nik = None

        else:
            nik = str(
                nik_raw
            ).strip()

            if len(
                nik
            ) != 16:
                return jsonify({
                    "message": (
                        "NIK must contain "
                        "16 digits"
                    )
                }), 400

            if not nik.isdigit():
                return jsonify({
                    "message": (
                        "NIK must contain "
                        "only numbers"
                    )
                }), 400

            if nik != person.nik:
                existing_nik = (
                    db.session.scalar(
                        db.select(
                            Person
                        ).where(
                            Person.nik
                            == nik,

                            Person.id
                            != person.id,
                        )
                    )
                )

                if existing_nik:
                    return jsonify({
                        "message": (
                            "NIK is already "
                            "registered"
                        )
                    }), 409

        person.nik = nik

    if "birth_date" in data:
        birth_date_raw = (
            data[
                "birth_date"
            ]
        )

        if (
            birth_date_raw
            in (
                "",
                None,
            )
        ):
            person.birth_date = None

        else:
            try:
                person.birth_date = (
                    date.fromisoformat(
                        str(
                            birth_date_raw
                        )
                    )
                )

            except ValueError:
                return jsonify({
                    "message": (
                        "birth_date must use "
                        "YYYY-MM-DD format"
                    )
                }), 400

    try:
        db.session.commit()

        response = (
            serialize_profile(
                user,
                person,
            )
        )

        response[
            "message"
        ] = (
            "Profile updated "
            "successfully"
        )

        return jsonify(
            response
        ), 200

    except Exception as error:
        db.session.rollback()

        return server_error_response(
            "Failed to update profile",
            error,
        )


@profile_bp.route(
    "/me/photo",
    methods=["POST"],
)
@jwt_required()
@limiter.limit(
    "10 per hour"
)
def upload_profile_photo():
    user = get_current_user()

    if not user:
        return jsonify({
            "message": (
                "Invalid token identity"
            )
        }), 401

    person = user.person

    if not person:
        return jsonify({
            "message": (
                "Person profile not found"
            )
        }), 404

    uploaded_file = (
        request.files.get(
            "photo"
        )
    )

    if (
        uploaded_file is None
        or not uploaded_file.filename
    ):
        return jsonify({
            "message": (
                "Profile photo is required"
            )
        }), 400

    raw_bytes = (
        uploaded_file
        .stream
        .read(
            MAX_PROFILE_PHOTO_BYTES
            + 1
        )
    )

    if not raw_bytes:
        return jsonify({
            "message": (
                "Profile photo is empty"
            )
        }), 400

    if (
        len(
            raw_bytes
        )
        > MAX_PROFILE_PHOTO_BYTES
    ):
        return jsonify({
            "message": (
                "Profile photo must be "
                "5 MB or smaller"
            )
        }), 413

    try:
        image = Image.open(
            BytesIO(
                raw_bytes
            )
        )

        image.verify()

        image = Image.open(
            BytesIO(
                raw_bytes
            )
        )

        image = (
            ImageOps.exif_transpose(
                image
            )
        )

        image.thumbnail(
            (
                MAX_PROFILE_PHOTO_DIMENSION,
                MAX_PROFILE_PHOTO_DIMENSION,
            )
        )

        if image.mode not in (
            "RGB",
            "L",
        ):
            image = image.convert(
                "RGB"
            )

        elif image.mode == "L":
            image = image.convert(
                "RGB"
            )

    except (
        UnidentifiedImageError,
        OSError,
        ValueError,
    ):
        return jsonify({
            "message": (
                "Uploaded file is not "
                "a valid image"
            )
        }), 400

    filename = (
        f"{person.id}_"
        f"{uuid4().hex}.jpg"
    )

    photo_directory = (
        get_profile_photo_directory()
    )

    output_path = (
        photo_directory
        / filename
    )

    try:
        image.save(
            output_path,
            format="JPEG",
            quality=88,
            optimize=True,
        )

        old_photo_url = (
            person.photo_url
        )

        person.photo_url = (
            f"{PROFILE_PHOTO_URL_PREFIX}"
            f"{filename}"
        )

        db.session.commit()

        delete_local_profile_photo(
            old_photo_url
        )

        response = (
            serialize_profile(
                user,
                person,
            )
        )

        response[
            "message"
        ] = (
            "Profile photo updated "
            "successfully"
        )

        return jsonify(
            response
        ), 200

    except Exception as error:
        db.session.rollback()

        try:
            output_path.unlink(
                missing_ok=True
            )

        except OSError:
            pass

        return server_error_response(
            (
                "Failed to update "
                "profile photo"
            ),
            error,
        )


@profile_bp.route(
    "/me/photo",
    methods=["DELETE"],
)
@jwt_required()
def delete_profile_photo():
    user = get_current_user()

    if not user:
        return jsonify({
            "message": (
                "Invalid token identity"
            )
        }), 401

    person = user.person

    if not person:
        return jsonify({
            "message": (
                "Person profile not found"
            )
        }), 404

    old_photo_url = (
        person.photo_url
    )

    if not old_photo_url:
        response = (
            serialize_profile(
                user,
                person,
            )
        )

        response[
            "message"
        ] = (
            "Profile photo is "
            "already empty"
        )

        return jsonify(
            response
        ), 200

    try:
        person.photo_url = None

        db.session.commit()

        delete_local_profile_photo(
            old_photo_url
        )

        response = (
            serialize_profile(
                user,
                person,
            )
        )

        response[
            "message"
        ] = (
            "Profile photo removed "
            "successfully"
        )

        return jsonify(
            response
        ), 200

    except Exception as error:
        db.session.rollback()

        return server_error_response(
            (
                "Failed to remove "
                "profile photo"
            ),
            error,
        )


@profile_bp.route(
    "/photos/<path:filename>",
    methods=["GET"],
)
def serve_profile_photo(
    filename,
):
    if (
        Path(
            filename
        ).name
        != filename
    ):
        return jsonify({
            "message": (
                "Invalid photo path"
            )
        }), 404

    return send_from_directory(
        get_profile_photo_directory(),
        filename,
        max_age=86400,
    )