from flask import (
    Blueprint,
    jsonify,
)

from flask_jwt_extended import (
    get_jwt_identity,
    jwt_required,
)

from uuid import UUID

from app.extensions import db
from app.models import User


product_access_bp = Blueprint(
    "product_access",
    __name__,
)


def _current_user():
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


@product_access_bp.get(
    "/access"
)
@jwt_required()
def get_product_access():
    user = _current_user()

    if user is None:
        return jsonify({
            "message": (
                "Invalid user"
            )
        }), 401

    return jsonify({
        "role": user.role,

        "can_browse_products": True,

        "can_sell_products": (
            user.can_sell_products
        ),

        "can_moderate_products": (
            user.is_admin
        ),
    }), 200