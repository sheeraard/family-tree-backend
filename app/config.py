import os
from datetime import timedelta

from dotenv import load_dotenv


load_dotenv()


APP_ENV = (
    os.getenv(
        "APP_ENV",
        "development",
    )
    .strip()
    .lower()
)

IS_PRODUCTION = (
    APP_ENV == "production"
)


def get_secret(
    variable_name,
    development_default,
):
    value = os.getenv(
        variable_name
    )

    if value:
        return value

    if IS_PRODUCTION:
        raise RuntimeError(
            f"{variable_name} must be "
            "set in production"
        )

    return development_default


def get_database_url():
    database_url = os.getenv(
        "DATABASE_URL"
    )

    if not database_url:
        if IS_PRODUCTION:
            raise RuntimeError(
                "DATABASE_URL must be "
                "set in production"
            )

        return (
            "postgresql+psycopg://"
            "localhost/family_tree"
        )

    if database_url.startswith(
        "postgres://"
    ):
        database_url = (
            "postgresql+psycopg://"
            + database_url[
                len(
                    "postgres://"
                ):
            ]
        )

    elif database_url.startswith(
        "postgresql://"
    ):
        database_url = (
            "postgresql+psycopg://"
            + database_url[
                len(
                    "postgresql://"
                ):
            ]
        )

    return database_url


def get_access_token_minutes():
    raw_value = os.getenv(
        "JWT_ACCESS_TOKEN_MINUTES",
        "60",
    )

    try:
        minutes = int(
            raw_value
        )

    except ValueError:
        raise RuntimeError(
            "JWT_ACCESS_TOKEN_MINUTES "
            "must be an integer"
        )

    if minutes < 1:
        raise RuntimeError(
            "JWT_ACCESS_TOKEN_MINUTES "
            "must be at least 1"
        )

    return minutes


def get_rate_limit_storage_uri():
    return os.getenv(
        "RATELIMIT_STORAGE_URI",
        "memory://",
    )


def get_debug_enabled():
    if IS_PRODUCTION:
        return False

    raw_value = os.getenv(
        "FLASK_DEBUG",
        "false",
    )

    return (
        raw_value
        .strip()
        .lower()
        in {
            "1",
            "true",
            "yes",
            "on",
        }
    )


def get_boolean_env(
    name,
    default=False,
):
    raw_value = os.getenv(
        name
    )

    if raw_value is None:
        return default

    return (
        raw_value
        .strip()
        .lower()
        in {
            "1",
            "true",
            "yes",
            "on",
        }
    )


def get_mail_port():
    raw_value = os.getenv(
        "MAIL_SMTP_PORT",
        "587",
    )

    try:
        port = int(
            raw_value
        )
    except ValueError:
        raise RuntimeError(
            "MAIL_SMTP_PORT "
            "must be an integer"
        )

    if (
        port < 1
        or
        port > 65535
    ):
        raise RuntimeError(
            "MAIL_SMTP_PORT "
            "must be between "
            "1 and 65535"
        )

    return port


def get_media_storage_backend():
    default_backend = (
        "s3"
        if IS_PRODUCTION
        else "local"
    )

    backend = (
        os.getenv(
            "MEDIA_STORAGE_BACKEND",
            default_backend,
        )
        .strip()
        .lower()
    )

    if backend not in {
        "local",
        "s3",
    }:
        raise RuntimeError(
            "MEDIA_STORAGE_BACKEND must be "
            "either local or s3"
        )

    if (
        IS_PRODUCTION
        and backend != "s3"
    ):
        raise RuntimeError(
            "MEDIA_STORAGE_BACKEND must be "
            "s3 in production"
        )

    return backend


MEDIA_STORAGE_BACKEND = (
    get_media_storage_backend()
)


def get_object_storage_value(
    variable_name,
    default="",
):
    value = os.getenv(
        variable_name,
        default,
    )

    if isinstance(
        value,
        str,
    ):
        value = value.strip()

    if (
        MEDIA_STORAGE_BACKEND
        == "s3"
        and not value
    ):
        raise RuntimeError(
            f"{variable_name} must be set "
            "when MEDIA_STORAGE_BACKEND=s3"
        )

    return value


