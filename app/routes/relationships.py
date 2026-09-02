from collections import deque
from datetime import datetime, timezone
from uuid import UUID

from flask import (
    Blueprint,
    current_app,
    jsonify,
    request,
)

from flask_jwt_extended import (
    get_jwt_identity,
    jwt_required,
)

from app.extensions import db

from app.models import (
    Person,
    Relationship,
    RelationshipRequest,
    User,
)


relationships_bp = Blueprint(
    "relationships",
    __name__,
)


ALLOWED_RELATIONSHIPS = {
    "parent",
    "child",
    "sibling",
    "spouse",
}


INVERSE_RELATIONSHIPS = {
    "parent": "child",
    "child": "parent",
    "sibling": "sibling",
    "spouse": "spouse",
}


def get_current_user():
    user_id = get_jwt_identity()

    try:
        user_uuid = UUID(
            str(user_id)
        )

    except (
        ValueError,
        TypeError,
    ):
        return None

    return db.session.get(
        User,
        user_uuid,
    )


def get_relationship_between(
    first_person_id,
    second_person_id,
):
    return db.session.scalar(
        db.select(
            Relationship
        )
        .where(
            db.or_(
                db.and_(
                    Relationship.person_a_id
                    == first_person_id,

                    Relationship.person_b_id
                    == second_person_id,
                ),

                db.and_(
                    Relationship.person_a_id
                    == second_person_id,

                    Relationship.person_b_id
                    == first_person_id,
                ),
            )
        )
    )


def get_pending_request_between(
    first_person_id,
    second_person_id,
):
    """
    Find a pending request between two
    people regardless of direction.

    Example:

    A -> B pending

    prevents:

    B -> A pending
    """

    return db.session.scalar(
        db.select(
            RelationshipRequest
        )
        .where(
            RelationshipRequest.status
            == "pending",

            db.or_(
                db.and_(
                    RelationshipRequest
                    .sender_person_id
                    == first_person_id,

                    RelationshipRequest
                    .receiver_person_id
                    == second_person_id,
                ),

                db.and_(
                    RelationshipRequest
                    .sender_person_id
                    == second_person_id,

                    RelationshipRequest
                    .receiver_person_id
                    == first_person_id,
                ),
            ),
        )
    )


def get_parent_ids(
    child_person_id,
):
    """
    Return all direct parents of a person.

    Relationship semantics:

    If relation_a_to_b == "parent":
        person B is person A's parent.

    If relation_a_to_b == "child":
        person A is person B's parent.
    """

    parent_ids = set()

    relationships = (
        db.session.scalars(
            db.select(
                Relationship
            )
            .where(
                db.or_(
                    Relationship.person_a_id
                    == child_person_id,

                    Relationship.person_b_id
                    == child_person_id,
                )
            )
        )
        .all()
    )

    for relationship in relationships:
        if (
            relationship.person_a_id
            == child_person_id
        ):
            relation = (
                relationship
                .relation_a_to_b
            )

            other_person_id = (
                relationship
                .person_b_id
            )

        else:
            relation = (
                relationship
                .relation_b_to_a
            )

            other_person_id = (
                relationship
                .person_a_id
            )

        if relation == "parent":
            parent_ids.add(
                other_person_id
            )

    return parent_ids


def has_ancestor(
    start_person_id,
    target_ancestor_id,
    max_depth=20,
):
    """
    Follow parent links upward.

    Returns True if target_ancestor_id
    already exists somewhere above
    start_person_id.
    """

    if (
        start_person_id
        == target_ancestor_id
    ):
        return True

    queue = deque([
        (
            start_person_id,
            0,
        )
    ])

    visited = {
        start_person_id
    }

    while queue:
        (
            current_person_id,
            depth,
        ) = queue.popleft()

        if depth >= max_depth:
            continue

        parent_ids = get_parent_ids(
            current_person_id
        )

        for parent_id in parent_ids:
            if (
                parent_id
                == target_ancestor_id
            ):
                return True

            if (
                parent_id
                not in visited
            ):
                visited.add(
                    parent_id
                )

                queue.append(
                    (
                        parent_id,
                        depth + 1,
                    )
                )

    return False


def would_create_parent_cycle(
    sender_person_id,
    receiver_person_id,
    relationship_type,
):
    """
    Determine whether a proposed
    parent/child relationship would
    create an ancestry loop.

    Example:

    Johnny Boy -> Tony

    already means Johnny is Tony's parent.

    Trying to make Tony Johnny's parent
    would create:

    Tony
      ↓
    Johnny
      ↓
    Tony
    """

    if relationship_type not in {
        "parent",
        "child",
    }:
        return False

    if relationship_type == "parent":
        child_id = (
            sender_person_id
        )

        parent_id = (
            receiver_person_id
        )

    else:
        child_id = (
            receiver_person_id
        )

        parent_id = (
            sender_person_id
        )

    return has_ancestor(
        parent_id,
        child_id,
    )


