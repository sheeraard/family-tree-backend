from flask import Flask
from dotenv import load_dotenv

from app.config import Config

from app.extensions import (
    db,
    jwt,
    limiter,
    migrate,
)

from app.routes.family import (
    family_bp,
)

from app.utils.error_handlers import (
    register_error_handlers,
)

from app.utils.product_guard import (
    register_product_guard,
)


def apply_rate_limits(
    app,
):
    limits = {
        "auth.register":
            "5 per hour",

        "auth.login":
            "10 per minute",

        "people.search_people":
            "30 per minute",

        "people.get_person_claim_code":
            "5 per hour",

        "people.create_non_user_relative":
            "20 per hour",

        "relationships.send_relationship_request":
            "20 per hour",

        "products.create_product":
            "20 per hour",

        "products.update_product":
            "60 per hour",

        "products.delete_product":
            "30 per hour",

        "products.upload_product_image":
            "20 per hour",

        "community.create_post":
            "30 per hour",

        "community.delete_post":
            "30 per hour",

        "culture.create_culture_content":
            "20 per hour",

        "culture.update_culture_content":
            "60 per hour",

        "culture.delete_culture_content":
            "30 per hour",

        "historical_tree.create_historical_person":
            "30 per hour",

        "historical_tree.update_historical_person":
            "60 per hour",

        "historical_tree.delete_historical_person":
            "30 per hour",

        "historical_tree.create_historical_relationship":
            "60 per hour",

        "historical_tree.delete_historical_relationship":
            "60 per hour",

        "umkm.create_application":
            "5 per hour",

        "umkm.review_application":
            "30 per hour",

        "password_reset.request_password_reset":
            "3 per 15 minutes",

        "password_reset.confirm_password_reset":
            "10 per 15 minutes",
    }

    for (
        endpoint,
        limit_value,
    ) in limits.items():

        view_function = (
            app.view_functions.get(
                endpoint
            )
        )

        if view_function is None:
            raise RuntimeError(
                "Rate-limit configuration "
                "references missing endpoint: "
                f"{endpoint}"
            )

        app.view_functions[
            endpoint
        ] = limiter.limit(
            limit_value
        )(
            view_function
        )


def create_app():
    load_dotenv()

    app = Flask(
        __name__
    )

    app.config.from_object(
        Config
    )

    #
    # Extensions
    #

    db.init_app(
        app
    )

    migrate.init_app(
        app,
        db,
    )

    jwt.init_app(
        app
    )

    limiter.init_app(
        app
    )

    #
    # Import models so Flask-Migrate
    # can discover all tables.
    #

    from app import models

    #
    # Blueprints
    #

    from app.routes.health import (
        health_bp,
    )

    from app.routes.auth import (
        auth_bp,
    )

    from app.routes.password_reset import (
        password_reset_bp,
    )

    from app.routes.profile import (
        profile_bp,
    )

    from app.routes.people import (
        people_bp,
    )

    from app.routes.relationships import (
        relationships_bp,
    )

    from app.routes.products import (
        products_bp,
    )

    from app.routes.product_access import (
        product_access_bp,
    )

    from app.routes.community import (
        community_bp,
    )

    from app.routes.culture import (
        culture_bp,
    )

    from app.routes.historical_tree import (
        historical_tree_bp,
    )

    from app.routes.umkm import (
        umkm_bp,
    )

    #
    # Register blueprints
    #

    app.register_blueprint(
        health_bp,
        url_prefix="/api",
    )

    app.register_blueprint(
        auth_bp,
        url_prefix="/api/auth",
    )

    app.register_blueprint(
        password_reset_bp,
        url_prefix=(
            "/api/auth/password-reset"
        ),
    )

    app.register_blueprint(
        profile_bp,
        url_prefix="/api/profile",
    )

    app.register_blueprint(
        people_bp,
        url_prefix="/api/people",
    )

    app.register_blueprint(
        relationships_bp,
        url_prefix="/api/relationships",
    )

    app.register_blueprint(
        family_bp,
        url_prefix="/api/family",
    )

    app.register_blueprint(
        products_bp,
        url_prefix="/api/products",
    )

    app.register_blueprint(
        product_access_bp,
        url_prefix="/api/products",
    )

    app.register_blueprint(
        community_bp,
        url_prefix="/api/community",
    )

    app.register_blueprint(
        culture_bp,
        url_prefix="/api/culture",
    )

    app.register_blueprint(
        historical_tree_bp,
        url_prefix=(
            "/api/historical-tree"
        ),
    )

    app.register_blueprint(
        umkm_bp,
        url_prefix="/api/umkm",
    )

    app.register_blueprint(
        email_verification_bp,
        url_prefix=(
            "/api/auth/"
            "email-verification"
        ),
    )

    #
    # Global guards
    #

    register_product_guard(
        app
    )

    #
    # Rate limits
    #

    apply_rate_limits(
        app
    )

    #
    # JSON error responses
    #

    register_error_handlers(
        app
    )

    from app.routes.email_verification import (
        email_verification_bp,
    )

    return app