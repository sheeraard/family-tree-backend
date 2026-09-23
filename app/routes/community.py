import os
import re
from collections import deque
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

from sqlalchemy.orm import joinedload

from app.extensions import db
from app.models import (
    CommunityPost,
    Person,
    Relationship,
    User,
)
from app.models.community_post import (
    CommunityPostReport,
    UserBlock,
)


community_bp = Blueprint(
    "community",
    __name__,
)


ALLOWED_POST_TYPES = {
    "event",
    "family_news",
}


ALLOWED_REPORT_REASONS = {
    "spam",
    "harassment",
    "hate_or_abuse",
    "sexual_content",
    "violence",
    "misinformation",
    "other",
}


ALLOWED_REPORT_STATUSES = {
    "pending",
    "reviewed",
    "dismissed",
    "actioned",
}


# This is intentionally a small, conservative baseline.
# Extra words/phrases can be added in Railway with:
#
# COMMUNITY_BLOCKED_TERMS=term one,term two,...
#
# The user-facing report/block tools remain the main moderation path.
DEFAULT_BLOCKED_TERMS = {
    "fuck",
    "fucking",
    "cunt",
    "faggot",
    "nigger",
    "porn",
    "pornography",
    "kill yourself",
    "kontol",
    "memek",
    "ngentot",
    "jembut",
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


def _user_display_name(user):
    if (
        user is not None
        and user.person is not None
    ):
        return user.person.full_name

    if user is not None:
        return "Caruban user"

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


def serialize_report(report):
    post = report.post

    return {
        "id": str(report.id),
        "post_id": str(report.post_id),
        "reporter_user_id": str(
            report.reporter_user_id
        ),
        "reason": report.reason,
        "details": report.details,
        "status": report.status,
        "created_at": (
            report.created_at.isoformat()
            if report.created_at
            else None
        ),
        "resolved_at": (
            report.resolved_at.isoformat()
            if report.resolved_at
            else None
        ),
        "post": (
            {
                "title": post.title,
                "author_user_id": str(
                    post.author_user_id
                ),
                "author_name": (
                    author_name(post)
                ),
            }
            if post is not None
            else None
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


def _blocked_terms():
    terms = set(
        DEFAULT_BLOCKED_TERMS
    )

    extra = os.getenv(
        "COMMUNITY_BLOCKED_TERMS",
        "",
    )

    for item in extra.split(","):
        item = item.strip()

        if item:
            terms.add(item)

    return terms


def _contains_blocked_content(
    *values,
):
    text = " ".join(
        str(value or "")
        for value in values
    )

    text = " ".join(
        text.casefold().split()
    )

    if not text:
        return False

    for term in _blocked_terms():
        normalized_term = (
            " ".join(
                term.casefold().split()
            )
        )

        if not normalized_term:
            continue

        pattern = (
            r"(?<!\w)"
            + re.escape(
                normalized_term
            )
            + r"(?!\w)"
        )

        if re.search(
            pattern,
            text,
            flags=re.IGNORECASE,
        ):
            return True

    return False


def _family_user_ids(
    user,
    max_depth=6,
):
    """
    Return registered user IDs in the logged-in
    user's connected personal genealogy network.

    This intentionally follows the same explicit
    relationship graph semantics already used by
    the personal family-tree features: parent,
    child, sibling, spouse, and any other stored
    Relationship edge are traversed up to six
    hops.

    If the account has no Person profile yet,
    only the account itself is considered part
    of its family network.
    """
    if user.person is None:
        return {
            user.id
        }

    root_person_id = (
        user.person.id
    )

    visited = {
        root_person_id
    }

    queue = deque([
        (
            root_person_id,
            0,
        )
    ])

    while queue:
        (
            current_person_id,
            depth,
        ) = queue.popleft()

        if depth >= max_depth:
            continue

        relationships = (
            db.session.scalars(
                db.select(
                    Relationship
                )
                .where(
                    db.or_(
                        Relationship
                        .person_a_id
                        == current_person_id,

                        Relationship
                        .person_b_id
                        == current_person_id,
                    )
                )
            )
            .all()
        )

        for relationship in relationships:
            if (
                relationship.person_a_id
                == current_person_id
            ):
                relative_id = (
                    relationship.person_b_id
                )
            else:
                relative_id = (
                    relationship.person_a_id
                )

            if relative_id in visited:
                continue

            visited.add(
                relative_id
            )

            queue.append(
                (
                    relative_id,
                    depth + 1,
                )
            )

    registered_user_ids = set(
        db.session.scalars(
            db.select(
                Person.user_id
            )
            .where(
                Person.id.in_(
                    visited
                ),
                Person.user_id.is_not(
                    None
                ),
            )
        )
        .all()
    )

    # Always include the current account, even if
    # its Person link is temporarily incomplete.
    registered_user_ids.add(
        user.id
    )

    return registered_user_ids


def _visible_posts_query(
    user,
):
    blocked_by_me = db.select(
        UserBlock.blocked_user_id
    ).where(
        UserBlock.blocker_user_id
        == user.id
    )

    blocked_me = db.select(
        UserBlock.blocker_user_id
    ).where(
        UserBlock.blocked_user_id
        == user.id
    )

    reported_by_me = db.select(
        CommunityPostReport.post_id
    ).where(
        CommunityPostReport
        .reporter_user_id
        == user.id
    )

    family_user_ids = (
        _family_user_ids(
            user
        )
    )

    return (
        CommunityPost.query
        .options(
            joinedload(
                CommunityPost.author
            ).joinedload(
                User.person
            )
        )
        .filter(
            ~CommunityPost.author_user_id
            .in_(blocked_by_me)
        )
        .filter(
            ~CommunityPost.author_user_id
            .in_(blocked_me)
        )
        .filter(
            ~CommunityPost.id
            .in_(reported_by_me)
        )
        .filter(
            db.or_(
                CommunityPost.post_type
                != "family_news",

                CommunityPost.author_user_id
                .in_(
                    family_user_ids
                ),
            )
        )
    )


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

    query = _visible_posts_query(
        user
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

    if len(body) > 10000:
        return jsonify(
            {
                "message":
                    "Post body is too long."
            }
        ), 400

    if len(location) > 255:
        return jsonify(
            {
                "message":
                    "Location is too long."
            }
        ), 400

    if _contains_blocked_content(
        title,
        body,
        location,
    ):
        return jsonify(
            {
                "message": (
                    "This post contains content "
                    "that is not allowed in the "
                    "Caruban community."
                )
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


@community_bp.post(
    "/posts/<uuid:post_id>/report"
)
@jwt_required()
def report_post(post_id):
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
        == user.id
    ):
        return jsonify(
            {
                "message":
                    "You cannot report "
                    "your own post."
            }
        ), 400

    data = (
        request.get_json(
            silent=True
        )
        or {}
    )

    reason = str(
        data.get(
            "reason",
            "",
        )
    ).strip()

    details = str(
        data.get(
            "details",
            "",
        )
        or ""
    ).strip()

    if (
        reason
        not in ALLOWED_REPORT_REASONS
    ):
        return jsonify(
            {
                "message":
                    "Invalid report reason."
            }
        ), 400

    if len(details) > 1000:
        return jsonify(
            {
                "message":
                    "Report details are too long."
            }
        ), 400

    existing = (
        CommunityPostReport.query
        .filter(
            CommunityPostReport.post_id
            == post.id,
            CommunityPostReport
            .reporter_user_id
            == user.id,
        )
        .first()
    )

    if existing is not None:
        existing.reason = reason
        existing.details = (
            details or None
        )
        existing.status = "pending"
        existing.resolved_at = None

        db.session.commit()

        return jsonify(
            {
                "message": (
                    "Report updated. "
                    "The post is hidden "
                    "from your feed."
                ),
                "report_id": str(
                    existing.id
                ),
            }
        ), 200

    report = CommunityPostReport(
        post_id=post.id,
        reporter_user_id=user.id,
        reason=reason,
        details=details or None,
    )

    db.session.add(
        report
    )

    db.session.commit()

    return jsonify(
        {
            "message": (
                "Report submitted. "
                "The post is hidden "
                "from your feed."
            ),
            "report_id": str(
                report.id
            ),
        }
    ), 201


@community_bp.post(
    "/users/<uuid:user_id>/block"
)
@jwt_required()
def block_user(user_id):
    user = get_current_user()

    if user is None:
        return jsonify(
            {
                "message":
                    "User not found."
            }
        ), 404

    if user_id == user.id:
        return jsonify(
            {
                "message":
                    "You cannot block yourself."
            }
        ), 400

    target = db.session.get(
        User,
        user_id,
    )

    if target is None:
        return jsonify(
            {
                "message":
                    "User not found."
            }
        ), 404

    existing = (
        UserBlock.query
        .filter(
            UserBlock.blocker_user_id
            == user.id,
            UserBlock.blocked_user_id
            == target.id,
        )
        .first()
    )

    if existing is not None:
        return jsonify(
            {
                "message":
                    "User is already blocked."
            }
        ), 200

    block = UserBlock(
        blocker_user_id=user.id,
        blocked_user_id=target.id,
    )

    db.session.add(
        block
    )

    db.session.commit()

    return jsonify(
        {
            "message":
                "User blocked.",
            "blocked_user": {
                "id": str(target.id),
                "name": (
                    _user_display_name(
                        target
                    )
                ),
            },
        }
    ), 201


@community_bp.delete(
    "/users/<uuid:user_id>/block"
)
@jwt_required()
def unblock_user(user_id):
    user = get_current_user()

    if user is None:
        return jsonify(
            {
                "message":
                    "User not found."
            }
        ), 404

    block = (
        UserBlock.query
        .filter(
            UserBlock.blocker_user_id
            == user.id,
            UserBlock.blocked_user_id
            == user_id,
        )
        .first()
    )

    if block is not None:
        db.session.delete(
            block
        )

        db.session.commit()

    return jsonify(
        {
            "message":
                "User unblocked."
        }
    ), 200


@community_bp.get(
    "/reports"
)
@jwt_required()
def get_reports():
    user = get_current_user()

    if user is None:
        return jsonify(
            {
                "message":
                    "User not found."
            }
        ), 404

    if not user.is_admin:
        return jsonify(
            {
                "message":
                    "Admin access required."
            }
        ), 403

    status = str(
        request.args.get(
            "status",
            "pending",
        )
    ).strip()

    if (
        status
        not in ALLOWED_REPORT_STATUSES
    ):
        return jsonify(
            {
                "message":
                    "Invalid report status."
            }
        ), 400

    page, per_page = (
        _pagination_args()
    )

    query = (
        CommunityPostReport.query
        .options(
            joinedload(
                CommunityPostReport.post
            ).joinedload(
                CommunityPost.author
            ).joinedload(
                User.person
            )
        )
        .filter(
            CommunityPostReport.status
            == status
        )
    )

    total = query.count()

    reports = (
        query
        .order_by(
            CommunityPostReport
            .created_at
            .desc()
        )
        .offset(
            (page - 1) * per_page
        )
        .limit(per_page)
        .all()
    )

    return jsonify(
        {
            "reports": [
                serialize_report(
                    report
                )
                for report in reports
            ],
            "pagination": (
                _pagination_payload(
                    page,
                    per_page,
                    total,
                )
            ),
        }
    ), 200


@community_bp.patch(
    "/reports/<uuid:report_id>"
)
@jwt_required()
def update_report(report_id):
    user = get_current_user()

    if user is None:
        return jsonify(
            {
                "message":
                    "User not found."
            }
        ), 404

    if not user.is_admin:
        return jsonify(
            {
                "message":
                    "Admin access required."
            }
        ), 403

    report = db.session.get(
        CommunityPostReport,
        report_id,
    )

    if report is None:
        return jsonify(
            {
                "message":
                    "Report not found."
            }
        ), 404

    data = (
        request.get_json(
            silent=True
        )
        or {}
    )

    status = str(
        data.get(
            "status",
            "",
        )
    ).strip()

    if status not in {
        "reviewed",
        "dismissed",
        "actioned",
    }:
        return jsonify(
            {
                "message":
                    "Invalid report status."
            }
        ), 400

    report.status = status
    report.resolved_at = (
        datetime.now(
            timezone.utc
        )
    )

    db.session.commit()

    return jsonify(
        {
            "message":
                "Report updated.",
            "report":
                serialize_report(
                    report
                ),
        }
    ), 200


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
        and not user.is_admin
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