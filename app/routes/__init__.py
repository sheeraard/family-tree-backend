from flask import Flask


def create_app():
    app = Flask(__name__)

    from app.routes.health import health_bp

    app.register_blueprint(
        health_bp,
        url_prefix="/api"
    )

    return app