def validate_relationship_pair(
    sender,
    receiver,
    relationship_type,
    check_pending=True,
):
    if (
        sender.id
        == receiver.id
    ):
        return (
            "You cannot add yourself "
            "as a relative",
            400,
        )

    existing_relationship = (
        get_relationship_between(
            sender.id,
            receiver.id,
        )
    )

    if existing_relationship:
        return (
            "A relationship between "
            "these people already exists",
            409,
        )

    if check_pending:
        existing_request = (
            get_pending_request_between(
                sender.id,
                receiver.id,
            )
        )

        if existing_request:
            return (
                "A relationship request "
                "between these people "
                "is already pending",
                409,
            )

    if would_create_parent_cycle(
        sender.id,
        receiver.id,
        relationship_type,
    ):
        return (
            "This parent-child "
            "relationship would create "
            "an ancestry cycle",
            409,
        )

    return None


def server_error_response(
    message,
    error,
):
    """
    Development:
        include the raw exception.

    Production:
        hide internal details.
    """

    response = {
        "message": message
    }

    if current_app.config[
        "DEBUG"
    ]:
        response["error"] = str(
            error
        )

    return jsonify(
        response
    ), 500


@relationships_bp.route(
    "/requests",
    methods=["POST"],
)
@jwt_required()
def send_relationship_request():
    user = get_current_user()

    if not user:
        return jsonify({
            "message": (
                "Invalid token identity"
            )
        }), 401

    if not user.person:
        return jsonify({
            "message": (
                "User profile not found"
            )
        }), 404

    sender = user.person

    data = request.get_json(
        silent=True
    )

    if not data:
        return jsonify({
            "message": (
                "Request body must be JSON"
            )
        }), 400

    receiver_id_raw = data.get(
        "receiver_person_id"
    )

    relationship_type = str(
        data.get(
            "relationship_type",
            "",
        )
    ).strip().lower()

    if not receiver_id_raw:
        return jsonify({
            "message": (
                "receiver_person_id "
                "is required"
            )
        }), 400

    try:
        receiver_uuid = UUID(
            str(
                receiver_id_raw
            )
        )

    except (
        ValueError,
        TypeError,
    ):
        return jsonify({
            "message": (
                "Invalid "
                "receiver_person_id"
            )
        }), 400

    if (
        relationship_type
        not in ALLOWED_RELATIONSHIPS
    ):
        return jsonify({
            "message": (
                "relationship_type must be "
                "parent, child, sibling, "
                "or spouse"
            )
        }), 400

    receiver = db.session.get(
        Person,
        receiver_uuid,
    )

    if not receiver:
        return jsonify({
            "message": (
                "Person not found"
            )
        }), 404

    if (
        receiver.user_id
        is None
    ):
        return jsonify({
            "message": (
                "This person does not "
                "have an account and "
                "cannot receive "
                "requests yet"
            )
        }), 400

    validation_error = (
        validate_relationship_pair(
            sender,
            receiver,
            relationship_type,
            check_pending=True,
        )
    )

    if validation_error:
        (
            message,
            status_code,
        ) = validation_error

        return jsonify({
            "message": message
        }), status_code

    relationship_request = (
        RelationshipRequest(
            sender_person_id=(
                sender.id
            ),

            receiver_person_id=(
                receiver.id
            ),

            relationship_type=(
                relationship_type
            ),

            status="pending",
        )
    )

    try:
        db.session.add(
            relationship_request
        )

        db.session.commit()

        return jsonify({
            "message": (
                "Relationship request sent"
            ),

            "request": {
                "id": str(
                    relationship_request.id
                ),

                "sender": {
                    "id": str(
                        sender.id
                    ),

                    "full_name": (
                        sender.full_name
                    ),
                },

                "receiver": {
                    "id": str(
                        receiver.id
                    ),

                    "full_name": (
                        receiver.full_name
                    ),
                },

                "relationship_type": (
                    relationship_request
                    .relationship_type
                ),

                "status": (
                    relationship_request
                    .status
                ),
            },
        }), 201

    except Exception as error:
        db.session.rollback()

        return server_error_response(
            (
                "Failed to send "
                "relationship request"
            ),
            error,
        )


@relationships_bp.route(
    "/requests/incoming",
    methods=["GET"],
)
@jwt_required()
def get_incoming_requests():
    user = get_current_user()

    if not user:
        return jsonify({
            "message": (
                "Invalid token identity"
            )
        }), 401

    if not user.person:
        return jsonify({
            "message": (
                "User profile not found"
            )
        }), 404

    person = user.person

    requests = (
        db.session.scalars(
            db.select(
                RelationshipRequest
            )
            .where(
                RelationshipRequest
                .receiver_person_id
                == person.id,

                RelationshipRequest.status
                == "pending",
            )
            .order_by(
                RelationshipRequest
                .created_at
                .desc()
            )
        )
        .all()
    )

    results = []

    for relationship_request in requests:
        results.append({
            "id": str(
                relationship_request.id
            ),

            "sender": {
                "id": str(
                    relationship_request
                    .sender.id
                ),

                "full_name": (
                    relationship_request
                    .sender
                    .full_name
                ),

                "photo_url": (
                    relationship_request
                    .sender
                    .photo_url
                ),
            },

            "relationship_type": (
                relationship_request
                .relationship_type
            ),

            "status": (
                relationship_request
                .status
            ),

            "created_at": (
                relationship_request
                .created_at
                .isoformat()
                if (
                    relationship_request
                    .created_at
                )
                else None
            ),
        })

    return jsonify({
        "requests": results
    }), 200


