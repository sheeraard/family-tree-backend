from flask import Blueprint, jsonify
from sqlalchemy import text

from app.extensions import db


health_bp = Blueprint("health", __name__)


@health_bp.route("/health", methods=["GET"])
def health():
    try:
        db.session.execute(text("SELECT 1"))

        return jsonify({
            "status": "ok",
            "api": "running",
            "database": "connected"
        }), 200

    except Exception as error:
        return jsonify({
            "status": "error",
            "api": "running",
            "database": "disconnected",
            "error": str(error)
        }), 500