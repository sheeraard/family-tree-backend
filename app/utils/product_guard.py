from uuid import UUID

from flask import (
    jsonify,
    request,
)

from flask_jwt_extended import (
    get_jwt_identity,
    verify_jwt_in_request,
)

from app.extensions import db
from app.models import User


WRITE_METHODS = {
    "POST",
    "PATCH",
    "PUT",
    "DELETE",
}


def register_product_guard(
    app,
):
    @app.before_request
    def product_permission_guard():
        if not request.path.startswith(
            "/api/products"
        ):
            return None

        if (
            request.method
            not in WRITE_METHODS
        ):
            return None

        try:
            verify_jwt_in_request()

        except Exception:
            return jsonify({
                "message": (
                    "Authentication required"
                )
            }), 401

        user_id = get_jwt_identity()

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

        if user is None:
            return jsonify({
                "message": (
                    "Invalid user"
                )
            }), 401

        if not user.is_active:
            return jsonify({
                "message": (
                    "Account is inactive"
                )
            }), 403

        if not user.can_sell_products:
            return jsonify({
                "message": (
                    "Only approved UMKM "
                    "accounts can manage "
                    "products."
                ),
                "role": user.role,
            }), 403

        return None