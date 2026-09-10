import uuid

from sqlalchemy import func
from sqlalchemy.dialects.postgresql import UUID

from app.extensions import db


class HistoricalRelationship(db.Model):
    __tablename__ = (
        "historical_relationships"
    )

    __table_args__ = (
        db.CheckConstraint(
            "parent_id <> child_id",
            name=(
                "ck_historical_relationship_"
                "different_people"
            ),
        ),
        db.UniqueConstraint(
            "parent_id",
            "child_id",
            "relationship_type",
            name=(
                "uq_historical_relationship_"
                "parent_child_type"
            ),
        ),
    )

    id = db.Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    parent_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey(
            "historical_people.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    child_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey(
            "historical_people.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    relationship_type = db.Column(
        db.String(50),
        nullable=False,
        default="parent",
        server_default="parent",
    )

    notes = db.Column(
        db.Text,
        nullable=True,
    )

    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    parent = db.relationship(
        "HistoricalPerson",
        foreign_keys=[parent_id],
        back_populates=(
            "outgoing_relationships"
        ),
    )

    child = db.relationship(
        "HistoricalPerson",
        foreign_keys=[child_id],
        back_populates=(
            "incoming_relationships"
        ),
    )

    def to_dict(self):
        return {
            "id": str(self.id),
            "parent_id": str(
                self.parent_id
            ),
            "child_id": str(
                self.child_id
            ),
            "relationship_type": (
                self.relationship_type
            ),
            "notes": self.notes,
            "created_at": (
                self.created_at.isoformat()
                if self.created_at
                else None
            ),
        }