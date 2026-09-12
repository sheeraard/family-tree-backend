from uuid import UUID

from flask import (
    Blueprint,
    jsonify,
    request,
)

from app.extensions import db

from app.models.historical_person import (
    HistoricalPerson,
)

from app.models.historical_relationship import (
    HistoricalRelationship,
)

from app.utils.permissions import (
    admin_required,
)


historical_tree_bp = Blueprint(
    "historical_tree",
    __name__,
)


def _parse_uuid(
    value,
):
    try:
        return UUID(
            str(value)
        )
    except (
        ValueError,
        TypeError,
    ):
        return None


def _get_person(
    person_id,
):
    person_uuid = _parse_uuid(
        person_id
    )

    if person_uuid is None:
        return None

    return db.session.get(
        HistoricalPerson,
        person_uuid,
    )


def _get_relationship(
    relationship_id,
):
    relationship_uuid = _parse_uuid(
        relationship_id
    )

    if relationship_uuid is None:
        return None

    return db.session.get(
        HistoricalRelationship,
        relationship_uuid,
    )


def _clean_optional_string(
    value,
):
    if value is None:
        return None

    value = str(
        value
    ).strip()

    if not value:
        return None

    return value


def _would_create_cycle(
    parent_id,
    child_id,
):
    relationships = (
        HistoricalRelationship.query
        .all()
    )

    children_by_parent = {}

    for relationship in relationships:
        children_by_parent.setdefault(
            relationship.parent_id,
            set(),
        ).add(
            relationship.child_id
        )

    pending = [
        child_id
    ]

    visited = set()

    while pending:
        current_id = pending.pop()

        if current_id == parent_id:
            return True

        if current_id in visited:
            continue

        visited.add(
            current_id
        )

        pending.extend(
            children_by_parent.get(
                current_id,
                set(),
            )
        )

    return False


def _serialize_tree(
    include_unpublished=False,
):
    people_query = (
        HistoricalPerson.query
    )

    if not include_unpublished:
        people_query = (
            people_query.filter_by(
                is_published=True
            )
        )

    people = (
        people_query
        .order_by(
            HistoricalPerson.created_at.asc()
        )
        .all()
    )

    allowed_ids = {
        person.id
        for person in people
    }

    relationships = (
        HistoricalRelationship.query
        .order_by(
            HistoricalRelationship
            .created_at
            .asc()
        )
        .all()
    )

    relationships = [
        relationship
        for relationship
        in relationships
        if (
            relationship.parent_id
            in allowed_ids
            and
            relationship.child_id
            in allowed_ids
        )
    ]

    return {
        "nodes": [
            person.to_dict()
            for person
            in people
        ],
        "edges": [
            relationship.to_dict()
            for relationship
            in relationships
        ],
    }


@historical_tree_bp.get("")
def get_historical_tree():
    return jsonify(
        _serialize_tree(
            include_unpublished=False
        )
    ), 200


@historical_tree_bp.get(
    "/admin"
)
@admin_required
def get_admin_historical_tree():
    return jsonify(
        _serialize_tree(
            include_unpublished=True
        )
    ), 200


@historical_tree_bp.post(
    "/people"
)
@admin_required
def create_historical_person():
    data = request.get_json(
        silent=True
    ) or {}

    name = str(
        data.get(
            "name",
            "",
        )
    ).strip()

    if not name:
        return jsonify({
            "message": (
                "Name is required"
            )
        }), 400

    is_published = data.get(
        "is_published",
        True,
    )

    if not isinstance(
        is_published,
        bool,
    ):
        return jsonify({
            "message": (
                "is_published must "
                "be true or false"
            )
        }), 400

    person = HistoricalPerson(
        name=name,

        title=_clean_optional_string(
            data.get(
                "title"
            )
        ),

        description=(
            _clean_optional_string(
                data.get(
                    "description"
                )
            )
        ),

        birth_year=(
            _clean_optional_string(
                data.get(
                    "birth_year"
                )
            )
        ),

        death_year=(
            _clean_optional_string(
                data.get(
                    "death_year"
                )
            )
        ),

        location=(
            _clean_optional_string(
                data.get(
                    "location"
                )
            )
        ),

        image_url=(
            _clean_optional_string(
                data.get(
                    "image_url"
                )
            )
        ),

        source=(
            _clean_optional_string(
                data.get(
                    "source"
                )
            )
        ),

        is_published=is_published,
    )

    db.session.add(
        person
    )

    db.session.commit()

    return jsonify({
        "message": (
            "Historical person created"
        ),
        "item": person.to_dict(),
    }), 201