@relationships_bp.route(
    "/requests/<request_id>/accept",
    methods=["POST"],
)
@jwt_required()
def accept_relationship_request(
    request_id,
):
    user = get_current_user()

    if not user:
        return jsonify({
            "message": (
                "Invalid token identity"
            )
        }), 401

    if not user.person:
        return jsonify({
            "message": (
                "User profile not found"
            )
        }), 404

    try:
        request_uuid = UUID(
            str(
                request_id
            )
        )

    except (
        ValueError,
        TypeError,
    ):
        return jsonify({
            "message": (
                "Invalid ID"
            )
        }), 400

    relationship_request = (
        db.session.get(
            RelationshipRequest,
            request_uuid,
        )
    )

    if not relationship_request:
        return jsonify({
            "message": (
                "Relationship request "
                "not found"
            )
        }), 404

    if (
        relationship_request
        .receiver_person_id
        != user.person.id
    ):
        return jsonify({
            "message": (
                "You cannot respond "
                "to this request"
            )
        }), 403

    if (
        relationship_request.status
        != "pending"
    ):
        return jsonify({
            "message": (
                "Request has already "
                "been processed"
            )
        }), 409

    sender = (
        relationship_request.sender
    )

    receiver = (
        relationship_request.receiver
    )

    relationship_type = (
        relationship_request
        .relationship_type
    )

    existing_relationship = (
        get_relationship_between(
            sender.id,
            receiver.id,
        )
    )

    if existing_relationship:
        return jsonify({
            "message": (
                "A relationship between "
                "these people already exists"
            )
        }), 409

    if would_create_parent_cycle(
        sender.id,
        receiver.id,
        relationship_type,
    ):
        return jsonify({
            "message": (
                "This parent-child "
                "relationship would create "
                "an ancestry cycle"
            )
        }), 409

    relation_a_to_b = (
        relationship_type
    )

    relation_b_to_a = (
        INVERSE_RELATIONSHIPS[
            relation_a_to_b
        ]
    )

    relationship = Relationship(
        person_a_id=(
            sender.id
        ),

        person_b_id=(
            receiver.id
        ),

        relation_a_to_b=(
            relation_a_to_b
        ),

        relation_b_to_a=(
            relation_b_to_a
        ),

        verification_status=(
            "verified"
        ),
    )

    relationship_request.status = (
        "accepted"
    )

    relationship_request.responded_at = (
        datetime.now(
            timezone.utc
        )
    )

    try:
        db.session.add(
            relationship
        )

        db.session.commit()

        return jsonify({
            "message": (
                "Relationship request "
                "accepted"
            ),

            "relationship": {
                "id": str(
                    relationship.id
                ),

                "person_a": {
                    "id": str(
                        sender.id
                    ),

                    "full_name": (
                        sender.full_name
                    ),

                    "relationship": (
                        relation_a_to_b
                    ),
                },

                "person_b": {
                    "id": str(
                        receiver.id
                    ),

                    "full_name": (
                        receiver.full_name
                    ),

                    "relationship": (
                        relation_b_to_a
                    ),
                },

                "verification_status": (
                    relationship
                    .verification_status
                ),
            },
        }), 201

    except Exception as error:
        db.session.rollback()

        return server_error_response(
            (
                "Failed to accept "
                "relationship request"
            ),
            error,
        )


@relationships_bp.route(
    "/requests/<request_id>/reject",
    methods=["POST"],
)
@jwt_required()
def reject_relationship_request(
    request_id,
):
    user = get_current_user()

    if not user:
        return jsonify({
            "message": (
                "Invalid token identity"
            )
        }), 401

    if not user.person:
        return jsonify({
            "message": (
                "User profile not found"
            )
        }), 404

    try:
        request_uuid = UUID(
            str(
                request_id
            )
        )

    except (
        ValueError,
        TypeError,
    ):
        return jsonify({
            "message": (
                "Invalid ID"
            )
        }), 400

    relationship_request = (
        db.session.get(
            RelationshipRequest,
            request_uuid,
        )
    )

    if not relationship_request:
        return jsonify({
            "message": (
                "Relationship request "
                "not found"
            )
        }), 404

    if (
        relationship_request
        .receiver_person_id
        != user.person.id
    ):
        return jsonify({
            "message": (
                "You cannot respond "
                "to this request"
            )
        }), 403

    if (
        relationship_request.status
        != "pending"
    ):
        return jsonify({
            "message": (
                "Request has already "
                "been processed"
            )
        }), 409

    relationship_request.status = (
        "rejected"
    )

    relationship_request.responded_at = (
        datetime.now(
            timezone.utc
        )
    )

    try:
        db.session.commit()

        return jsonify({
            "message": (
                "Relationship request "
                "rejected"
            )
        }), 200

    except Exception as error:
        db.session.rollback()

        return server_error_response(
            (
                "Failed to reject "
                "relationship request"
            ),
            error,
        )