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

    #
    # Railway / Render / other hosts
    # may provide:
    #
    # postgres://...
    # postgresql://...
    #
    # This project uses Psycopg 3.
    #

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
    """
    Development default:
        memory://

    Production can later use Redis:
        redis://...

    If multiple Gunicorn instances /
    containers are used, Redis is preferred
    so all workers share the same counters.
    """

    return os.getenv(
        "RATELIMIT_STORAGE_URI",
        "memory://",
    )


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
        not IS_PRODUCTION
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