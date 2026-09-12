from uuid import UUID

from flask import (
    Blueprint,
    current_app,
    jsonify,
)

from flask_jwt_extended import (
    get_jwt_identity,
    jwt_required,
)

from app.extensions import db

from app.models import (
    User,
)


account_bp = Blueprint(
    "account",
    __name__,
)


def get_current_user():
    user_id = get_jwt_identity()

    try:
        user_uuid = UUID(
            str(user_id)
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


@account_bp.route(
    "",
    methods=["DELETE"],
)
@jwt_required()
def delete_account():
    user = get_current_user()

    if not user:
        return jsonify({
            "message": (
                "Invalid token identity"
            )
        }), 401

    #
    # Prevent accidental removal of
    # administrative accounts.
    #
    if user.is_admin:
        return jsonify({
            "message": (
                "Admin accounts cannot "
                "be deleted through the app"
            )
        }), 403

    person = user.person

    old_photo_url = None

    if person:
        old_photo_url = (
            person.photo_url
        )

        #
        # Preserve the genealogy node,
        # but remove account-specific
        # private information.
        #
        person.user_id = None

        person.nik = None

        person.photo_url = None

        person.claim_code_hash = None

        person.claim_code_expires_at = (
            None
        )

    try:
        db.session.delete(
            user
        )

        db.session.commit()

    except Exception as error:
        db.session.rollback()

        current_app.logger.exception(
            "Account deletion failed"
        )

        response = {
            "message": (
                "Failed to delete account"
            )
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

    #
    # Delete local profile image only
    # after DB deletion succeeds.
    #
    if old_photo_url:
        try:
            from app.routes.profile import (
                delete_local_profile_photo,
            )

            delete_local_profile_photo(
                old_photo_url
            )

        except Exception:
            current_app.logger.exception(
                "Account deleted, but "
                "profile photo cleanup failed"
            )

    return jsonify({
        "message": (
            "Account deleted successfully"
        ),

        "family_profile_preserved": (
            person is not None
        ),
    }), 200