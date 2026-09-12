from datetime import datetime, timezone
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
    UmkmApplication,
    User,
)

from app.utils.permissions import (
    admin_required,
)


umkm_bp = Blueprint(
    "umkm",
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


def _clean_optional(
    value,
):
    if value is None:
        return None

    value = str(
        value
    ).strip()

    return value or None


def _parse_uuid(
    value,
):
    try:
        return UUID(
            str(value)
        )

    except (
        ValueError,
        TypeError,
    ):
        return None


@umkm_bp.post(
    "/applications"
)
@jwt_required()
def create_application():
    user = _current_user()

    if user is None:
        return jsonify({
            "message":
                "User not found"
        }), 401

    if not user.is_active:
        return jsonify({
            "message":
                "Account is inactive"
        }), 403

    if user.role in {
        User.ROLE_UMKM,
        User.ROLE_ADMIN,
        User.ROLE_SUPER_ADMIN,
    }:
        return jsonify({
            "message": (
                "Account already has "
                "UMKM privileges."
            )
        }), 409

    existing = (
        UmkmApplication.query
        .filter_by(
            user_id=user.id
        )
        .order_by(
            UmkmApplication
            .created_at
            .desc()
        )
        .first()
    )

    if (
        existing is not None
        and existing.status
        == UmkmApplication.STATUS_PENDING
    ):
        return jsonify({
            "message": (
                "You already have a "
                "pending UMKM application."
            ),

            "application":
                existing.to_dict(),
        }), 409

    data = request.get_json(
        silent=True
    ) or {}

    business_name = str(
        data.get(
            "business_name",
            "",
        )
    ).strip()

    business_category = str(
        data.get(
            "business_category",
            "",
        )
    ).strip()

    phone = str(
        data.get(
            "phone",
            "",
        )
    ).strip()

    address = str(
        data.get(
            "address",
            "",
        )
    ).strip()

    if not business_name:
        return jsonify({
            "message":
                "Business name is required."
        }), 400

    if not business_category:
        return jsonify({
            "message": (
                "Business category "
                "is required."
            )
        }), 400

    if not phone:
        return jsonify({
            "message":
                "Phone is required."
        }), 400

    if not address:
        return jsonify({
            "message":
                "Address is required."
        }), 400

    nik = _clean_optional(
        data.get("nik")
    )

    if (
        nik is not None
        and (
            not nik.isdigit()
            or len(nik) != 16
        )
    ):
        return jsonify({
            "message": (
                "NIK must contain "
                "exactly 16 digits."
            )
        }), 400

    application = UmkmApplication(
        user_id=user.id,

        business_name=business_name,

        business_category=(
            business_category
        ),

        phone=phone,

        address=address,

        description=_clean_optional(
            data.get(
                "description"
            )
        ),

        nik=nik,

        document_url=_clean_optional(
            data.get(
                "document_url"
            )
        ),

        status=(
            UmkmApplication
            .STATUS_PENDING
        ),
    )

    db.session.add(
        application
    )

    db.session.commit()

    return jsonify({
        "message": (
            "UMKM application submitted."
        ),

        "application":
            application.to_dict(),
    }), 201


@umkm_bp.get(
    "/applications/me"
)
@jwt_required()
def get_my_application():
    user = _current_user()

    if user is None:
        return jsonify({
            "message":
                "User not found"
        }), 401

    application = (
        UmkmApplication.query
        .filter_by(
            user_id=user.id
        )
        .order_by(
            UmkmApplication
            .created_at
            .desc()
        )
        .first()
    )

    return jsonify({
        "role": user.role,

        "application": (
            application.to_dict()
            if application
            else None
        ),
    }), 200


@umkm_bp.get(
    "/applications"
)
@admin_required
def get_applications():
    status = request.args.get(
        "status"
    )

    query = (
        UmkmApplication.query
    )

    if status:
        if (
            status
            not in
            UmkmApplication
            .VALID_STATUSES
        ):
            return jsonify({
                "message":
                    "Invalid status"
            }), 400

        query = query.filter_by(
            status=status
        )

    applications = (
        query
        .order_by(
            UmkmApplication
            .created_at
            .desc()
        )
        .all()
    )

    return jsonify({
        "applications": [
            item.to_dict()
            for item
            in applications
        ],

        "count":
            len(applications),
    }), 200


@umkm_bp.patch(
    "/applications/"
    "<application_id>"
)
@admin_required
def review_application(
    application_id,
):
    application_uuid = _parse_uuid(
        application_id
    )

    if application_uuid is None:
        return jsonify({
            "message":
                "Invalid application ID"
        }), 400

    application = db.session.get(
        UmkmApplication,
        application_uuid,
    )

    if application is None:
        return jsonify({
            "message": (
                "UMKM application "
                "not found"
            )
        }), 404

    if (
        application.status
        != UmkmApplication
        .STATUS_PENDING
    ):
        return jsonify({
            "message": (
                "Application has "
                "already been reviewed."
            )
        }), 409

    admin = _current_user()

    if admin is None:
        return jsonify({
            "message":
                "Admin not found"
        }), 401

    data = request.get_json(
        silent=True
    ) or {}

    decision = str(
        data.get(
            "decision",
            "",
        )
    ).strip().lower()

    if decision not in {
        "approved",
        "rejected",
    }:
        return jsonify({
            "message": (
                "Decision must be "
                "'approved' or "
                "'rejected'."
            )
        }), 400

    if decision == "approved":
        applicant = db.session.get(
            User,
            application.user_id,
        )

        if applicant is None:
            return jsonify({
                "message": (
                    "Applicant account "
                    "not found."
                )
            }), 404

        if not applicant.is_active:
            return jsonify({
                "message": (
                    "Inactive accounts "
                    "cannot be approved "
                    "as UMKM."
                )
            }), 409

        if applicant.id == admin.id:
            return jsonify({
                "message": (
                    "Administrators cannot "
                    "approve their own "
                    "UMKM application."
                )
            }), 403

        if (
            applicant.role
            != User.ROLE_MEMBER
        ):
            return jsonify({
                "message": (
                    "Applicant is no longer "
                    "eligible for UMKM "
                    "approval."
                ),

                "current_role": (
                    applicant.role
                ),
            }), 409

        applicant.role = (
            User.ROLE_UMKM
        )

        application.status = (
            UmkmApplication
            .STATUS_APPROVED
        )

        application.rejection_reason = (
            None
        )

    else:
        reason = _clean_optional(
            data.get(
                "reason"
            )
        )

        application.status = (
            UmkmApplication
            .STATUS_REJECTED
        )

        application.rejection_reason = (
            reason
        )

    application.reviewed_by = (
        admin.id
    )

    application.reviewed_at = (
        datetime.now(
            timezone.utc
        )
    )

    db.session.commit()

    return jsonify({
        "message": (
            "UMKM application "
            f"{decision}."
        ),

        "application":
            application.to_dict(),
    }), 200