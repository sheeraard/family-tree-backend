import sys
import uuid

from flask_jwt_extended import create_access_token

from app import create_app
from app.extensions import db
from app.models import (
    Person,
    Relationship,
    User,
)


TEST_PREFIX = "__74B1_TEST__"


def find_person(name):
    return db.session.scalar(
        db.select(Person).where(
            Person.full_name.ilike(name)
        )
    )


def delete_test_people():
    """
    Delete anything created by this test.
    Relationship rows should disappear through
    CASCADE, but we explicitly delete them too
    so cleanup remains predictable.
    """

    test_people = (
        db.session.scalars(
            db.select(Person).where(
                Person.full_name.ilike(
                    f"{TEST_PREFIX}%"
                )
            )
        )
        .all()
    )

    ids = {
        person.id
        for person in test_people
    }

    if ids:
        relationships = (
            db.session.scalars(
                db.select(Relationship).where(
                    db.or_(
                        Relationship.person_a_id.in_(
                            ids
                        ),
                        Relationship.person_b_id.in_(
                            ids
                        ),
                    )
                )
            )
            .all()
        )

        for relationship in relationships:
            db.session.delete(
                relationship
            )

        for person in test_people:
            db.session.delete(
                person
            )

        db.session.commit()


def create_temp_person(
    *,
    name,
    creator_user_id,
):
    person = Person(
        full_name=name,
        created_by_user_id=creator_user_id,
    )

    db.session.add(person)
    db.session.flush()

    return person


def create_relationship(
    first,
    second,
    first_to_second,
    second_to_first,
):
    relationship = Relationship(
        person_a_id=first.id,
        person_b_id=second.id,
        relation_a_to_b=first_to_second,
        relation_b_to_a=second_to_first,
        verification_status="claimed",
    )

    db.session.add(
        relationship
    )

    db.session.commit()

    return relationship


def post_relative(
    client,
    token,
    *,
    name,
    relationship_type,
    relative_to_person_id=None,
):
    payload = {
        "full_name": name,
        "relationship_type": relationship_type,
        "gender": "male",
    }

    if relative_to_person_id is not None:
        payload[
            "relative_to_person_id"
        ] = str(
            relative_to_person_id
        )

    return client.post(
        "/api/people/non-user-relative",
        json=payload,
        headers={
            "Authorization": (
                f"Bearer {token}"
            )
        },
    )


def print_result(
    number,
    name,
    response,
    expected_status,
):
    actual = response.status_code

    passed = (
        actual == expected_status
    )

    symbol = (
        "PASS"
        if passed
        else "FAIL"
    )

    print()
    print(
        f"[{symbol}] Test {number}: {name}"
    )

    print(
        f"       expected: {expected_status}"
    )

    print(
        f"       actual:   {actual}"
    )

    try:
        print(
            f"       response: {response.get_json()}"
        )
    except Exception:
        print(
            f"       response: {response.data}"
        )

    return passed


