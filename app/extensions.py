from flask import request
from flask_jwt_extended import JWTManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy


def get_rate_limit_address():
    railway_ip = (
        request.headers.get(
            "X-Real-IP",
            "",
        )
        .strip()
    )

    if railway_ip:
        return railway_ip

    return get_remote_address()


db = SQLAlchemy()

migrate = Migrate()

jwt = JWTManager()

limiter = Limiter(
    key_func=get_rate_limit_address,
    default_limits=[
        "300 per minute",
        "5000 per hour",
    ],
)