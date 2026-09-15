import uuid

from sqlalchemy import func
from sqlalchemy.dialects.postgresql import (
    JSONB,
    UUID,
)

from app.extensions import db


class CultureContent(db.Model):
    __tablename__ = "culture_contents"

    id = db.Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    title = db.Column(
        db.String(200),
        nullable=False,
        index=True,
    )

    description = db.Column(
        db.Text,
        nullable=False,
    )

    category = db.Column(
        db.String(100),
        nullable=True,
        index=True,
    )

    location = db.Column(
        db.String(200),
        nullable=True,
    )

    # Backward-compatible cover image field.
    # The first entry in image_urls is always
    # mirrored here for older clients.
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

    is_published = db.Column(
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

    def to_dict(self):
        images = list(
            self.image_urls
            or []
        )

        if (
            not images
            and self.image_url
        ):
            images = [
                self.image_url
            ]

        return {
            "id": str(self.id),
            "title": self.title,
            "description": self.description,
            "category": self.category,
            "location": self.location,
            "image_url": (
                images[0]
                if images
                else None
            ),
            "image_urls": images,
            "is_published": self.is_published,
            "created_at": (
                self.created_at.isoformat()
                if self.created_at
                else None
            ),
            "updated_at": (
                self.updated_at.isoformat()
                if self.updated_at
                else None
            ),
        }