@historical_tree_bp.put(
    "/people/<person_id>"
)
@admin_required
def update_historical_person(
    person_id,
):
    person = _get_person(
        person_id
    )

    if person is None:
        return jsonify({
            "message": (
                "Historical person "
                "not found"
            )
        }), 404

    data = request.get_json(
        silent=True
    ) or {}

    if "name" in data:
        name = str(
            data.get(
                "name",
                "",
            )
        ).strip()

        if not name:
            return jsonify({
                "message": (
                    "Name cannot be empty"
                )
            }), 400

        person.name = name

    optional_fields = [
        "title",
        "description",
        "birth_year",
        "death_year",
        "location",
        "image_url",
        "source",
    ]

    for field in optional_fields:
        if field in data:
            setattr(
                person,
                field,
                _clean_optional_string(
                    data.get(
                        field
                    )
                ),
            )

    if "is_published" in data:
        is_published = data.get(
            "is_published"
        )

        if not isinstance(
            is_published,
            bool,
        ):
            return jsonify({
                "message": (
                    "is_published must "
                    "be true or false"
                )
            }), 400

        person.is_published = (
            is_published
        )

    db.session.commit()

    return jsonify({
        "message": (
            "Historical person updated"
        ),
        "item": person.to_dict(),
    }), 200


@historical_tree_bp.delete(
    "/people/<person_id>"
)
@admin_required
def delete_historical_person(
    person_id,
):
    person = _get_person(
        person_id
    )

    if person is None:
        return jsonify({
            "message": (
                "Historical person "
                "not found"
            )
        }), 404

    db.session.delete(
        person
    )

    db.session.commit()

    return jsonify({
        "message": (
            "Historical person deleted"
        )
    }), 200


@historical_tree_bp.post(
    "/relationships"
)
@admin_required
def create_historical_relationship():
    data = request.get_json(
        silent=True
    ) or {}

    parent_id = _parse_uuid(
        data.get(
            "parent_id"
        )
    )

    child_id = _parse_uuid(
        data.get(
            "child_id"
        )
    )

    if (
        parent_id is None
        or
        child_id is None
    ):
        return jsonify({
            "message": (
                "Valid parent_id and "
                "child_id are required"
            )
        }), 400

    if parent_id == child_id:
        return jsonify({
            "message": (
                "A person cannot be "
                "their own descendant"
            )
        }), 400

    parent = db.session.get(
        HistoricalPerson,
        parent_id,
    )

    child = db.session.get(
        HistoricalPerson,
        child_id,
    )

    if (
        parent is None
        or
        child is None
    ):
        return jsonify({
            "message": (
                "Parent or child "
                "not found"
            )
        }), 404

    if _would_create_cycle(
        parent_id,
        child_id,
    ):
        return jsonify({
            "message": (
                "Historical relationship "
                "would create a cycle"
            )
        }), 409

    relationship_type = str(
        data.get(
            "relationship_type",
            "parent",
        )
    ).strip()

    if not relationship_type:
        relationship_type = "parent"

    existing = (
        HistoricalRelationship.query
        .filter_by(
            parent_id=parent_id,
            child_id=child_id,
            relationship_type=(
                relationship_type
            ),
        )
        .first()
    )

    if existing is not None:
        return jsonify({
            "message": (
                "Historical relationship "
                "already exists"
            )
        }), 409

    relationship = (
        HistoricalRelationship(
            parent_id=parent_id,
            child_id=child_id,
            relationship_type=(
                relationship_type
            ),
            notes=(
                _clean_optional_string(
                    data.get(
                        "notes"
                    )
                )
            ),
        )
    )

    db.session.add(
        relationship
    )

    db.session.commit()

    return jsonify({
        "message": (
            "Historical relationship "
            "created"
        ),
        "item": (
            relationship.to_dict()
        ),
    }), 201


@historical_tree_bp.delete(
    "/relationships/"
    "<relationship_id>"
)
@admin_required
def delete_historical_relationship(
    relationship_id,
):
    relationship = (
        _get_relationship(
            relationship_id
        )
    )

    if relationship is None:
        return jsonify({
            "message": (
                "Historical relationship "
                "not found"
            )
        }), 404

    db.session.delete(
        relationship
    )

    db.session.commit()

    return jsonify({
        "message": (
            "Historical relationship "
            "deleted"
        )
    }), 200