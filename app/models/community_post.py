import uuid

from sqlalchemy import func
from sqlalchemy.dialects.postgresql import UUID

from app.extensions import db


class CommunityPost(db.Model):
    __tablename__ = "community_posts"

    __table_args__ = (
        db.Index(
            "ix_community_posts_type_created_at",
            "post_type",
            "created_at",
        ),
    )

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


class CommunityPostReport(db.Model):
    __tablename__ = "community_post_reports"

    __table_args__ = (
        db.UniqueConstraint(
            "post_id",
            "reporter_user_id",
            name="uq_community_post_reports_post_reporter",
        ),
        db.Index(
            "ix_community_post_reports_status_created_at",
            "status",
            "created_at",
        ),
    )

    id = db.Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    post_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey(
            "community_posts.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    reporter_user_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey(
            "users.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    reason = db.Column(
        db.String(40),
        nullable=False,
    )

    details = db.Column(
        db.Text,
        nullable=True,
    )

    status = db.Column(
        db.String(20),
        nullable=False,
        default="pending",
        server_default="pending",
        index=True,
    )

    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )

    resolved_at = db.Column(
        db.DateTime(timezone=True),
        nullable=True,
    )

    post = db.relationship(
        "CommunityPost",
        foreign_keys=[post_id],
    )

    reporter = db.relationship(
        "User",
        foreign_keys=[reporter_user_id],
    )


class UserBlock(db.Model):
    __tablename__ = "user_blocks"

    __table_args__ = (
        db.UniqueConstraint(
            "blocker_user_id",
            "blocked_user_id",
            name="uq_user_blocks_blocker_blocked",
        ),
        db.Index(
            "ix_user_blocks_blocker_created_at",
            "blocker_user_id",
            "created_at",
        ),
    )

    id = db.Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    blocker_user_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey(
            "users.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    blocked_user_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey(
            "users.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )
