from collections import deque
from itertools import combinations
from uuid import UUID

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.extensions import db
from app.models import Person, Relationship, User

family_bp = Blueprint("family", __name__)

GENERATION_CHANGE = {
    "parent": -1,
    "child": 1,
    "sibling": 0,
    "half_sibling": 0,
    "spouse": 0,
    "co_parent": 0,
}


def serialize_person(person):
    return {
        "id": str(person.id),
        "full_name": person.full_name,
        "birth_date": (
            person.birth_date.isoformat()
            if person.birth_date
            else None
        ),
        "gender": person.gender,
        "photo_url": person.photo_url,
        "has_account": person.user_id is not None,
    }


def get_current_user():
    user_id = get_jwt_identity()

    try:
        user_uuid = UUID(str(user_id))
    except (ValueError, TypeError):
        return None

    return db.session.get(
        User,
        user_uuid,
    )


def normalize_gender(gender):
    if not gender:
        return None

    value = str(gender).strip().lower()

    if value in {
        "male",
        "m",
        "man",
    }:
        return "male"

    if value in {
        "female",
        "f",
        "woman",
    }:
        return "female"

    return None


def gendered_label(
    gender,
    male_label,
    female_label,
    neutral_label,
):
    gender = normalize_gender(gender)

    if gender == "male":
        return male_label

    if gender == "female":
        return female_label

    return neutral_label


def ancestor_label(
    levels,
    gender,
):
    if levels <= 0:
        return "Relative"

    if levels == 1:
        return gendered_label(
            gender,
            "Father",
            "Mother",
            "Parent",
        )

    if levels == 2:
        return gendered_label(
            gender,
            "Grandfather",
            "Grandmother",
            "Grandparent",
        )

    prefix = "Great-" * (
        levels - 2
    )

    return gendered_label(
        gender,
        f"{prefix}Grandfather",
        f"{prefix}Grandmother",
        f"{prefix}Grandparent",
    )


def descendant_label(
    levels,
    gender,
):
    if levels <= 0:
        return "Relative"

    if levels == 1:
        return gendered_label(
            gender,
            "Son",
            "Daughter",
            "Child",
        )

    if levels == 2:
        return gendered_label(
            gender,
            "Grandson",
            "Granddaughter",
            "Grandchild",
        )

    prefix = "Great-" * (
        levels - 2
    )

    return gendered_label(
        gender,
        f"{prefix}Grandson",
        f"{prefix}Granddaughter",
        f"{prefix}Grandchild",
    )


def aunt_uncle_label(
    levels_up,
    gender,
):
    if levels_up <= 1:
        return gendered_label(
            gender,
            "Uncle",
            "Aunt",
            "Aunt / Uncle",
        )

    prefix = "Great-" * (
        levels_up - 1
    )

    return gendered_label(
        gender,
        f"{prefix}Uncle",
        f"{prefix}Aunt",
        f"{prefix}Aunt / Uncle",
    )


def nephew_niece_label(
    levels_down,
    gender,
):
    if levels_down <= 1:
        return gendered_label(
            gender,
            "Nephew",
            "Niece",
            "Niece / Nephew",
        )

    prefix = "Great-" * (
        levels_down - 1
    )

    return gendered_label(
        gender,
        f"{prefix}Nephew",
        f"{prefix}Niece",
        f"{prefix}Niece / Nephew",
    )


