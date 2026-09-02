import uuid

from sqlalchemy import func
from sqlalchemy.dialects.postgresql import UUID

from app.extensions import db


class RelationshipRequest(db.Model):
    __tablename__ = "relationship_requests"

    id = db.Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    sender_person_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey("people.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    receiver_person_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey("people.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    relationship_type = db.Column(
        db.String(30),
        nullable=False,
    )

    status = db.Column(
        db.String(20),
        nullable=False,
        default="pending",
        index=True,
    )

    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    responded_at = db.Column(
        db.DateTime(timezone=True),
        nullable=True,
    )

    sender = db.relationship(
        "Person",
        foreign_keys=[sender_person_id],
        backref="sent_relationship_requests",
    )

    receiver = db.relationship(
        "Person",
        foreign_keys=[receiver_person_id],
        backref="received_relationship_requests",
    )