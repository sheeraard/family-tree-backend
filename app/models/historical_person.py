import uuid

from sqlalchemy import func
from sqlalchemy.dialects.postgresql import UUID

from app.extensions import db


class HistoricalPerson(db.Model):
    __tablename__ = "historical_people"

    id = db.Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    name = db.Column(
        db.String(255),
        nullable=False,
        index=True,
    )

    title = db.Column(
        db.String(255),
        nullable=True,
    )

    description = db.Column(
        db.Text,
        nullable=True,
    )

    birth_year = db.Column(
        db.String(50),
        nullable=True,
    )

    death_year = db.Column(
        db.String(50),
        nullable=True,
    )

    location = db.Column(
        db.String(255),
        nullable=True,
    )

    image_url = db.Column(
        db.Text,
        nullable=True,
    )

    source = db.Column(
        db.Text,
        nullable=True,
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

    outgoing_relationships = db.relationship(
        "HistoricalRelationship",
        foreign_keys=(
            "HistoricalRelationship.parent_id"
        ),
        back_populates="parent",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    incoming_relationships = db.relationship(
        "HistoricalRelationship",
        foreign_keys=(
            "HistoricalRelationship.child_id"
        ),
        back_populates="child",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def to_dict(self):
        return {
            "id": str(self.id),
            "name": self.name,
            "title": self.title,
            "description": self.description,
            "birth_year": self.birth_year,
            "death_year": self.death_year,
            "location": self.location,
            "image_url": self.image_url,
            "source": self.source,
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