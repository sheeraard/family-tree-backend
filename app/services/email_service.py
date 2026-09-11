import smtplib
from email.message import (
    EmailMessage,
)

from flask import current_app


def _mail_is_configured():
    required_values = [
        current_app.config.get(
            "MAIL_SMTP_HOST"
        ),
        current_app.config.get(
            "MAIL_SMTP_USERNAME"
        ),
        current_app.config.get(
            "MAIL_SMTP_PASSWORD"
        ),
        current_app.config.get(
            "MAIL_FROM"
        ),
    ]

    return all(
        bool(value)
        for value
        in required_values
    )


def _open_smtp_connection():
    host = (
        current_app.config[
            "MAIL_SMTP_HOST"
        ]
    )

    port = (
        current_app.config[
            "MAIL_SMTP_PORT"
        ]
    )

    use_ssl = (
        current_app.config[
            "MAIL_SMTP_USE_SSL"
        ]
    )

    use_tls = (
        current_app.config[
            "MAIL_SMTP_USE_TLS"
        ]
    )

    if use_ssl:
        connection = (
            smtplib.SMTP_SSL(
                host,
                port,
                timeout=15,
            )
        )
    else:
        connection = (
            smtplib.SMTP(
                host,
                port,
                timeout=15,
            )
        )

        connection.ehlo()

        if use_tls:
            connection.starttls()
            connection.ehlo()

    return connection


def send_email(
    *,
    recipient,
    subject,
    text_body,
):
    if not _mail_is_configured():
        if current_app.config.get(
            "IS_PRODUCTION",
            False,
        ):
            raise RuntimeError(
                "SMTP email delivery "
                "is not configured"
            )

        current_app.logger.warning(
            "Development email "
            "delivery fallback.\n"
            "Recipient: %s\n"
            "Subject: %s\n"
            "%s",
            recipient,
            subject,
            text_body,
        )

        return

    message = EmailMessage()

    from_name = (
        current_app.config[
            "MAIL_FROM_NAME"
        ]
    )

    from_email = (
        current_app.config[
            "MAIL_FROM"
        ]
    )

    message[
        "From"
    ] = (
        f"{from_name} "
        f"<{from_email}>"
    )

    message[
        "To"
    ] = recipient

    message[
        "Subject"
    ] = subject

    message.set_content(
        text_body
    )

    username = (
        current_app.config[
            "MAIL_SMTP_USERNAME"
        ]
    )

    password = (
        current_app.config[
            "MAIL_SMTP_PASSWORD"
        ]
    )

    with _open_smtp_connection() as smtp:
        smtp.login(
            username,
            password,
        )

        smtp.send_message(
            message
        )


def send_password_reset_code(
    *,
    recipient,
    code,
):
    subject = (
        "Kode Reset Password GEKRAFS"
    )

    text_body = (
        "Kami menerima permintaan "
        "untuk mengatur ulang "
        "password akun GEKRAFS Anda.\n\n"

        f"Kode reset Anda: {code}\n\n"

        "Kode ini berlaku selama "
        "15 menit.\n\n"

        "Jika Anda tidak meminta "
        "reset password, abaikan "
        "email ini.\n\n"

        "GEKRAFS"
    )

    send_email(
        recipient=recipient,
        subject=subject,
        text_body=text_body,
    )