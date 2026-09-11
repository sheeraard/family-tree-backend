import smtplib
import ssl

from email.message import EmailMessage

from flask import current_app


def _email_is_configured() -> bool:
    return bool(
        current_app.config.get("MAIL_SMTP_HOST")
        and current_app.config.get("MAIL_SMTP_PORT")
        and current_app.config.get("MAIL_SMTP_USERNAME")
        and current_app.config.get("MAIL_SMTP_PASSWORD")
        and current_app.config.get("MAIL_FROM")
    )


def _open_smtp_connection():
    host = current_app.config["MAIL_SMTP_HOST"]
    port = int(current_app.config["MAIL_SMTP_PORT"])

    use_tls = bool(
        current_app.config.get("MAIL_SMTP_USE_TLS")
    )

    use_ssl = bool(
        current_app.config.get("MAIL_SMTP_USE_SSL")
    )

    username = current_app.config[
        "MAIL_SMTP_USERNAME"
    ]

    password = current_app.config[
        "MAIL_SMTP_PASSWORD"
    ]

    if use_ssl:
        context = ssl.create_default_context()

        smtp = smtplib.SMTP_SSL(
            host,
            port,
            timeout=15,
            context=context,
        )

        smtp.login(
            username,
            password,
        )

        return smtp

    smtp = smtplib.SMTP(
        host,
        port,
        timeout=15,
    )

    smtp.ehlo()

    if use_tls:
        context = ssl.create_default_context()

        smtp.starttls(
            context=context,
        )

        smtp.ehlo()

    smtp.login(
        username,
        password,
    )

    return smtp


def send_email(
    *,
    recipient: str,
    subject: str,
    text_body: str,
    html_body: str | None = None,
):
    if not _email_is_configured():
        if current_app.config.get("IS_PRODUCTION"):
            raise RuntimeError(
                "SMTP email delivery is not configured"
            )

        current_app.logger.warning(
            (
                "SMTP email delivery is not configured.\n"
                "Development email:\n"
                "To: %s\n"
                "Subject: %s\n\n"
                "%s"
            ),
            recipient,
            subject,
            text_body,
        )

        return None

    sender_email = current_app.config["MAIL_FROM"]

    sender_name = current_app.config.get(
        "MAIL_FROM_NAME",
        "GEKRAFS",
    )

    message = EmailMessage()

    message["From"] = (
        f"{sender_name} <{sender_email}>"
    )

    message["To"] = recipient

    message["Subject"] = subject

    message.set_content(
        text_body
    )

    if html_body:
        message.add_alternative(
            html_body,
            subtype="html",
        )

    with _open_smtp_connection() as smtp:
        smtp.send_message(
            message
        )

    return True


def send_password_reset_code(
    *,
    recipient: str,
    code: str,
):
    subject = "Kode Reset Password GEKRAFS"

    text_body = f"""Halo,

Kami menerima permintaan untuk mereset password akun GEKRAFS Anda.

Kode reset password Anda:

{code}

Kode ini berlaku selama 15 menit.

Jika Anda tidak meminta reset password, abaikan email ini.

GEKRAFS
"""

    html_body = f"""
<!DOCTYPE html>
<html lang="id">
<body>
    <p>Halo,</p>

    <p>
        Kami menerima permintaan untuk mereset
        password akun GEKRAFS Anda.
    </p>

    <p>Kode reset password Anda:</p>

    <div
        style="
            font-size: 28px;
            font-weight: bold;
            letter-spacing: 6px;
            margin: 24px 0;
        "
    >
        {code}
    </div>

    <p>
        Kode ini berlaku selama
        <strong>15 menit</strong>.
    </p>

    <p>
        Jika Anda tidak meminta reset password,
        abaikan email ini.
    </p>

    <p>GEKRAFS</p>
</body>
</html>
"""

    return send_email(
        recipient=recipient,
        subject=subject,
        text_body=text_body,
        html_body=html_body,
    )