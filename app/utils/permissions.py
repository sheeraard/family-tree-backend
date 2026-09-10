from functools import wraps
from uuid import UUID

from flask import jsonify

from flask_jwt_extended import (
    get_jwt_identity,
    jwt_required,
)

from app.extensions import db
from app.models.user import User


def _get_current_user():
    user_id = get_jwt_identity()

    if not user_id:
        return None

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


def roles_required(
    *allowed_roles,
):
    """
    Require the logged-in user to have
    one of the supplied roles.

    Example:

        @roles_required(
            "admin",
            "super_admin",
        )
        def route():
            ...
    """

    def decorator(
        function,
    ):
        @wraps(function)
        @jwt_required()
        def wrapper(
            *args,
            **kwargs,
        ):
            user = _get_current_user()

            if user is None:
                return jsonify({
                    "message": (
                        "User not found"
                    )
                }), 401

            if not user.is_active:
                return jsonify({
                    "message": (
                        "Account is inactive"
                    )
                }), 403

            if (
                user.role
                not in allowed_roles
            ):
                return jsonify({
                    "message": (
                        "You do not have "
                        "permission to perform "
                        "this action"
                    ),

                    "required_roles": list(
                        allowed_roles
                    ),

                    "current_role": (
                        user.role
                    ),
                }), 403

            return function(
                *args,
                **kwargs,
            )

        return wrapper

    return decorator


def admin_required(
    function,
):
    """
    Allow admin and super_admin.
    """

    @wraps(function)
    @jwt_required()
    def wrapper(
        *args,
        **kwargs,
    ):
        user = _get_current_user()

        if user is None:
            return jsonify({
                "message": (
                    "User not found"
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
                ),

                "current_role": (
                    user.role
                ),
            }), 403

        return function(
            *args,
            **kwargs,
        )

    return wrapper


def super_admin_required(
    function,
):
    """
    Allow super_admin only.
    """

    @wraps(function)
    @jwt_required()
    def wrapper(
        *args,
        **kwargs,
    ):
        user = _get_current_user()

        if user is None:
            return jsonify({
                "message": (
                    "User not found"
                )
            }), 401

        if not user.is_active:
            return jsonify({
                "message": (
                    "Account is inactive"
                )
            }), 403

        if not user.is_super_admin:
            return jsonify({
                "message": (
                    "Super admin access "
                    "required"
                ),

                "current_role": (
                    user.role
                ),
            }), 403

        return function(
            *args,
            **kwargs,
        )

    return wrapper


def umkm_required(
    function,
):
    """
    Allow approved UMKM, admin,
    and super_admin.
    """

    @wraps(function)
    @jwt_required()
    def wrapper(
        *args,
        **kwargs,
    ):
        user = _get_current_user()

        if user is None:
            return jsonify({
                "message": (
                    "User not found"
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
                    "Approved UMKM account "
                    "required"
                ),

                "current_role": (
                    user.role
                ),
            }), 403

        return function(
            *args,
            **kwargs,
        )

    return wrapper