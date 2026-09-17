from datetime import datetime
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

from sqlalchemy.orm import joinedload

from app.extensions import db
from app.models import (
    CommunityPost,
    User,
)


community_bp = Blueprint(
    "community",
    __name__,
)


ALLOWED_POST_TYPES = {
    "event",
    "family_news",
}


def _pagination_args(
    default_per_page=20,
):
    page = request.args.get(
        "page",
        default=1,
        type=int,
    ) or 1

    per_page = request.args.get(
        "per_page",
        default=default_per_page,
        type=int,
    ) or default_per_page

    page = max(1, page)
    per_page = min(
        100,
        max(1, per_page),
    )

    return page, per_page


def _pagination_payload(
    page,
    per_page,
    total,
):
    pages = (
        (total + per_page - 1)
        // per_page
        if total > 0
        else 0
    )

    return {
        "page": page,
        "per_page": per_page,
        "total": total,
        "pages": pages,
        "has_next": page < pages,
        "has_prev": page > 1,
    }


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


def author_name(post):
    author = post.author

    if (
        author is not None
        and author.person is not None
    ):
        return author.person.full_name

    if author is not None:
        return author.email

    return "Unknown"


def serialize_post(
    post,
    current_user_id=None,
):
    return {
        "id": str(post.id),

        "author_user_id": str(
            post.author_user_id
        ),

        "author_name": author_name(
            post
        ),

        "post_type": post.post_type,

        "title": post.title,

        "body": post.body,

        "event_at": (
            post.event_at.isoformat()
            if post.event_at
            else None
        ),

        "location": post.location,

        "created_at": (
            post.created_at.isoformat()
            if post.created_at
            else None
        ),

        "updated_at": (
            post.updated_at.isoformat()
            if post.updated_at
            else None
        ),

        "is_owner": (
            current_user_id is not None
            and post.author_user_id
            == current_user_id
        ),
    }


def parse_iso_datetime(value):
    if value is None:
        return None

    value = str(value).strip()

    if not value:
        return None

    try:
        return datetime.fromisoformat(
            value.replace(
                "Z",
                "+00:00",
            )
        )

    except ValueError:
        return None


@community_bp.get("/posts")
@jwt_required()
def get_posts():
    user = get_current_user()

    if user is None:
        return jsonify(
            {
                "message":
                    "User not found."
            }
        ), 404

    post_type = (
        request.args
        .get(
            "type",
            "",
        )
        .strip()
    )

    page, per_page = (
        _pagination_args()
    )

    query = (
        CommunityPost.query
        .options(
            joinedload(
                CommunityPost.author
            ).joinedload(
                User.person
            )
        )
    )

    if post_type:
        if (
            post_type
            not in ALLOWED_POST_TYPES
        ):
            return jsonify(
                {
                    "message":
                        "Invalid post type."
                }
            ), 400

        query = query.filter(
            CommunityPost.post_type
            == post_type
        )

    total = query.count()

    posts = (
        query
        .order_by(
            CommunityPost.created_at.desc()
        )
        .offset(
            (page - 1) * per_page
        )
        .limit(per_page)
        .all()
    )

    return jsonify(
        {
            "posts": [
                serialize_post(
                    post,
                    current_user_id=user.id,
                )
                for post in posts
            ],
            "count": len(posts),
            "pagination": (
                _pagination_payload(
                    page,
                    per_page,
                    total,
                )
            ),
        }
    ), 200


@community_bp.post("/posts")
@jwt_required()
def create_post():
    user = get_current_user()

    if user is None:
        return jsonify(
            {
                "message":
                    "User not found."
            }
        ), 404

    data = (
        request.get_json(
            silent=True
        )
        or {}
    )

    post_type = str(
        data.get(
            "post_type",
            "",
        )
    ).strip()

    title = str(
        data.get(
            "title",
            "",
        )
    ).strip()

    body = str(
        data.get(
            "body",
            "",
        )
        or ""
    ).strip()

    location = str(
        data.get(
            "location",
            "",
        )
        or ""
    ).strip()

    if (
        post_type
        not in ALLOWED_POST_TYPES
    ):
        return jsonify(
            {
                "message":
                    "Invalid post type."
            }
        ), 400

    if not title:
        return jsonify(
            {
                "message":
                    "Title is required."
            }
        ), 400

    if len(title) > 180:
        return jsonify(
            {
                "message":
                    "Title is too long."
            }
        ), 400

    event_at = None

    if post_type == "event":
        event_at = parse_iso_datetime(
            data.get(
                "event_at"
            )
        )

        if event_at is None:
            return jsonify(
                {
                    "message":
                        "Event date and time "
                        "are required."
                }
            ), 400

    post = CommunityPost(
        author_user_id=user.id,
        post_type=post_type,
        title=title,
        body=body or None,
        event_at=event_at,
        location=location or None,
    )

    db.session.add(
        post
    )

    db.session.commit()

    return jsonify(
        {
            "message":
                "Post created.",

            "post":
                serialize_post(
                    post,
                    current_user_id=user.id,
                ),
        }
    ), 201


@community_bp.delete(
    "/posts/<uuid:post_id>"
)
@jwt_required()
def delete_post(post_id):
    user = get_current_user()

    if user is None:
        return jsonify(
            {
                "message":
                    "User not found."
            }
        ), 404

    post = db.session.get(
        CommunityPost,
        post_id,
    )

    if post is None:
        return jsonify(
            {
                "message":
                    "Post not found."
            }
        ), 404

    if (
        post.author_user_id
        != user.id
    ):
        return jsonify(
            {
                "message":
                    "You cannot delete "
                    "this post."
            }
        ), 403

    db.session.delete(
        post
    )

    db.session.commit()

    return jsonify(
        {
            "message":
                "Post deleted."
        }
    ), 200