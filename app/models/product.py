import uuid

from sqlalchemy import func
from sqlalchemy.dialects.postgresql import (
    JSONB,
    UUID,
)

from app.extensions import db


class Product(db.Model):
    __tablename__ = "products"

    id = db.Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    seller_user_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey(
            "users.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    name = db.Column(
        db.String(160),
        nullable=False,
        index=True,
    )

    description = db.Column(
        db.Text,
        nullable=True,
    )

    price = db.Column(
        db.BigInteger,
        nullable=False,
    )

    category = db.Column(
        db.String(80),
        nullable=True,
        index=True,
    )

    contact = db.Column(
        db.String(255),
        nullable=True,
    )

    image_url = db.Column(
        db.Text,
        nullable=True,
    )

    image_urls = db.Column(
        JSONB,
        nullable=False,
        default=list,
        server_default="[]",
    )

    is_active = db.Column(
        db.Boolean,
        nullable=False,
        default=True,
        server_default="true",
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

    seller = db.relationship(
        "User",
        foreign_keys=[
            seller_user_id
        ],
        back_populates="products",
    )