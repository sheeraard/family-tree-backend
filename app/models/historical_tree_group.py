import uuid

from sqlalchemy import func
from sqlalchemy.dialects.postgresql import UUID

from app.extensions import db


class HistoricalTreeGroup(db.Model):
    __tablename__ = "historical_tree_groups"

    id = db.Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    name = db.Column(
        db.String(255),
        nullable=False,
        unique=True,
        index=True,
    )

    head_person_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey(
            "historical_people.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        unique=True,
        index=True,
    )

    description = db.Column(
        db.Text,
        nullable=True,
    )

    sort_order = db.Column(
        db.Integer,
        nullable=False,
        default=0,
        server_default="0",
        index=True,
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

    head_person = db.relationship(
        "HistoricalPerson",
        foreign_keys=[head_person_id],
        lazy="joined",
        passive_deletes=True,
    )

    def to_dict(self):
        return {
            "id": str(self.id),
            "name": self.name,
            "head_person_id": (
                str(self.head_person_id)
                if self.head_person_id
                else None
            ),
            "description": self.description,
            "sort_order": self.sort_order,
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
