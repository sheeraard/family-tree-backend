import uuid

from sqlalchemy import func
from sqlalchemy.dialects.postgresql import UUID

from app.extensions import db


class UmkmApplication(db.Model):
    __tablename__ = "umkm_applications"

    STATUS_PENDING = "pending"
    STATUS_APPROVED = "approved"
    STATUS_REJECTED = "rejected"

    VALID_STATUSES = {
        STATUS_PENDING,
        STATUS_APPROVED,
        STATUS_REJECTED,
    }

    id = db.Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    user_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey(
            "users.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    business_name = db.Column(
        db.String(255),
        nullable=False,
        index=True,
    )

    business_category = db.Column(
        db.String(120),
        nullable=False,
    )

    phone = db.Column(
        db.String(50),
        nullable=False,
    )

    address = db.Column(
        db.Text,
        nullable=False,
    )

    description = db.Column(
        db.Text,
        nullable=True,
    )

    nik = db.Column(
        db.String(32),
        nullable=True,
    )

    document_url = db.Column(
        db.Text,
        nullable=True,
    )

    status = db.Column(
        db.String(30),
        nullable=False,
        default=STATUS_PENDING,
        server_default=STATUS_PENDING,
        index=True,
    )

    rejection_reason = db.Column(
        db.Text,
        nullable=True,
    )

    reviewed_by = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey(
            "users.id",
            ondelete="SET NULL",
        ),
        nullable=True,
    )

    reviewed_at = db.Column(
        db.DateTime(timezone=True),
        nullable=True,
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

    applicant = db.relationship(
        "User",
        foreign_keys=[user_id],
    )

    reviewer = db.relationship(
        "User",
        foreign_keys=[reviewed_by],
    )

    def to_dict(self):
        return {
            "id": str(self.id),

            "user_id": str(
                self.user_id
            ),

            "business_name":
                self.business_name,

            "business_category":
                self.business_category,

            "phone": self.phone,

            "address": self.address,

            "description":
                self.description,

            "nik": self.nik,

            "document_url":
                self.document_url,

            "status": self.status,

            "rejection_reason":
                self.rejection_reason,

            "reviewed_by": (
                str(self.reviewed_by)
                if self.reviewed_by
                else None
            ),

            "reviewed_at": (
                self.reviewed_at.isoformat()
                if self.reviewed_at
                else None
            ),

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

            "applicant": {
                "email":
                    self.applicant.email,

                "phone":
                    self.applicant.phone,

                "role":
                    self.applicant.role,
            } if self.applicant else None,
        }