def derive_relationship_label(
    path,
    person,
):
    if not path:
        return "You"

    gender = person.gender

    raw_path = list(path)

    #
    # DIRECT RELATIONSHIPS
    #

    if raw_path == [
        "half_sibling"
    ]:
        return gendered_label(
            gender,
            "Half-brother",
            "Half-sister",
            "Half-sibling",
        )

    if raw_path == [
        "co_parent"
    ]:
        return "Co-parent"

    if raw_path == [
        "parent"
    ]:
        return ancestor_label(
            1,
            gender,
        )

    if raw_path == [
        "child"
    ]:
        return descendant_label(
            1,
            gender,
        )

    if raw_path == [
        "sibling"
    ]:
        return gendered_label(
            gender,
            "Brother",
            "Sister",
            "Sibling",
        )

    if raw_path == [
        "spouse"
    ]:
        return gendered_label(
            gender,
            "Husband",
            "Wife",
            "Spouse",
        )

    #
    # STEP FAMILY
    #
    # Your biological parent's actual spouse
    # is a step-parent.
    #
    # A co-parent is NOT enough evidence.
    #

    if raw_path == [
        "parent",
        "spouse",
    ]:
        return gendered_label(
            gender,
            "Stepfather",
            "Stepmother",
            "Step-parent",
        )

    #
    # Parent's co-parent is deliberately NOT
    # called step-parent.
    #

    if raw_path == [
        "parent",
        "co_parent",
    ]:
        return "Parent's co-parent"

    #
    # Child of a spouse.
    #
    # Example:
    #
    # You -> spouse -> their child
    #
    # We can safely call them a step-child.
    #

    if raw_path == [
        "spouse",
        "child",
    ]:
        return gendered_label(
            gender,
            "Stepson",
            "Stepdaughter",
            "Stepchild",
        )

    #
    # Your parent's spouse's child.
    #
    # This is a step-sibling relationship.
    #

    if raw_path == [
        "parent",
        "spouse",
        "child",
    ]:
        return gendered_label(
            gender,
            "Stepbrother",
            "Stepsister",
            "Stepsibling",
        )

    #
    # Do NOT infer step-family through
    # co-parent relationships.
    #

    if raw_path == [
        "parent",
        "co_parent",
        "child",
    ]:
        return "Relative"

    #
    # IN-LAWS
    #

    if raw_path == [
        "child",
        "spouse",
    ]:
        return gendered_label(
            gender,
            "Son-in-law",
            "Daughter-in-law",
            "Child-in-law",
        )

    if raw_path == [
        "spouse",
        "parent",
    ]:
        return gendered_label(
            gender,
            "Father-in-law",
            "Mother-in-law",
            "Parent-in-law",
        )

    if raw_path == [
        "spouse",
        "sibling",
    ]:
        return gendered_label(
            gender,
            "Brother-in-law",
            "Sister-in-law",
            "Sibling-in-law",
        )

    if raw_path == [
        "sibling",
        "spouse",
    ]:
        return gendered_label(
            gender,
            "Brother-in-law",
            "Sister-in-law",
            "Sibling-in-law",
        )

    #
    # HALF-SIBLING PATHS
    #
    # For extended genealogy, half-siblings
    # behave like siblings.
    #
    # We keep the direct Half-brother /
    # Half-sister label above.
    #

    normalized_path = [
        (
            "sibling"
            if relation
            == "half_sibling"
            else relation
        )
        for relation
        in raw_path
    ]

    #
    # ANCESTORS
    #

    if all(
        relation == "parent"
        for relation
        in normalized_path
    ):
        return ancestor_label(
            len(
                normalized_path
            ),
            gender,
        )

    #
    # DESCENDANTS
    #

    if all(
        relation == "child"
        for relation
        in normalized_path
    ):
        return descendant_label(
            len(
                normalized_path
            ),
            gender,
        )

    #
    # AUNT / UNCLE
    #
    # parent -> sibling
    # parent -> parent -> sibling
    # etc.
    #

    if (
        len(
            normalized_path
        )
        >= 2
        and normalized_path[
            -1
        ]
        == "sibling"
        and all(
            relation
            == "parent"
            for relation
            in normalized_path[
                :-1
            ]
        )
    ):
        return aunt_uncle_label(
            len(
                normalized_path
            ) - 1,
            gender,
        )

    #
    # NIECE / NEPHEW
    #
    # sibling -> child
    # sibling -> child -> child
    # etc.
    #

    if (
        len(
            normalized_path
        )
        >= 2
        and normalized_path[
            0
        ]
        == "sibling"
        and all(
            relation
            == "child"
            for relation
            in normalized_path[
                1:
            ]
        )
    ):
        return nephew_niece_label(
            len(
                normalized_path
            ) - 1,
            gender,
        )

    #
    # COUSIN
    #

    if normalized_path == [
        "parent",
        "sibling",
        "child",
    ]:
        return "Cousin"

    #
    # IMPORTANT:
    #
    # co_parent is never converted into spouse.
    #
    # This means an ex-partner or unmarried
    # parent remains safely classified as a
    # co-parent unless the database contains
    # an explicit spouse relationship.
    #

    if "co_parent" in raw_path:
        generation = (
            raw_path.count(
                "child"
            )
            - raw_path.count(
                "parent"
            )
        )

        if generation < 0:
            return "Relative"

        if generation > 0:
            return "Relative"

        return "Relative"

    #
    # FALLBACK
    #

    generation = (
        normalized_path.count(
            "child"
        )
        - normalized_path.count(
            "parent"
        )
    )

    if generation < 0:
        return "Ancestor"

    if generation > 0:
        return "Descendant"

    return "Relative"


def graph_key(
    person_a_id,
    person_b_id,
):
    values = sorted([
        str(person_a_id),
        str(person_b_id),
    ])

    return (
        values[0],
        values[1],
    )


def add_graph_connection(
    adjacency,
    edge_map,
    person_a_id,
    person_b_id,
    relation_a_to_b,
    relation_b_to_a,
    *,
    edge_id,
    verification_status,
    inferred=False,
    inference_type=None,
):
    if (
        person_a_id
        == person_b_id
    ):
        return False

    pair_key = graph_key(
        person_a_id,
        person_b_id,
    )

    existing = edge_map.get(
        pair_key
    )

    if existing:
        if (
            existing["inferred"]
            is False
        ):
            return False

        if inferred:
            return False

        old_a = existing[
            "person_a_id"
        ]

        old_b = existing[
            "person_b_id"
        ]

        adjacency[
            old_a
        ].pop(
            old_b,
            None,
        )

        adjacency[
            old_b
        ].pop(
            old_a,
            None,
        )

    edge_data = {
        "id": str(
            edge_id
        ),

        "person_a_id": (
            person_a_id
        ),

        "person_b_id": (
            person_b_id
        ),

        "relation_a_to_b": (
            relation_a_to_b
        ),

        "relation_b_to_a": (
            relation_b_to_a
        ),

        "verification_status": (
            verification_status
        ),

        "inferred": (
            inferred
        ),

        "inference_type": (
            inference_type
        ),

        "sibling_type": None,

        "shared_parent_ids": [],

        "shared_child_ids": [],
    }

    edge_map[
        pair_key
    ] = edge_data

    adjacency.setdefault(
        person_a_id,
        {},
    )

    adjacency.setdefault(
        person_b_id,
        {},
    )

    adjacency[
        person_a_id
    ][
        person_b_id
    ] = {
        "relation": (
            relation_a_to_b
        ),

        "reverse_relation": (
            relation_b_to_a
        ),

        "edge": (
            edge_data
        ),
    }

    adjacency[
        person_b_id
    ][
        person_a_id
    ] = {
        "relation": (
            relation_b_to_a
        ),

        "reverse_relation": (
            relation_a_to_b
        ),

        "edge": (
            edge_data
        ),
    }

    return True


def build_explicit_graph(
    root_person_id=None,
    max_depth=6,
):
    """
    Build the explicit relationship graph.

    If a root is supplied, only load that
    connected family neighborhood.

    Without a root, preserve old behavior
    for regression scripts.
    """

    adjacency = {}
    edge_map = {}

    if root_person_id is None:
        relationships = (
            db.session.scalars(
                db.select(
                    Relationship
                )
            )
            .all()
        )

        for relationship in relationships:
            add_graph_connection(
                adjacency=adjacency,
                edge_map=edge_map,

                person_a_id=(
                    relationship
                    .person_a_id
                ),

                person_b_id=(
                    relationship
                    .person_b_id
                ),

                relation_a_to_b=(
                    relationship
                    .relation_a_to_b
                ),

                relation_b_to_a=(
                    relationship
                    .relation_b_to_a
                ),

                edge_id=(
                    relationship.id
                ),

                verification_status=(
                    relationship
                    .verification_status
                ),

                inferred=False,

                inference_type=None,
            )

        return (
            adjacency,
            edge_map,
        )

    adjacency.setdefault(
        root_person_id,
        {},
    )

    distance = {
        root_person_id: 0
    }

    frontier = {
        root_person_id
    }

    processed_relationship_ids = set()

    for depth in range(
        max_depth + 1
    ):
        if not frontier:
            break

        relationships = (
            db.session.scalars(
                db.select(
                    Relationship
                )
                .where(
                    db.or_(
                        Relationship
                        .person_a_id
                        .in_(
                            frontier
                        ),

                        Relationship
                        .person_b_id
                        .in_(
                            frontier
                        ),
                    )
                )
            )
            .all()
        )

        next_frontier = set()

        for relationship in relationships:
            if (
                relationship.id
                in
                processed_relationship_ids
            ):
                continue

            processed_relationship_ids.add(
                relationship.id
            )

            person_a_id = (
                relationship
                .person_a_id
            )

            person_b_id = (
                relationship
                .person_b_id
            )

            if person_a_id in frontier:
                current_id = (
                    person_a_id
                )

                relative_id = (
                    person_b_id
                )

            elif person_b_id in frontier:
                current_id = (
                    person_b_id
                )

                relative_id = (
                    person_a_id
                )

            else:
                continue

            current_depth = (
                distance.get(
                    current_id,
                    depth,
                )
            )

            relative_depth = (
                current_depth + 1
            )

            if (
                relative_id
                not in distance
                and relative_depth
                <= max_depth
            ):
                distance[
                    relative_id
                ] = relative_depth

                next_frontier.add(
                    relative_id
                )

            if (
                person_a_id
                not in distance
                or person_b_id
                not in distance
            ):
                continue

            if (
                distance[
                    person_a_id
                ] > max_depth
                or distance[
                    person_b_id
                ] > max_depth
            ):
                continue

            add_graph_connection(
                adjacency=adjacency,

                edge_map=edge_map,

                person_a_id=(
                    person_a_id
                ),

                person_b_id=(
                    person_b_id
                ),

                relation_a_to_b=(
                    relationship
                    .relation_a_to_b
                ),

                relation_b_to_a=(
                    relationship
                    .relation_b_to_a
                ),

                edge_id=(
                    relationship.id
                ),

                verification_status=(
                    relationship
                    .verification_status
                ),

                inferred=False,

                inference_type=None,
            )

        frontier = next_frontier

    return (
        adjacency,
        edge_map,
    )


def get_sibling_components(
    adjacency,
):
    sibling_graph = {}

    for (
        person_id,
        neighbors,
    ) in adjacency.items():

        for (
            neighbor_id,
            connection,
        ) in neighbors.items():

            edge = (
                connection["edge"]
            )

            if edge["inferred"]:
                continue

            if (
                connection[
                    "relation"
                ]
                != "sibling"
            ):
                continue

            sibling_graph.setdefault(
                person_id,
                set(),
            ).add(
                neighbor_id
            )

            sibling_graph.setdefault(
                neighbor_id,
                set(),
            ).add(
                person_id
            )

    visited = set()
    components = []

    for start_id in sibling_graph:
        if start_id in visited:
            continue

        component = set()

        queue = deque([
            start_id
        ])

        visited.add(
            start_id
        )

        while queue:
            person_id = (
                queue.popleft()
            )

            component.add(
                person_id
            )

            for sibling_id in (
                sibling_graph.get(
                    person_id,
                    set(),
                )
            ):
                if (
                    sibling_id
                    in visited
                ):
                    continue

                visited.add(
                    sibling_id
                )

                queue.append(
                    sibling_id
                )

        if len(component) >= 2:
            components.append(
                component
            )

    return components


def get_known_parent_ids(
    person_id,
    adjacency,
):
    parent_ids = set()

    for (
        relative_id,
        connection,
    ) in adjacency.get(
        person_id,
        {},
    ).items():

        if (
            connection[
                "relation"
            ]
            == "parent"
        ):
            parent_ids.add(
                relative_id
            )

    return parent_ids


def infer_shared_sibling_parents(
    adjacency,
    edge_map,
):
    """
    Conservative rule:

    Never infer a specific parent identity
    from a sibling relationship alone.

    Siblings can be full siblings,
    half-siblings, step-siblings, or have
    incomplete parent data.

    Therefore parent-child relationships
    must come from explicit parent evidence.

    Sibling relationships may still be
    inferred later FROM known parents,
    but known parents must never be inferred
    FROM sibling relationships.
    """

    return 0


def classify_sibling_relationships(
    adjacency,
    edge_map,
):
    """
    Classify every sibling edge using currently
    known parent evidence.

    full:
        two or more shared known parents

    half:
        exactly one shared known parent AND
        each sibling has at least one different
        known parent

    unknown:
        the people are known/inferred siblings,
        but the available parent evidence is not
        enough to decide full vs half.

    Explicit database rows are never rewritten.
    Only the in-memory graph used for this
    response is classified.
    """

    full_count = 0
    half_count = 0
    unknown_count = 0

    processed = set()

    for edge in edge_map.values():
        relation_a = edge[
            "relation_a_to_b"
        ]

        relation_b = edge[
            "relation_b_to_a"
        ]

        if (
            relation_a
            not in {
                "sibling",
                "half_sibling",
            }
            or relation_b
            not in {
                "sibling",
                "half_sibling",
            }
        ):
            continue

        pair_key = graph_key(
            edge[
                "person_a_id"
            ],
            edge[
                "person_b_id"
            ],
        )

        if pair_key in processed:
            continue

        processed.add(
            pair_key
        )

        person_a_id = edge[
            "person_a_id"
        ]

        person_b_id = edge[
            "person_b_id"
        ]

        parents_a = (
            get_known_parent_ids(
                person_a_id,
                adjacency,
            )
        )

        parents_b = (
            get_known_parent_ids(
                person_b_id,
                adjacency,
            )
        )

        shared_parents = (
            parents_a
            & parents_b
        )

        unique_a = (
            parents_a
            - parents_b
        )

        unique_b = (
            parents_b
            - parents_a
        )

        if len(shared_parents) >= 2:
            sibling_type = "full"

            graph_relation = (
                "sibling"
            )

            full_count += 1

        elif (
            len(shared_parents) == 1
            and unique_a
            and unique_b
        ):
            sibling_type = "half"

            graph_relation = (
                "half_sibling"
            )

            half_count += 1

        else:
            sibling_type = "unknown"

            graph_relation = (
                "sibling"
            )

            unknown_count += 1

        edge[
            "sibling_type"
        ] = sibling_type

        edge[
            "shared_parent_ids"
        ] = [
            str(parent_id)
            for parent_id
            in sorted(
                shared_parents,
                key=str,
            )
        ]

        adjacency[
            person_a_id
        ][
            person_b_id
        ][
            "relation"
        ] = graph_relation

        adjacency[
            person_b_id
        ][
            person_a_id
        ][
            "relation"
        ] = graph_relation

    return {
        "full_sibling_edges": (
            full_count
        ),

        "half_sibling_edges": (
            half_count
        ),

        "unknown_sibling_edges": (
            unknown_count
        ),
    }

def build_parents_by_child(
    adjacency,
):
    """
    Build:

        child_id -> {parent_id, parent_id, ...}

    from the current in-memory family graph.
    """

    parents_by_child = {}

    for (
        person_id,
        neighbors,
    ) in adjacency.items():

        for (
            relative_id,
            connection,
        ) in neighbors.items():

            if (
                connection[
                    "relation"
                ]
                != "parent"
            ):
                continue

            parents_by_child.setdefault(
                person_id,
                set(),
            ).add(
                relative_id
            )

    return parents_by_child


def infer_sibling_pairs_from_parents(
    adjacency,
    edge_map,
):
    """
    Infer sibling connections from parent evidence.

    Sharing at least one known parent is enough
    to establish that two people are siblings.

    It is NOT always enough to establish whether
    they are full or half siblings.

    That is decided later by
    classify_sibling_relationships().

    No database relationship is created.
    """

    parents_by_child = (
        build_parents_by_child(
            adjacency
        )
    )

    children_by_parent = {}

    for (
        child_id,
        parent_ids,
    ) in parents_by_child.items():
        for parent_id in parent_ids:
            children_by_parent.setdefault(
                parent_id,
                set(),
            ).add(
                child_id
            )

    candidate_pairs = set()

    for child_ids in (
        children_by_parent.values()
    ):
        if len(child_ids) < 2:
            continue

        sorted_children = sorted(
            child_ids,
            key=str,
        )

        for (
            first_child_id,
            second_child_id,
        ) in combinations(
            sorted_children,
            2,
        ):
            candidate_pairs.add(
                (
                    first_child_id,
                    second_child_id,
                )
            )

    inferred_count = 0

    for (
        first_child_id,
        second_child_id,
    ) in candidate_pairs:
        pair_key = graph_key(
            first_child_id,
            second_child_id,
        )

        existing_edge = edge_map.get(
            pair_key
        )

        if existing_edge:
            existing_relations = {
                existing_edge[
                    "relation_a_to_b"
                ],
                existing_edge[
                    "relation_b_to_a"
                ],
            }

            if (
                "sibling"
                in existing_relations
                or "half_sibling"
                in existing_relations
            ):
                continue

            # Never overwrite another explicit
            # relationship between the people.

            continue

        created = add_graph_connection(
            adjacency=adjacency,
            edge_map=edge_map,

            person_a_id=(
                first_child_id
            ),

            person_b_id=(
                second_child_id
            ),

            relation_a_to_b=(
                "sibling"
            ),

            relation_b_to_a=(
                "sibling"
            ),

            edge_id=(
                "inferred:"
                "shared-parent-sibling:"
                f"{pair_key[0]}:"
                f"{pair_key[1]}"
            ),

            verification_status=(
                "inferred"
            ),

            inferred=True,

            inference_type=(
                "shared_parent_sibling"
            ),
        )

        if created:
            inferred_count += 1

    return inferred_count


def infer_coparent_pairs(
    adjacency,
    edge_map,
):
    """
    Build one co-parent pair per unique
    combination of parents.

    Multiple children shared by the same pair
    are attached to that single pairing.

    One person may therefore have multiple
    independent co-parent relationships.
    """

    parents_by_child = (
        build_parents_by_child(
            adjacency
        )
    )

    children_by_pair = {}

    for (
        child_id,
        parent_ids,
    ) in parents_by_child.items():

        if len(parent_ids) < 2:
            continue

        sorted_parents = sorted(
            parent_ids,
            key=str,
        )

        for (
            first_parent_id,
            second_parent_id,
        ) in combinations(
            sorted_parents,
            2,
        ):
            pair_key = graph_key(
                first_parent_id,
                second_parent_id,
            )

            children_by_pair.setdefault(
                pair_key,
                {
                    "parent_a_id": (
                        first_parent_id
                    ),

                    "parent_b_id": (
                        second_parent_id
                    ),

                    "child_ids": (
                        set()
                    ),
                },
            )

            children_by_pair[
                pair_key
            ][
                "child_ids"
            ].add(
                child_id
            )

    inferred_edge_count = 0

    parent_partners = {}

    for (
        pair_key,
        pair_data,
    ) in children_by_pair.items():

        first_parent_id = (
            pair_data[
                "parent_a_id"
            ]
        )

        second_parent_id = (
            pair_data[
                "parent_b_id"
            ]
        )

        child_ids = (
            pair_data[
                "child_ids"
            ]
        )

        parent_partners.setdefault(
            first_parent_id,
            set(),
        ).add(
            second_parent_id
        )

        parent_partners.setdefault(
            second_parent_id,
            set(),
        ).add(
            first_parent_id
        )

        existing_edge = (
            edge_map.get(
                pair_key
            )
        )

        if existing_edge:
            existing_edge[
                "shared_child_ids"
            ] = [
                str(child_id)
                for child_id
                in sorted(
                    child_ids,
                    key=str,
                )
            ]

            continue

        created = (
            add_graph_connection(
                adjacency=(
                    adjacency
                ),

                edge_map=(
                    edge_map
                ),

                person_a_id=(
                    first_parent_id
                ),

                person_b_id=(
                    second_parent_id
                ),

                relation_a_to_b=(
                    "co_parent"
                ),

                relation_b_to_a=(
                    "co_parent"
                ),

                edge_id=(
                    "inferred:"
                    "co-parent:"
                    f"{pair_key[0]}:"
                    f"{pair_key[1]}"
                ),

                verification_status=(
                    "inferred"
                ),

                inferred=True,

                inference_type=(
                    "co_parent"
                ),
            )
        )

        if not created:
            continue

        inferred_edge_count += 1

        created_edge = (
            edge_map[
                pair_key
            ]
        )

        created_edge[
            "shared_child_ids"
        ] = [
            str(child_id)
            for child_id
            in sorted(
                child_ids,
                key=str,
            )
        ]

    multiple_partner_people = sum(
        1
        for partner_ids
        in parent_partners.values()
        if len(partner_ids) > 1
    )

    return {
        "co_parent_edges": (
            inferred_edge_count
        ),

        "co_parent_pairs": (
            len(
                children_by_pair
            )
        ),

        "co_parent_child_links": (
            sum(
                len(
                    pair_data[
                        "child_ids"
                    ]
                )
                for pair_data
                in children_by_pair.values()
            )
        ),

        "multiple_partner_people": (
            multiple_partner_people
        ),
    }


def build_inferred_family_graph(
    root_person_id=None,
    max_depth=6,
):
    (
        adjacency,
        edge_map,
    ) = build_explicit_graph(
        root_person_id=(
            root_person_id
        ),
        max_depth=(
            max_depth
        ),
    )

    # Support old sibling records where only
    # one sibling had parent information.
    sibling_parent_count = (
        infer_shared_sibling_parents(
            adjacency,
            edge_map,
        )
    )

    # Parent evidence can independently prove
    # that two people are siblings.
    inferred_sibling_count = (
        infer_sibling_pairs_from_parents(
            adjacency,
            edge_map,
        )
    )

    # Full / half / unknown is decided only
    # after all available parent evidence exists.
    sibling_stats = (
        classify_sibling_relationships(
            adjacency,
            edge_map,
        )
    )

    # Sharing a child creates co-parenthood,
    # never an automatic marriage.
    coparent_stats = (
        infer_coparent_pairs(
            adjacency,
            edge_map,
        )
    )

    inference_stats = {
        "shared_parent_edges": (
            sibling_parent_count
        ),

        "inferred_sibling_edges": (
            inferred_sibling_count
        ),

        **sibling_stats,

        **coparent_stats,

        "total_inferred_edges": (
            sibling_parent_count
            + inferred_sibling_count
            + coparent_stats[
                "co_parent_edges"
            ]
        ),
    }

    return (
        adjacency,
        edge_map,
        inference_stats,
    )

def serialize_graph_edge(
    edge,
    source_person_id,
    target_person_id,
):
    if (
        source_person_id
        == edge[
            "person_a_id"
        ]
    ):
        semantic_source_to_target = (
            edge[
                "relation_a_to_b"
            ]
        )

        semantic_target_to_source = (
            edge[
                "relation_b_to_a"
            ]
        )

    else:
        semantic_source_to_target = (
            edge[
                "relation_b_to_a"
            ]
        )

        semantic_target_to_source = (
            edge[
                "relation_a_to_b"
            ]
        )

    if (
        edge[
            "inferred"
        ]
        and edge[
            "inference_type"
        ]
        == "co_parent"
    ):
        layout_source_to_target = (
            "spouse"
        )

        layout_target_to_source = (
            "spouse"
        )

    else:
        layout_source_to_target = (
            semantic_source_to_target
        )

        layout_target_to_source = (
            semantic_target_to_source
        )

    return {
        "id": (
            edge["id"]
        ),

        "source_person_id": str(
            source_person_id
        ),

        "target_person_id": str(
            target_person_id
        ),

        "source_to_target": (
            layout_source_to_target
        ),

        "target_to_source": (
            layout_target_to_source
        ),

        "semantic_source_to_target": (
            semantic_source_to_target
        ),

        "semantic_target_to_source": (
            semantic_target_to_source
        ),

        "verification_status": (
            edge[
                "verification_status"
            ]
        ),

        "inferred": (
            edge[
                "inferred"
            ]
        ),

        "inference_type": (
            edge[
                "inference_type"
            ]
        ),

        "sibling_type": (
            edge.get(
                "sibling_type"
            )
        ),

        "shared_parent_ids": (
            edge.get(
                "shared_parent_ids",
                [],
            )
        ),

        "shared_child_ids": (
            edge.get(
                "shared_child_ids",
                [],
            )
        ),
    }


@family_bp.route(
    "",
    methods=["GET"],
)
@jwt_required()
def get_family():
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

    current_person = (
        user.person
    )

    (
        adjacency,
        _edge_map,
        inference_stats,
    ) = build_inferred_family_graph(
        root_person_id=(
            current_person.id
        ),
        max_depth=2,
    )

    direct_ids = set(
        adjacency.get(
            current_person.id,
            {},
        ).keys()
    )

    people_by_id = {}

    if direct_ids:
        people = (
            db.session.scalars(
                db.select(
                    Person
                ).where(
                    Person.id.in_(
                        direct_ids
                    )
                )
            )
            .all()
        )

        people_by_id = {
            person.id: person
            for person in people
        }

    family_members = []

    for (
        relative_id,
        connection,
    ) in adjacency.get(
        current_person.id,
        {},
    ).items():

        relative = (
            people_by_id.get(
                relative_id
            )
        )

        if not relative:
            continue

        edge = (
            connection[
                "edge"
            ]
        )

        relation_type = (
            connection[
                "relation"
            ]
        )

        family_members.append({
            "relationship_id": (
                edge[
                    "id"
                ]
            ),

            "person": (
                serialize_person(
                    relative
                )
            ),

            "relationship_type": (
                relation_type
            ),

            "derived_relationship": (
                derive_relationship_label(
                    [
                        relation_type
                    ],
                    relative,
                )
            ),

            "inferred": (
                edge[
                    "inferred"
                ]
            ),

            "inference_type": (
                edge[
                    "inference_type"
                ]
            ),

            "verification_status": (
                edge[
                    "verification_status"
                ]
            ),

            "sibling_type": (
                edge.get(
                    "sibling_type"
                )
            ),

            "shared_parent_ids": (
                edge.get(
                    "shared_parent_ids",
                    [],
                )
            ),

            "shared_child_ids": (
                edge.get(
                    "shared_child_ids",
                    [],
                )
            ),
        })

    return jsonify({
        "person": {
            "id": str(
                current_person.id
            ),

            "full_name": (
                current_person.full_name
            ),
        },

        "family": (
            family_members
        ),

        "count": (
            len(
                family_members
            )
        ),

        "inference": (
            inference_stats
        ),
    }), 200


@family_bp.route(
    "/tree",
    methods=["GET"],
)
@jwt_required()
def get_family_tree():
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

    root_person = (
        user.person
    )

    depth_raw = (
        request.args.get(
            "depth",
            default="4",
        )
    )

    try:
        max_depth = int(
            depth_raw
        )

    except (
        ValueError,
        TypeError,
    ):
        return jsonify({
            "message": (
                "depth must be a number"
            )
        }), 400

    if max_depth < 1:
        return jsonify({
            "message": (
                "depth must be at least 1"
            )
        }), 400

    if max_depth > 6:
        max_depth = 6

    (
        adjacency,
        _edge_map,
        inference_stats,
    ) = build_inferred_family_graph(
        root_person_id=(
            root_person.id
        ),
        max_depth=(
            max_depth
        ),
    )

    person_ids = set(
        adjacency.keys()
    )

    person_ids.add(
        root_person.id
    )

    people = (
        db.session.scalars(
            db.select(
                Person
            ).where(
                Person.id.in_(
                    person_ids
                )
            )
        )
        .all()
    )

    people_by_id = {
        person.id: person
        for person in people
    }

    queue = deque([
        (
            root_person,
            0,
            0,
            [],
        )
    ])

    visited = {
        root_person.id
    }

    nodes = {
        str(
            root_person.id
        ): {
            **serialize_person(
                root_person
            ),

            "depth": 0,

            "generation": 0,

            "is_root": True,

            "kinship_path": [],

            "derived_relationship": (
                "You"
            ),
        }
    }

    edges = {}

    while queue:
        (
            current_person,
            current_depth,
            current_generation,
            current_path,
        ) = queue.popleft()

        if (
            current_depth
            >= max_depth
        ):
            continue

        for (
            relative_id,
            connection,
        ) in adjacency.get(
            current_person.id,
            {},
        ).items():

            relative = (
                people_by_id.get(
                    relative_id
                )
            )

            if not relative:
                continue

            current_to_relative = (
                connection[
                    "relation"
                ]
            )

            edge = (
                connection[
                    "edge"
                ]
            )

            relative_generation = (
                current_generation
                + GENERATION_CHANGE.get(
                    current_to_relative,
                    0,
                )
            )

            relative_path = [
                *current_path,
                current_to_relative,
            ]

            pair_key = graph_key(
                current_person.id,
                relative.id,
            )

            serialized_edge_key = (
                f"{pair_key[0]}:"
                f"{pair_key[1]}"
            )

            if (
                serialized_edge_key
                not in edges
            ):
                edges[
                    serialized_edge_key
                ] = serialize_graph_edge(
                    edge=(
                        edge
                    ),

                    source_person_id=(
                        current_person.id
                    ),

                    target_person_id=(
                        relative.id
                    ),
                )

            if (
                relative.id
                in visited
            ):
                continue

            visited.add(
                relative.id
            )

            nodes[
                str(
                    relative.id
                )
            ] = {
                **serialize_person(
                    relative
                ),

                "depth": (
                    current_depth
                    + 1
                ),

                "generation": (
                    relative_generation
                ),

                "is_root": False,

                "kinship_path": (
                    relative_path
                ),

                "derived_relationship": (
                    derive_relationship_label(
                        relative_path,
                        relative,
                    )
                ),
            }

            queue.append(
                (
                    relative,
                    current_depth + 1,
                    relative_generation,
                    relative_path,
                )
            )

    generations = [
        node[
            "generation"
        ]
        for node
        in nodes.values()
    ]

    return jsonify({
        "root_person_id": str(
            root_person.id
        ),

        "depth": (
            max_depth
        ),

        "min_generation": (
            min(
                generations
            )
        ),

        "max_generation": (
            max(
                generations
            )
        ),

        "nodes": (
            list(
                nodes.values()
            )
        ),

        "edges": (
            list(
                edges.values()
            )
        ),

        "node_count": (
            len(
                nodes
            )
        ),

        "edge_count": (
            len(
                edges
            )
        ),

        "inference": (
            inference_stats
        ),
    }), 200