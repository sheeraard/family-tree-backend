from flask import jsonify
from werkzeug.exceptions import HTTPException

from app.extensions import db


HTTP_ERROR_MESSAGES = {
    400: "Bad request.",
    401: "Authentication required.",
    403: "You do not have permission to perform this action.",
    404: "Endpoint not found.",
    405: "Method not allowed.",
    409: "Request conflicts with the current state.",
    413: "Uploaded file or request body is too large.",
    415: "Unsupported media type.",
    422: "Unable to process the request.",
    429: "Too many requests. Please try again later.",
}


def register_error_handlers(
    app,
):
    @app.errorhandler(
        HTTPException
    )
    def handle_http_exception(
        error,
    ):
        status_code = (
            error.code or 500
        )

        message = (
            HTTP_ERROR_MESSAGES.get(
                status_code
            )
            or error.description
            or "Request failed."
        )

        response = {
            "message": message,
            "status": status_code,
        }

        if status_code == 429:
            retry_after = getattr(
                error,
                "retry_after",
                None,
            )

            if retry_after is not None:
                response[
                    "retry_after"
                ] = retry_after

        return jsonify(
            response
        ), status_code

    @app.errorhandler(
        Exception
    )
    def handle_unexpected_exception(
        error,
    ):
        #
        # An exception during a database
        # operation can leave the SQLAlchemy
        # session unusable until rollback.
        #
        try:
            db.session.rollback()
        except Exception:
            pass

        #
        # Log the real exception on the
        # backend / Railway logs, but do not
        # send stack traces or database
        # details to the mobile client.
        #
        app.logger.exception(
            "Unhandled application error",
            exc_info=error,
        )

        return jsonify({
            "message": (
                "Internal server error."
            ),
            "status": 500,
        }), 500