def main():
    app = create_app()

    results = []

    with app.app_context():
        # -----------------------------------------
        # Locate the existing Sopranos test people.
        # -----------------------------------------

        lucia = find_person(
            "lucia%"
        )

        tony = find_person(
            "Tony%"
        )

        if lucia is None:
            print(
                "ERROR: Could not find lucia "
                "in the people table."
            )
            sys.exit(1)

        if lucia.user_id is None:
            print(
                "ERROR: lucia does not have "
                "a registered account."
            )
            sys.exit(1)

        if tony is None:
            print(
                "ERROR: Could not find Tony "
                "in the people table."
            )
            sys.exit(1)

        if tony.user_id is None:
            print(
                "ERROR: Tony does not have "
                "a registered account."
            )
            sys.exit(1)

        lucia_user = db.session.get(
            User,
            lucia.user_id,
        )

        tony_user = db.session.get(
            User,
            tony.user_id,
        )

        if lucia_user is None:
            print(
                "ERROR: lucia's User row "
                "could not be found."
            )
            sys.exit(1)

        if tony_user is None:
            print(
                "ERROR: Tony's User row "
                "could not be found."
            )
            sys.exit(1)

        print()
        print(
            "7.4B-1 Relationship Ownership Tests"
        )

        print(
            "=================================="
        )

        print(
            f"lucia: {lucia.full_name} "
            f"({lucia.id})"
        )

        print(
            f"Tony:  {tony.full_name} "
            f"({tony.id})"
        )

        # Clean up leftovers from a previous
        # interrupted test run.
        delete_test_people()

        token = create_access_token(
            identity=str(
                lucia_user.id
            )
        )

        client = app.test_client()

        try:
            # =====================================
            # TEST 1
            #
            # lucia adds relative to herself.
            #
            # EXPECTED: 201
            # =====================================

            response = post_relative(
                client,
                token,
                name=(
                    f"{TEST_PREFIX}"
                    "SELF_RELATIVE"
                ),
                relationship_type="sibling",
            )

            results.append(
                print_result(
                    1,
                    (
                        "user can add "
                        "relative to self"
                    ),
                    response,
                    201,
                )
            )

            response_json = (
                response.get_json()
                or {}
            )

            own_relative_id = (
                response_json
                .get(
                    "person",
                    {},
                )
                .get(
                    "id"
                )
            )

            # =====================================
            # TEST 2
            #
            # lucia extends a non-user profile
            # that lucia created.
            #
            # EXPECTED: 201
            # =====================================

            if own_relative_id:
                response = post_relative(
                    client,
                    token,
                    name=(
                        f"{TEST_PREFIX}"
                        "OWN_BRANCH_RELATIVE"
                    ),
                    relationship_type="child",
                    relative_to_person_id=(
                        own_relative_id
                    ),
                )

                results.append(
                    print_result(
                        2,
                        (
                            "user can extend "
                            "their own non-user "
                            "profile"
                        ),
                        response,
                        201,
                    )
                )

            else:
                print()
                print(
                    "[FAIL] Test 2: Test 1 "
                    "did not produce a Person ID."
                )

                results.append(
                    False
                )

            # =====================================
            # TEST 3
            #
            # lucia tries to add a relative
            # directly to Tony.
            #
            # Tony is a registered user.
            #
            # EXPECTED: 403
            # =====================================

            response = post_relative(
                client,
                token,
                name=(
                    f"{TEST_PREFIX}"
                    "TONY_RELATIVE"
                ),
                relationship_type="parent",
                relative_to_person_id=(
                    tony.id
                ),
            )

            results.append(
                print_result(
                    3,
                    (
                        "user cannot modify "
                        "another registered "
                        "user's branch"
                    ),
                    response,
                    403,
                )
            )

            # =====================================
            # TEST 4
            #
            # Create a non-user profile owned by
            # Tony but connected into lucia's
            # family network.
            #
            # Then lucia attempts to extend it.
            #
            # EXPECTED: 403
            # =====================================

            foreign_person = (
                create_temp_person(
                    name=(
                        f"{TEST_PREFIX}"
                        "TONY_CREATED_PROFILE"
                    ),
                    creator_user_id=(
                        tony_user.id
                    ),
                )
            )

            # Connect the temporary profile to
            # lucia so it IS in her family network.
            #
            # Therefore a 403 here proves the
            # creator ownership restriction is
            # working, rather than merely failing
            # the family-network check.

            create_relationship(
                lucia,
                foreign_person,
                "sibling",
                "sibling",
            )

            response = post_relative(
                client,
                token,
                name=(
                    f"{TEST_PREFIX}"
                    "FOREIGN_BRANCH_RELATIVE"
                ),
                relationship_type="child",
                relative_to_person_id=(
                    foreign_person.id
                ),
            )

            results.append(
                print_result(
                    4,
                    (
                        "user cannot extend "
                        "another user's "
                        "non-user profile"
                    ),
                    response,
                    403,
                )
            )

        finally:
            # -------------------------------------
            # Always clean test data, even if one
            # of the requests crashes.
            # -------------------------------------

            delete_test_people()

        # =========================================
        # SUMMARY
        # =========================================

        print()
        print(
            "=================================="
        )

        passed = sum(
            1
            for result in results
            if result
        )

        total = len(
            results
        )

        print(
            f"Result: {passed}/{total} passed"
        )

        if (
            total == 4
            and passed == 4
        ):
            print()
            print(
                "7.4B-1 PASSED"
            )

            sys.exit(0)

        print()
        print(
            "7.4B-1 FAILED"
        )

        sys.exit(1)


if __name__ == "__main__":
    main()