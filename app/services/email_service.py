import json
import urllib.error
import urllib.request

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

    request = urllib.request.Request(
        RESEND_API_URL,
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=15,
        ) as response:
            response_body = response.read().decode(
                "utf-8"
            )

            if not response_body:
                return None

            return json.loads(response_body)

    except urllib.error.HTTPError as error:
        error_body = error.read().decode(
            "utf-8",
            errors="replace",
        )

        current_app.logger.error(
            "Resend API error. HTTP %s: %s",
            error.code,
            error_body,
        )

        raise RuntimeError(
            (
                "Email provider returned "
                f"HTTP {error.code}."
            )
        ) from error

    except urllib.error.URLError as error:
        current_app.logger.error(
            "Unable to connect to Resend: %s",
            error.reason,
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

    html_body = f"""\
<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta
        name="viewport"
        content="width=device-width, initial-scale=1.0"
    >
    <title>Kode Reset Password GEKRAFS</title>
</head>
<body
    style="
        margin: 0;
        padding: 0;
        background-color: #f5f5f5;
        font-family: Arial, sans-serif;
    "
>
    <div
        style="
            max-width: 560px;
            margin: 0 auto;
            padding: 32px 20px;
        "
    >
        <div
            style="
                background-color: #ffffff;
                border-radius: 12px;
                padding: 32px;
            "
        >
            <h2
                style="
                    margin-top: 0;
                    margin-bottom: 24px;
                "
            >
                Reset Password GEKRAFS
            </h2>

            <p>Halo,</p>

            <p>
                Kami menerima permintaan untuk
                mereset password akun GEKRAFS Anda.
            </p>

            <p>
                Gunakan kode berikut untuk
                melanjutkan:
            </p>

            <div
                style="
                    margin: 28px 0;
                    padding: 18px;
                    background-color: #f3f3f3;
                    border-radius: 8px;
                    text-align: center;
                    font-size: 30px;
                    font-weight: bold;
                    letter-spacing: 8px;
                "
            >
                {code}
            </div>

            <p>
                Kode ini berlaku selama
                <strong>15 menit</strong>.
            </p>

            <p>
                Jika Anda tidak meminta reset
                password, abaikan email ini.
            </p>

            <p
                style="
                    margin-top: 32px;
                    margin-bottom: 0;
                "
            >
                GEKRAFS
            </p>
        </div>
    </div>
</body>
</html>
"""

    return send_email(
        recipient=recipient,
        subject=subject,
        text_body=text_body,
        html_body=html_body,
    )