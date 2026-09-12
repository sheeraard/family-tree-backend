import uuid

from sqlalchemy import func
from sqlalchemy.dialects.postgresql import UUID

from app.extensions import db


class User(db.Model):
    __tablename__ = "users"

    ROLE_MEMBER = "member"
    ROLE_UMKM = "umkm"
    ROLE_ADMIN = "admin"
    ROLE_SUPER_ADMIN = "super_admin"

    VALID_ROLES = {
        ROLE_MEMBER,
        ROLE_UMKM,
        ROLE_ADMIN,
        ROLE_SUPER_ADMIN,
    }

    id = db.Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    email = db.Column(
        db.String(255),
        unique=True,
        nullable=False,
        index=True,
    )

    phone = db.Column(
        db.String(30),
        unique=True,
        nullable=True,
        index=True,
    )

    password_hash = db.Column(
        db.String(255),
        nullable=False,
    )

    role = db.Column(
        db.String(30),
        nullable=False,
        default=ROLE_MEMBER,
        server_default=ROLE_MEMBER,
        index=True,
    )

    is_active = db.Column(
        db.Boolean,
        nullable=False,
        default=True,
    )

    is_email_verified = db.Column(
        db.Boolean,
        nullable=False,
        default=False,
        server_default=db.false(),
        index=True,
    )

    session_version = db.Column(
        db.Integer,
        nullable=False,
        default=0,
        server_default="0",
    )

    email_verified_at = db.Column(
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

    person = db.relationship(
        "Person",
        foreign_keys="Person.user_id",
        back_populates="user",
        uselist=False,
    )

    products = db.relationship(
        "Product",
        foreign_keys="Product.seller_user_id",
        back_populates="seller",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    email_verification_codes = db.relationship(
        "EmailVerificationCode",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    @property
    def is_member(self):
        return self.role == self.ROLE_MEMBER

    @property
    def is_umkm(self):
        return self.role == self.ROLE_UMKM

    @property
    def is_admin(self):
        return self.role in {
            self.ROLE_ADMIN,
            self.ROLE_SUPER_ADMIN,
        }

    @property
    def is_super_admin(self):
        return (
            self.role
            == self.ROLE_SUPER_ADMIN
        )

    @property
    def can_sell_products(self):
        return self.role in {
            self.ROLE_UMKM,
            self.ROLE_ADMIN,
            self.ROLE_SUPER_ADMIN,
        }

    def to_dict(self):
        return {
            "id": str(self.id),
            "email": self.email,
            "phone": self.phone,
            "role": self.role,
            "is_active": self.is_active,
            "is_email_verified": (
                self.is_email_verified
            ),
            "email_verified_at": (
                self.email_verified_at.isoformat()
                if self.email_verified_at
                else None
            ),
        }