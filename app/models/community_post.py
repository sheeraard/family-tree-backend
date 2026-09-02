import uuid

from sqlalchemy import func
from sqlalchemy.dialects.postgresql import UUID

from app.extensions import db


class CommunityPost(db.Model):
    __tablename__ = "community_posts"

    id = db.Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    author_user_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey(
            "users.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    post_type = db.Column(
        db.String(30),
        nullable=False,
        index=True,
    )

    title = db.Column(
        db.String(180),
        nullable=False,
    )

    body = db.Column(
        db.Text,
        nullable=True,
    )

    event_at = db.Column(
        db.DateTime(timezone=True),
        nullable=True,
        index=True,
    )

    location = db.Column(
        db.String(255),
        nullable=True,
    )

    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )

    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    author = db.relationship(
        "User",
        foreign_keys=[author_user_id],
    )