import hashlib
import hmac
import uuid

from datetime import (
    datetime,
    timezone,
)

from flask import current_app
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import UUID

from app.extensions import db


class EmailVerificationCode(db.Model):
    __tablename__ = "email_verification_codes"

    MAX_ATTEMPTS = 5

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

    code_hash = db.Column(
        db.String(64),
        nullable=False,
    )

    attempts = db.Column(
        db.Integer,
        nullable=False,
        default=0,
        server_default="0",
    )

    expires_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        index=True,
    )

    used_at = db.Column(
        db.DateTime(timezone=True),
        nullable=True,
    )

    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    user = db.relationship(
        "User",
        back_populates="email_verification_codes",
    )

    @staticmethod
    def hash_code(code: str) -> str:
        secret = current_app.config[
            "SECRET_KEY"
        ].encode("utf-8")

        return hmac.new(
            secret,
            code.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    def matches_code(
        self,
        code: str,
    ) -> bool:
        submitted_hash = self.hash_code(
            code
        )

        return hmac.compare_digest(
            self.code_hash,
            submitted_hash,
        )

    @property
    def is_expired(self) -> bool:
        expires_at = self.expires_at

        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(
                tzinfo=timezone.utc
            )

        return (
            expires_at
            <= datetime.now(timezone.utc)
        )

    @property
    def is_usable(self) -> bool:
        return (
            self.used_at is None
            and not self.is_expired
            and self.attempts
            < self.MAX_ATTEMPTS
        )