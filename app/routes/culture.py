from uuid import UUID

from flask import (
    Blueprint,
    jsonify,
    request,
)

from flask_jwt_extended import (
    jwt_required,
)

from app.extensions import db
from app.models.culture_content import (
    CultureContent,
)
from app.utils.permissions import (
    admin_required,
)


culture_bp = Blueprint(
    "culture",
    __name__,
)


def _get_content_or_none(
    content_id,
):
    try:
        content_uuid = UUID(
            str(content_id)
        )

    except (
        ValueError,
        TypeError,
    ):
        return None

    return db.session.get(
        CultureContent,
        content_uuid,
    )


@culture_bp.get("")
def get_culture_contents():
    """
    Public endpoint.

    Normal users only receive
    published Budaya content.
    """

    contents = (
        CultureContent.query
        .filter_by(
            is_published=True
        )
        .order_by(
            CultureContent.created_at.desc()
        )
        .all()
    )

    return jsonify({
        "items": [
            content.to_dict()
            for content in contents
        ],
        "count": len(contents),
    }), 200


@culture_bp.get("/<content_id>")
def get_culture_content(
    content_id,
):
    """
    Public endpoint for one
    published Budaya item.
    """

    content = _get_content_or_none(
        content_id
    )

    if content is None:
        return jsonify({
            "message": (
                "Culture content not found"
            )
        }), 404

    if not content.is_published:
        return jsonify({
            "message": (
                "Culture content not found"
            )
        }), 404

    return jsonify(
        content.to_dict()
    ), 200


@culture_bp.get("/admin")
@admin_required
def get_admin_culture_contents():
    """
    Admin endpoint.

    Includes drafts and
    unpublished content.
    """

    contents = (
        CultureContent.query
        .order_by(
            CultureContent.created_at.desc()
        )
        .all()
    )

    return jsonify({
        "items": [
            content.to_dict()
            for content in contents
        ],
        "count": len(contents),
    }), 200


@culture_bp.post("")
@admin_required
def create_culture_content():
    data = request.get_json(
        silent=True
    ) or {}

    title = str(
        data.get(
            "title",
            "",
        )
    ).strip()

    description = str(
        data.get(
            "description",
            "",
        )
    ).strip()

    category = data.get(
        "category"
    )

    location = data.get(
        "location"
    )

    image_url = data.get(
        "image_url"
    )

    is_published = data.get(
        "is_published",
        True,
    )

    if not title:
        return jsonify({
            "message": (
                "Title is required"
            )
        }), 400

    if not description:
        return jsonify({
            "message": (
                "Description is required"
            )
        }), 400

    if category is not None:
        category = str(
            category
        ).strip() or None

    if location is not None:
        location = str(
            location
        ).strip() or None

    if image_url is not None:
        image_url = str(
            image_url
        ).strip() or None

    if not isinstance(
        is_published,
        bool,
    ):
        return jsonify({
            "message": (
                "is_published must "
                "be true or false"
            )
        }), 400

    content = CultureContent(
        title=title,
        description=description,
        category=category,
        location=location,
        image_url=image_url,
        is_published=is_published,
    )

    db.session.add(
        content
    )

    db.session.commit()

    return jsonify({
        "message": (
            "Culture content created"
        ),
        "item": content.to_dict(),
    }), 201


@culture_bp.put("/<content_id>")
@admin_required
def update_culture_content(
    content_id,
):
    content = _get_content_or_none(
        content_id
    )

    if content is None:
        return jsonify({
            "message": (
                "Culture content not found"
            )
        }), 404

    data = request.get_json(
        silent=True
    ) or {}

    if "title" in data:
        title = str(
            data.get(
                "title",
                "",
            )
        ).strip()

        if not title:
            return jsonify({
                "message": (
                    "Title cannot be empty"
                )
            }), 400

        content.title = title

    if "description" in data:
        description = str(
            data.get(
                "description",
                "",
            )
        ).strip()

        if not description:
            return jsonify({
                "message": (
                    "Description cannot "
                    "be empty"
                )
            }), 400

        content.description = (
            description
        )

    if "category" in data:
        category = data.get(
            "category"
        )

        content.category = (
            str(category).strip()
            if category is not None
            else None
        )

        if content.category == "":
            content.category = None

    if "location" in data:
        location = data.get(
            "location"
        )

        content.location = (
            str(location).strip()
            if location is not None
            else None
        )

        if content.location == "":
            content.location = None

    if "image_url" in data:
        image_url = data.get(
            "image_url"
        )

        content.image_url = (
            str(image_url).strip()
            if image_url is not None
            else None
        )

        if content.image_url == "":
            content.image_url = None

    if "is_published" in data:
        is_published = data.get(
            "is_published"
        )

        if not isinstance(
            is_published,
            bool,
        ):
            return jsonify({
                "message": (
                    "is_published must "
                    "be true or false"
                )
            }), 400

        content.is_published = (
            is_published
        )

    db.session.commit()

    return jsonify({
        "message": (
            "Culture content updated"
        ),
        "item": content.to_dict(),
    }), 200


@culture_bp.delete("/<content_id>")
@admin_required
def delete_culture_content(
    content_id,
):
    content = _get_content_or_none(
        content_id
    )

    if content is None:
        return jsonify({
            "message": (
                "Culture content not found"
            )
        }), 404

    db.session.delete(
        content
    )

    db.session.commit()

    return jsonify({
        "message": (
            "Culture content deleted"
        )
    }), 200