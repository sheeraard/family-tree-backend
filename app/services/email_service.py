import requests

from flask import current_app


RESEND_API_URL = "https://api.resend.com/emails"


def _email_is_configured() -> bool:
    return bool(
        current_app.config.get("RESEND_API_KEY")
        and current_app.config.get("MAIL_FROM")
    )


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
                "Email service is not configured."
            )

        current_app.logger.warning(
            (
                "Email service is not configured.\n"
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

    api_key = current_app.config["RESEND_API_KEY"]
    sender_email = current_app.config["MAIL_FROM"]
    sender_name = current_app.config.get(
        "MAIL_FROM_NAME",
        "GEKRAFS",
    )

    payload = {
        "from": f"{sender_name} <{sender_email}>",
        "to": [recipient],
        "subject": subject,
        "text": text_body,
    }

    if html_body:
        payload["html"] = html_body

    try:
        response = requests.post(
            RESEND_API_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "User-Agent": "GEKRAFS-Backend/1.0",
            },
            json=payload,
            timeout=15,
        )

        if not response.ok:
            current_app.logger.error(
                "Resend API error. HTTP %s: %s",
                response.status_code,
                response.text,
            )

            raise RuntimeError(
                (
                    "Email provider returned "
                    f"HTTP {response.status_code}."
                )
            )

        if not response.content:
            return None

        return response.json()

    except requests.RequestException as error:
        current_app.logger.error(
            "Unable to connect to Resend: %s",
            error,
        )

        raise RuntimeError(
            "Unable to connect to email provider."
        ) from error


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