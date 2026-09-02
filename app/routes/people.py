import hashlib
import secrets

from collections import deque
from datetime import (
    date,
    datetime,
    timedelta,
    timezone,
)
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
    User,
)


people_bp = Blueprint(
    "people",
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


CLAIM_CODE_VALID_DAYS = 7


def server_error_response(
    message,
    error,
):
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


def hash_claim_code(
    claim_code,
):
    return hashlib.sha256(
        claim_code.encode(
            "utf-8"
        )
    ).hexdigest()


def generate_claim_code():
    """
    Return:

    (
        raw code shown to user,
        SHA-256 hash stored in DB,
        expiration datetime
    )
    """

    while True:
        raw_code = (
            secrets.token_urlsafe(16)
        )

        code_hash = hash_claim_code(
            raw_code
        )

        existing = db.session.scalar(
            db.select(Person).where(
                Person.claim_code_hash
                == code_hash
            )
        )

        if not existing:
            break

    expires_at = (
        datetime.now(
            timezone.utc
        )
        + timedelta(
            days=CLAIM_CODE_VALID_DAYS
        )
    )

    return (
        raw_code,
        code_hash,
        expires_at,
    )


def is_person_in_family_network(
    root_person_id,
    target_person_id,
    max_depth=6,
):
    if (
        root_person_id
        == target_person_id
    ):
        return True

    queue = deque([
        (
            root_person_id,
            0,
        )
    ])

    visited = {
        root_person_id
    }

    while queue:
        (
            current_person_id,
            depth,
        ) = queue.popleft()

        if depth >= max_depth:
            continue

        relationships = (
            db.session.scalars(
                db.select(
                    Relationship
                )
                .where(
                    db.or_(
                        Relationship
                        .person_a_id
                        == current_person_id,

                        Relationship
                        .person_b_id
                        == current_person_id,
                    )
                )
            )
            .all()
        )

        for relationship in relationships:
            if (
                relationship.person_a_id
                == current_person_id
            ):
                relative_id = (
                    relationship.person_b_id
                )

            else:
                relative_id = (
                    relationship.person_a_id
                )

            if (
                relative_id
                == target_person_id
            ):
                return True

            if (
                relative_id
                not in visited
            ):
                visited.add(
                    relative_id
                )

                queue.append(
                    (
                        relative_id,
                        depth + 1,
                    )
                )

    return False


def find_duplicate_direct_relative(
    target_person,
    full_name,
    relationship_type,
    birth_date,
):
    normalized_name = (
        full_name
        .strip()
        .casefold()
    )

    relationships = (
        db.session.scalars(
            db.select(
                Relationship
            )
            .where(
                db.or_(
                    Relationship.person_a_id
                    == target_person.id,

                    Relationship.person_b_id
                    == target_person.id,
                )
            )
        )
        .all()
    )

    for relationship in relationships:
        if (
            relationship.person_a_id
            == target_person.id
        ):
            relative = (
                relationship.person_b
            )

            target_to_relative = (
                relationship
                .relation_a_to_b
            )

        else:
            relative = (
                relationship.person_a
            )

            target_to_relative = (
                relationship
                .relation_b_to_a
            )

        if (
            target_to_relative
            != relationship_type
        ):
            continue

        if (
            relative.full_name
            .strip()
            .casefold()
            != normalized_name
        ):
            continue

        if birth_date is not None:
            if (
                relative.birth_date
                != birth_date
            ):
                continue

        return relative

    return None


@people_bp.route(
    "/search",
    methods=["GET"],
)
@jwt_required()
def search_people():
    query = str(
        request.args.get(
            "q",
            "",
        )
    ).strip()

    if len(query) < 2:
        return jsonify({
            "message": (
                "Search query must contain "
                "at least 2 characters"
            )
        }), 400

    search_term = (
        f"%{query}%"
    )

    people = (
        db.session.scalars(
            db.select(
                Person
            )
            .outerjoin(
                User,
                Person.user_id
                == User.id,
            )
            .where(
                db.or_(
                    Person.full_name
                    .ilike(
                        search_term
                    ),

                    User.email
                    .ilike(
                        search_term
                    ),
                )
            )
            .limit(20)
        )
        .all()
    )

    results = []

    for person in people:
        results.append({
            "id": str(
                person.id
            ),

            "full_name": (
                person.full_name
            ),

            "photo_url": (
                person.photo_url
            ),

            "has_account": (
                person.user_id
                is not None
            ),
        })

    return jsonify({
        "results": results
    }), 200


@people_bp.route(
    "/<person_id>/claim-code",
    methods=["GET"],
)
@jwt_required()
def get_person_claim_code(
    person_id,
):
    user = get_current_user()

    if not user:
        return jsonify({
            "message": (
                "Invalid user"
            )
        }), 401

    if not user.person:
        return jsonify({
            "message": (
                "User profile not found"
            )
        }), 404

    try:
        person_uuid = UUID(
            str(person_id)
        )

    except (
        ValueError,
        TypeError,
    ):
        return jsonify({
            "message": (
                "Invalid person ID"
            )
        }), 400

    person = db.session.get(
        Person,
        person_uuid,
    )

    if not person:
        return jsonify({
            "message": (
                "Person not found"
            )
        }), 404

    if not is_person_in_family_network(
        user.person.id,
        person.id,
    ):
        return jsonify({
            "message": (
                "This person is not in "
                "your family network"
            )
        }), 403

    if (
        person.user_id
        is not None
    ):
        return jsonify({
            "message": (
                "This person already has "
                "a registered account"
            )
        }), 409

    if (
        person.created_by_user_id
        != user.id
    ):
        return jsonify({
            "message": (
                "Only the person who created "
                "this profile can create "
                "its claim code"
            )
        }), 403

    try:
        (
            raw_code,
            code_hash,
            expires_at,
        ) = generate_claim_code()

        # Every time the creator opens the
        # invite action, create a brand-new
        # code.
        #
        # The old code immediately stops
        # working.

        person.claim_code_hash = (
            code_hash
        )

        person.claim_code_expires_at = (
            expires_at
        )

        db.session.commit()

        return jsonify({
            "person": {
                "id": str(
                    person.id
                ),

                "full_name": (
                    person.full_name
                ),

                "has_account": False,
            },

            "claim_code": (
                raw_code
            ),

            "expires_at": (
                expires_at.isoformat()
            ),

            "expires_in_days": (
                CLAIM_CODE_VALID_DAYS
            ),
        }), 200

    except Exception as error:
        db.session.rollback()

        return server_error_response(
            (
                "Failed to create "
                "claim code"
            ),
            error,
        )


def get_explicit_parent_people(
    person_id,
):
    """
    Return parents explicitly stored for a person.

    This deliberately ignores inferred graph edges.

    If a sibling is added, the new sibling gets
    the target person's actual stored parents.

    No generation guessing.
    No uncle guessing.
    No spouse guessing.
    """

    relationships = (
        db.session.scalars(
            db.select(
                Relationship
            )
            .where(
                db.or_(
                    Relationship.person_a_id
                    == person_id,

                    Relationship.person_b_id
                    == person_id,
                )
            )
        )
        .all()
    )

    parent_ids = set()

    for relationship in relationships:
        if (
            relationship.person_a_id
            == person_id
        ):
            if (
                relationship
                .relation_a_to_b
                == "parent"
            ):
                parent_ids.add(
                    relationship
                    .person_b_id
                )

        else:
            if (
                relationship
                .relation_b_to_a
                == "parent"
            ):
                parent_ids.add(
                    relationship
                    .person_a_id
                )

    if not parent_ids:
        return []

    return (
        db.session.scalars(
            db.select(
                Person
            )
            .where(
                Person.id.in_(
                    parent_ids
                )
            )
        )
        .all()
    )


@people_bp.route(
    "/non-user-relative",
    methods=["POST"],
)
@jwt_required()
def create_non_user_relative():
    user = get_current_user()

    if not user:
        return jsonify({
            "message": (
                "Invalid user"
            )
        }), 401

    if not user.person:
        return jsonify({
            "message": (
                "User profile not found"
            )
        }), 404

    data = request.get_json(
        silent=True
    )

    if not data:
        return jsonify({
            "message": (
                "Request body must be JSON"
            )
        }), 400

    full_name = str(
        data.get(
            "full_name",
            "",
        )
    ).strip()

    relationship_type = str(
        data.get(
            "relationship_type",
            "",
        )
    ).strip().lower()

    relative_to_person_id_raw = (
        data.get(
            "relative_to_person_id"
        )
    )

    gender_raw = data.get(
        "gender"
    )

    birth_date_raw = data.get(
        "birth_date"
    )

    parent_ids_raw = data.get(
        "parent_ids",
        [],
    )

    gender = (
        str(gender_raw)
        .strip()
        .lower()
        if (
            gender_raw is not None
            and str(
                gender_raw
            ).strip()
        )
        else None
    )

    birth_date = None

    if birth_date_raw:
        try:
            birth_date = (
                date.fromisoformat(
                    str(
                        birth_date_raw
                    )
                )
            )

        except ValueError:
            return jsonify({
                "message": (
                    "birth_date must use "
                    "YYYY-MM-DD format"
                )
            }), 400

    if not full_name:
        return jsonify({
            "message": (
                "Full name is required"
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


    if parent_ids_raw is None:
        parent_ids_raw = []

    if not isinstance(
        parent_ids_raw,
        list,
    ):
        return jsonify({
            "message": (
                "parent_ids must be a list"
            )
        }), 400

    if (
        parent_ids_raw
        and relationship_type
        not in {
            "child",
            "sibling",
        }
    ):
        return jsonify({
            "message": (
                "parent_ids can only be supplied "
                "when adding a child or sibling"
            )
        }), 400

    parent_ids = []
    seen_parent_ids = set()

    for raw_parent_id in parent_ids_raw:
        try:
            parent_id = UUID(
                str(
                    raw_parent_id
                )
            )

        except (
            ValueError,
            TypeError,
        ):
            return jsonify({
                "message": (
                    "parent_ids contains an "
                    "invalid person ID"
                )
            }), 400

        if parent_id in seen_parent_ids:
            continue

        seen_parent_ids.add(
            parent_id
        )

        parent_ids.append(
            parent_id
        )

    if (
        relationship_type == "child"
        and len(parent_ids) > 1
    ):
        return jsonify({
            "message": (
                "When adding a child, select "
                "at most one other parent"
            )
        }), 400

    if (
        relationship_type == "sibling"
        and len(parent_ids) > 2
    ):
        return jsonify({
            "message": (
                "When adding a sibling, select "
                "at most two known parents"
            )
        }), 400

    # -----------------------------------------
    # Target person
    # -----------------------------------------

    if relative_to_person_id_raw:
        try:
            target_person_uuid = UUID(
                str(
                    relative_to_person_id_raw
                )
            )

        except (
            ValueError,
            TypeError,
        ):
            return jsonify({
                "message": (
                    "Invalid "
                    "relative_to_person_id"
                )
            }), 400

        target_person = (
            db.session.get(
                Person,
                target_person_uuid,
            )
        )

        if not target_person:
            return jsonify({
                "message": (
                    "Target person not found"
                )
            }), 404

    else:
        target_person = (
            user.person
        )

    # =====================================================
    # OWNERSHIP RESTRICTION
    # =====================================================
    #
    # User may modify:
    #
    # 1. their own Person profile
    #
    # 2. a non-user Person they created
    #
    # User may not rewrite another registered user's
    # genealogy directly.
    # =====================================================

    is_own_profile = (
        target_person.id
        == user.person.id
    )

    if not is_own_profile:
        if (
            target_person.user_id
            is not None
        ):
            return jsonify({
                "message": (
                    "You cannot add relatives "
                    "directly to another "
                    "registered user's profile"
                )
            }), 403

        if (
            target_person.created_by_user_id
            != user.id
        ):
            return jsonify({
                "message": (
                    "You can only add relatives "
                    "to yourself or to a "
                    "non-user profile you created"
                )
            }), 403

        if not is_person_in_family_network(
            user.person.id,
            target_person.id,
        ):
            return jsonify({
                "message": (
                    "This profile is not in "
                    "your family network"
                )
            }), 403

    # -----------------------------------------
    # Determine supplemental parents
    # -----------------------------------------

    selected_parents = []

    for parent_id in parent_ids:
        if parent_id == target_person.id:
            return jsonify({
                "message": (
                    "The target person cannot "
                    "also be selected as a parent"
                )
            }), 400

        parent_person = (
            db.session.get(
                Person,
                parent_id,
            )
        )

        if not parent_person:
            return jsonify({
                "message": (
                    "One of the selected parents "
                    "was not found"
                )
            }), 404

        if not is_person_in_family_network(
            user.person.id,
            parent_person.id,
        ):
            return jsonify({
                "message": (
                    "Selected parents must "
                    "already exist in your "
                    "family network"
                )
            }), 403

        is_self = (
            parent_person.id
            == user.person.id
        )

        if not is_self:
            if (
                parent_person.user_id
                is not None
            ):
                return jsonify({
                    "message": (
                        "A registered user's "
                        "genealogy cannot be "
                        "modified directly"
                    )
                }), 403

            if (
                parent_person
                .created_by_user_id
                != user.id
            ):
                return jsonify({
                    "message": (
                        "You can only use yourself "
                        "or a non-user profile you "
                        "created as a selected parent"
                    )
                }), 403

        selected_parents.append(
            parent_person
        )

    # -----------------------------------------
    # Duplicate detection
    # -----------------------------------------

    duplicate_person = (
        find_duplicate_direct_relative(
            target_person=(
                target_person
            ),

            full_name=(
                full_name
            ),

            relationship_type=(
                relationship_type
            ),

            birth_date=(
                birth_date
            ),
        )
    )

    if duplicate_person:
        return jsonify({
            "message": (
                "This relative already "
                "appears to exist"
            ),

            "existing_person": {
                "id": str(
                    duplicate_person.id
                ),

                "full_name": (
                    duplicate_person
                    .full_name
                ),

                "birth_date": (
                    duplicate_person
                    .birth_date
                    .isoformat()
                    if (
                        duplicate_person
                        .birth_date
                    )
                    else None
                ),

                "has_account": (
                    duplicate_person
                    .user_id
                    is not None
                ),
            },
        }), 409

    try:
        (
            raw_code,
            code_hash,
            expires_at,
        ) = generate_claim_code()

        new_person = Person(
            full_name=(
                full_name
            ),

            birth_date=(
                birth_date
            ),

            gender=(
                gender
            ),

            created_by_user_id=(
                user.id
            ),

            claim_code_hash=(
                code_hash
            ),

            claim_code_expires_at=(
                expires_at
            ),
        )

        db.session.add(
            new_person
        )

        db.session.flush()

        # -------------------------------------
        # Main/direct relationship
        # -------------------------------------

        relationship = Relationship(
            person_a_id=(
                target_person.id
            ),

            person_b_id=(
                new_person.id
            ),

            relation_a_to_b=(
                relationship_type
            ),

            relation_b_to_a=(
                INVERSE_RELATIONSHIPS[
                    relationship_type
                ]
            ),

            verification_status=(
                "claimed"
            ),
        )

        db.session.add(
            relationship
        )

        # -------------------------------------
        # Supplemental explicit parent evidence
        # -------------------------------------
        #
        # IMPORTANT:
        #
        # spouse != parent
        #
        # A spouse is NEVER copied here merely
        # because they are married to the target.
        #
        # For sibling:
        #   these are the target's explicit parents.
        #
        # For child:
        #   this is the explicitly selected other
        #   parent, if one was selected.
        # -------------------------------------

        parent_relationships = []

        for parent_person in selected_parents:
            # Defensive protection.
            #
            # For child, target already has the
            # direct "child" relationship.
            #
            # For sibling this should normally
            # never happen either.

            if (
                parent_person.id
                == target_person.id
            ):
                continue

            parent_relationship = (
                Relationship(
                    person_a_id=(
                        parent_person.id
                    ),

                    person_b_id=(
                        new_person.id
                    ),

                    relation_a_to_b=(
                        "child"
                    ),

                    relation_b_to_a=(
                        "parent"
                    ),

                    verification_status=(
                        "claimed"
                    ),
                )
            )

            db.session.add(
                parent_relationship
            )

            parent_relationships.append(
                parent_relationship
            )

        db.session.commit()

        return jsonify({
            "message": (
                "Non-user relative created"
            ),

            "relative_to": {
                "id": str(
                    target_person.id
                ),

                "full_name": (
                    target_person.full_name
                ),
            },

            "person": {
                "id": str(
                    new_person.id
                ),

                "full_name": (
                    new_person.full_name
                ),

                "birth_date": (
                    new_person.birth_date
                    .isoformat()
                    if (
                        new_person.birth_date
                    )
                    else None
                ),

                "gender": (
                    new_person.gender
                ),

                "has_account": False,

                # Raw code is returned once.
                # Only the hash is stored.

                "claim_code": (
                    raw_code
                ),

                "claim_code_expires_at": (
                    expires_at.isoformat()
                ),
            },

            "relationship": {
                "id": str(
                    relationship.id
                ),

                "relationship_type": (
                    relationship
                    .relation_a_to_b
                ),

                "verification_status": (
                    relationship
                    .verification_status
                ),
            },

            "parent_relationships": [
                {
                    "id": str(
                        item.id
                    ),

                    "parent_person_id": str(
                        item.person_a_id
                    ),

                    "child_person_id": str(
                        item.person_b_id
                    ),
                }
                for item
                in parent_relationships
            ],
        }), 201

    except Exception as error:
        db.session.rollback()

        return server_error_response(
            (
                "Failed to create "
                "relative"
            ),
            error,
        )