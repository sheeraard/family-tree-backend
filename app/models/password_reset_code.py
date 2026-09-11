import hashlib
import hmac
import uuid
from datetime import datetime, timezone

from flask import current_app
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import UUID

from app.extensions import db


class PasswordResetCode(
    db.Model
):
    __tablename__ = (
        "password_reset_codes"
    )

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
        db.DateTime(
            timezone=True
        ),
        nullable=False,
        index=True,
    )

    used_at = db.Column(
        db.DateTime(
            timezone=True
        ),
        nullable=True,
    )

    created_at = db.Column(
        db.DateTime(
            timezone=True
        ),
        nullable=False,
        server_default=func.now(),
    )

    user = db.relationship(
        "User",
    )

    @staticmethod
    def _hash_code(
        code,
    ):
        secret = (
            current_app.config[
                "SECRET_KEY"
            ]
            .encode("utf-8")
        )

        return hmac.new(
            secret,
            code.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    def set_code(
        self,
        code,
    ):
        self.code_hash = (
            self._hash_code(
                code
            )
        )

    def check_code(
        self,
        code,
    ):
        expected = (
            self._hash_code(
                code
            )
        )

        return hmac.compare_digest(
            self.code_hash,
            expected,
        )

    @property
    def expired(self):
        now = datetime.now(
            timezone.utc
        )

        expires_at = (
            self.expires_at
        )

        if (
            expires_at.tzinfo
            is None
        ):
            expires_at = (
                expires_at.replace(
                    tzinfo=timezone.utc
                )
            )

        return now >= expires_at

    @property
    def usable(self):
        return (
            self.used_at is None
            and
            not self.expired
            and
            self.attempts < 5
        )