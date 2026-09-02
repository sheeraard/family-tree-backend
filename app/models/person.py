import uuid

from sqlalchemy import func
from sqlalchemy.dialects.postgresql import UUID

from app.extensions import db


class Person(db.Model):
    __tablename__ = "people"

    id = db.Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    user_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey(
            "users.id",
            ondelete="SET NULL",
        ),
        unique=True,
        nullable=True,
    )

    created_by_user_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey(
            "users.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    full_name = db.Column(
        db.String(255),
        nullable=False,
        index=True,
    )

    birth_date = db.Column(
        db.Date,
        nullable=True,
    )

    gender = db.Column(
        db.String(20),
        nullable=True,
    )

    nik = db.Column(
        db.String(16),
        unique=True,
        nullable=True,
    )

    photo_url = db.Column(
        db.Text,
        nullable=True,
    )

    claim_code_hash = db.Column(
        db.String(64),
        unique=True,
        nullable=True,
        index=True,
    )

    claim_code_expires_at = db.Column(
        db.DateTime(timezone=True),
        nullable=True,
        index=True,
    )

    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    user = db.relationship(
        "User",
        foreign_keys=[user_id],
        back_populates="person",
    )

    created_by_user = db.relationship(
        "User",
        foreign_keys=[created_by_user_id],
    )