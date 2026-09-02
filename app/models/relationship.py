import uuid

from sqlalchemy import func
from sqlalchemy.dialects.postgresql import UUID

from app.extensions import db


class Relationship(db.Model):
    __tablename__ = "relationships"

    __table_args__ = (
        db.CheckConstraint(
            "person_a_id <> person_b_id",
            name=(
                "ck_relationship_"
                "different_people"
            ),
        ),
    )

    id = db.Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    person_a_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey(
            "people.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    person_b_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey(
            "people.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    relation_a_to_b = db.Column(
        db.String(30),
        nullable=False,
    )

    relation_b_to_a = db.Column(
        db.String(30),
        nullable=False,
    )

    verification_status = (
        db.Column(
            db.String(20),
            nullable=False,
            default="verified",
            server_default="verified",
            index=True,
        )
    )

    created_at = db.Column(
        db.DateTime(
            timezone=True
        ),
        nullable=False,
        server_default=func.now(),
    )

    person_a = db.relationship(
        "Person",
        foreign_keys=[
            person_a_id
        ],
    )

    person_b = db.relationship(
        "Person",
        foreign_keys=[
            person_b_id
        ],
    )