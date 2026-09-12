from uuid import UUID

from flask import (
    Blueprint,
    jsonify,
    request,
)

from flask_jwt_extended import (
    get_jwt_identity,
    jwt_required,
)

from app.extensions import db
from app.models import (
    Product,
    User,
)


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


def _get_product(
    product_id,
):
    try:
        product_uuid = UUID(
            str(product_id)
        )

    except (
        ValueError,
        TypeError,
    ):
        return None, (
            jsonify({
                "message": (
                    "Invalid product ID"
                )
            }),
            400,
        )

    product = db.session.get(
        Product,
        product_uuid,
    )

    if product is None:
        return None, (
            jsonify({
                "message": (
                    "Product not found"
                )
            }),
            404,
        )

    return product, None


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

    if not user.is_active:
        return jsonify({
            "message": (
                "Account is inactive"
            )
        }), 403

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


@product_access_bp.patch(
    "/<product_id>/moderation"
)
@jwt_required()
def moderate_product(
    product_id,
):
    user = _current_user()

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

    if not user.is_admin:
        return jsonify({
            "message": (
                "Admin access required"
            )
        }), 403

    (
        product,
        error_response,
    ) = _get_product(
        product_id
    )

    if error_response:
        return error_response

    data = request.get_json(
        silent=True
    )

    if not data:
        return jsonify({
            "message": (
                "Request body "
                "must be JSON"
            )
        }), 400

    if "is_active" not in data:
        return jsonify({
            "message": (
                "is_active is required"
            )
        }), 400

    is_active = data.get(
        "is_active"
    )

    if not isinstance(
        is_active,
        bool,
    ):
        return jsonify({
            "message": (
                "is_active must be "
                "true or false"
            )
        }), 400

    try:
        product.is_active = (
            is_active
        )

        db.session.commit()

        return jsonify({
            "message": (
                "Product moderation "
                "updated"
            ),

            "product": {
                "id": str(
                    product.id
                ),

                "seller_user_id": str(
                    product
                    .seller_user_id
                ),

                "name": (
                    product.name
                ),

                "is_active": (
                    product.is_active
                ),
            },
        }), 200

    except Exception:
        db.session.rollback()

        raise