def get_s3_url_style():
    style = (
        os.getenv(
            "AWS_S3_URL_STYLE",
            "virtual",
        )
        .strip()
        .lower()
    )

    if style not in {
        "auto",
        "path",
        "virtual",
    }:
        raise RuntimeError(
            "AWS_S3_URL_STYLE must be "
            "auto, path, or virtual"
        )

    return style


class Config:
    #
    # Environment
    #

    ENVIRONMENT = (
        APP_ENV
    )

    IS_PRODUCTION = (
        IS_PRODUCTION
    )

    DEBUG = (
        get_debug_enabled()
    )

    TESTING = False

    #
    # Flask
    #

    SECRET_KEY = get_secret(
        "SECRET_KEY",
        "development-only-secret-key",
    )

    PROPAGATE_EXCEPTIONS = False

    JSON_SORT_KEYS = False

    MAX_CONTENT_LENGTH = (
        10 * 1024 * 1024
    )

    #
    # Database
    #

    SQLALCHEMY_DATABASE_URI = (
        get_database_url()
    )

    SQLALCHEMY_TRACK_MODIFICATIONS = (
        False
    )

    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 300,
    }

    #
    # JWT
    #

    JWT_SECRET_KEY = get_secret(
        "JWT_SECRET_KEY",
        "development-only-jwt-secret",
    )

    JWT_ACCESS_TOKEN_EXPIRES = (
        timedelta(
            minutes=(
                get_access_token_minutes()
            )
        )
    )

    JWT_TOKEN_LOCATION = [
        "headers"
    ]

    JWT_HEADER_NAME = (
        "Authorization"
    )

    JWT_HEADER_TYPE = (
        "Bearer"
    )

    JWT_ERROR_MESSAGE_KEY = (
        "message"
    )

    #
    # Rate limiting
    #

    RATELIMIT_STORAGE_URI = (
        get_rate_limit_storage_uri()
    )

    RATELIMIT_HEADERS_ENABLED = True

    #
    # Media storage
    #

    MEDIA_STORAGE_BACKEND = (
        MEDIA_STORAGE_BACKEND
    )

    AWS_ENDPOINT_URL = (
        get_object_storage_value(
            "AWS_ENDPOINT_URL"
        )
    )

    AWS_ACCESS_KEY_ID = (
        get_object_storage_value(
            "AWS_ACCESS_KEY_ID"
        )
    )

    AWS_SECRET_ACCESS_KEY = (
        get_object_storage_value(
            "AWS_SECRET_ACCESS_KEY"
        )
    )

    AWS_S3_BUCKET_NAME = (
        get_object_storage_value(
            "AWS_S3_BUCKET_NAME"
        )
    )

    AWS_DEFAULT_REGION = (
        os.getenv(
            "AWS_DEFAULT_REGION",
            "auto",
        )
        .strip()
        or "auto"
    )

    AWS_S3_URL_STYLE = (
        get_s3_url_style()
    )

    #
    # Email / SMTP
    #

    MAIL_SMTP_HOST = os.getenv(
        "MAIL_SMTP_HOST",
        "",
    ).strip()

    MAIL_SMTP_PORT = (
        get_mail_port()
    )

    MAIL_SMTP_USERNAME = (
        os.getenv(
            "MAIL_SMTP_USERNAME",
            "",
        )
        .strip()
    )

    MAIL_SMTP_PASSWORD = (
        os.getenv(
            "MAIL_SMTP_PASSWORD",
            "",
        )
    )

    MAIL_FROM = (
        os.getenv(
            "MAIL_FROM",
            "",
        )
        .strip()
    )

    MAIL_FROM_NAME = (
        os.getenv(
            "MAIL_FROM_NAME",
            "GEKRAFS",
        )
        .strip()
    )

    MAIL_SMTP_USE_TLS = (
        get_boolean_env(
            "MAIL_SMTP_USE_TLS",
            True,
        )
    )

    MAIL_SMTP_USE_SSL = (
        get_boolean_env(
            "MAIL_SMTP_USE_SSL",
            False,
        )
    )