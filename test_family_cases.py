from flask_jwt_extended import create_access_token
from werkzeug.security import generate_password_hash

from app import create_app
from app.extensions import db
from app.models import Person, Relationship, User


# ============================================================
# CONFIG
# ============================================================

TEST_EMAIL_SUFFIX = ".familycase@test.local"

DEFAULT_PASSWORD = "FamilyTest123!"


# ============================================================
# APP
# ============================================================

app = create_app()


# ============================================================
# HELPERS
# ============================================================

def create_person_account(
    full_name,
    email_name,
    gender,
):
    """
    Create:
        User
        Person

    Every test character gets an account so
    they can be logged into manually in Flutter.
    """

    email = (
        f"{email_name}"
        f"{TEST_EMAIL_SUFFIX}"
    )

    user = User(
        email=email,
        password_hash=generate_password_hash(
            DEFAULT_PASSWORD,
            method="pbkdf2:sha256",
        ),
        is_active=True,
    )

    db.session.add(user)
    db.session.flush()

    person = Person(
        full_name=full_name,
        gender=gender,
        user_id=user.id,
    )

    db.session.add(person)
    db.session.flush()

    return {
        "user": user,
        "person": person,
        "email": email,
    }


def add_relationship(
    person_a,
    person_b,
    relation_a_to_b,
    relation_b_to_a,
):
    relationship = Relationship(
        person_a_id=person_a.id,
        person_b_id=person_b.id,
        relation_a_to_b=relation_a_to_b,
        relation_b_to_a=relation_b_to_a,
        verification_status="verified",
    )

    db.session.add(
        relationship
    )

    return relationship


def add_parent(
    child,
    parent,
):
    """
    Relationship semantics used by the app:

    child -> parent = "parent"
    parent -> child = "child"
    """

    return add_relationship(
        child,
        parent,
        "parent",
        "child",
    )


def add_sibling(
    person_a,
    person_b,
):
    return add_relationship(
        person_a,
        person_b,
        "sibling",
        "sibling",
    )


def add_spouse(
    person_a,
    person_b,
):
    return add_relationship(
        person_a,
        person_b,
        "spouse",
        "spouse",
    )


def get_tree(
    client,
    user,
):
    token = create_access_token(
        identity=str(
            user.id
        )
    )

    response = client.get(
        "/api/family/tree?depth=6",
        headers={
            "Authorization": (
                f"Bearer {token}"
            )
        },
    )

    if response.status_code != 200:
        raise RuntimeError(
            "Tree endpoint failed.\n"
            f"Status: {response.status_code}\n"
            f"Response: {response.get_data(as_text=True)}"
        )

    return response.get_json()


def nodes_by_name(
    tree,
):
    return {
        node["full_name"]: node
        for node in tree[
            "nodes"
        ]
    }


def get_node(
    tree,
    name,
):
    nodes = nodes_by_name(
        tree
    )

    return nodes.get(
        name
    )


def get_edge_between(
    tree,
    name_a,
    name_b,
):
    id_to_name = {
        node["id"]: (
            node[
                "full_name"
            ]
        )
        for node
        in tree["nodes"]
    }

    for edge in tree[
        "edges"
    ]:
        source_name = (
            id_to_name.get(
                edge[
                    "source_person_id"
                ]
            )
        )

        target_name = (
            id_to_name.get(
                edge[
                    "target_person_id"
                ]
            )
        )

        if {
            source_name,
            target_name,
        } == {
            name_a,
            name_b,
        }:
            return edge

    return None


def relationship_from_to(
    tree,
    source_name,
    target_name,
):
    """
    Return the semantic relationship from
    source_name -> target_name.
    """

    id_to_name = {
        node["id"]: (
            node[
                "full_name"
            ]
        )
        for node
        in tree["nodes"]
    }

    for edge in tree[
        "edges"
    ]:
        actual_source = (
            id_to_name.get(
                edge[
                    "source_person_id"
                ]
            )
        )

        actual_target = (
            id_to_name.get(
                edge[
                    "target_person_id"
                ]
            )
        )

        if (
            actual_source
            == source_name
            and actual_target
            == target_name
        ):
            return edge.get(
                "semantic_source_to_target",
                edge.get(
                    "source_to_target"
                ),
            )

        if (
            actual_source
            == target_name
            and actual_target
            == source_name
        ):
            return edge.get(
                "semantic_target_to_source",
                edge.get(
                    "target_to_source"
                ),
            )

    return None


# ============================================================
# CLEAN OLD TEST DATA
# ============================================================

def clean_previous_test_data():
    users = (
        db.session.scalars(
            db.select(
                User
            ).where(
                User.email.like(
                    f"%{TEST_EMAIL_SUFFIX}"
                )
            )
        )
        .all()
    )

    if not users:
        return

    user_ids = [
        user.id
        for user
        in users
    ]

    people = (
        db.session.scalars(
            db.select(
                Person
            ).where(
                Person.user_id.in_(
                    user_ids
                )
            )
        )
        .all()
    )

    person_ids = [
        person.id
        for person
        in people
    ]

    if person_ids:
        db.session.execute(
            db.delete(
                Relationship
            ).where(
                (
                    Relationship
                    .person_a_id
                    .in_(
                        person_ids
                    )
                )
                |
                (
                    Relationship
                    .person_b_id
                    .in_(
                        person_ids
                    )
                )
            )
        )

        db.session.execute(
            db.delete(
                Person
            ).where(
                Person.id.in_(
                    person_ids
                )
            )
        )

    db.session.execute(
        db.delete(
            User
        ).where(
            User.id.in_(
                user_ids
            )
        )
    )

    db.session.commit()


# ============================================================
# CASE 1
#
# THE SOPRANOS
#
# Tests:
# - sibling parent propagation
# - inferred co-parent
# - inferred parents remain biological parents
#
# Only Tony initially has Johnny Boy and Livia
# registered as parents.
#
# Janice + Barbara are explicit siblings.
#
# Engine should propagate Tony's known parents.
# ============================================================

def seed_sopranos():
    family = {}

    family["Tony"] = (
        create_person_account(
            "Tony Soprano",
            "tony.soprano",
            "male",
        )
    )

    family["Janice"] = (
        create_person_account(
            "Janice Soprano",
            "janice.soprano",
            "female",
        )
    )

    family["Barbara"] = (
        create_person_account(
            "Barbara Soprano",
            "barbara.soprano",
            "female",
        )
    )

    family["Livia"] = (
        create_person_account(
            "Livia Soprano",
            "livia.soprano",
            "female",
        )
    )

    family["Johnny"] = (
        create_person_account(
            "Johnny Boy Soprano",
            "johnnyboy.soprano",
            "male",
        )
    )

    add_parent(
        family["Tony"][
            "person"
        ],
        family["Livia"][
            "person"
        ],
    )

    add_parent(
        family["Tony"][
            "person"
        ],
        family["Johnny"][
            "person"
        ],
    )

    add_sibling(
        family["Tony"][
            "person"
        ],
        family["Janice"][
            "person"
        ],
    )

    add_sibling(
        family["Janice"][
            "person"
        ],
        family["Barbara"][
            "person"
        ],
    )

    return family


# ============================================================
# CASE 2
#
# MODERN FAMILY
#
#                   Dede
#                     |
#                   Claire
#                     |
#                    Jay ===== Gloria
#                              /    \
#                          Manny    Joe
#                            |
#                         Javier
#
# More accurately:
#
# Jay + Dede
#     |
#   Claire
#
# Jay + Gloria
#     |
#    Joe
#
# Gloria + Javier
#     |
#   Manny
#
#
# Tests:
# - multiple partners
# - half siblings
# - spouse vs co-parent
# - step-parent
# - former/unmarried co-parent safety
# ============================================================

def seed_modern_family():
    family = {}

    family["Jay"] = (
        create_person_account(
            "Jay Pritchett",
            "jay.pritchett",
            "male",
        )
    )

    family["Gloria"] = (
        create_person_account(
            "Gloria Delgado-Pritchett",
            "gloria.pritchett",
            "female",
        )
    )

    family["Dede"] = (
        create_person_account(
            "DeDe Pritchett",
            "dede.pritchett",
            "female",
        )
    )

    family["Claire"] = (
        create_person_account(
            "Claire Dunphy",
            "claire.dunphy",
            "female",
        )
    )

    family["Joe"] = (
        create_person_account(
            "Joe Pritchett",
            "joe.pritchett",
            "male",
        )
    )

    family["Manny"] = (
        create_person_account(
            "Manny Delgado",
            "manny.delgado",
            "male",
        )
    )

    family["Javier"] = (
        create_person_account(
            "Javier Delgado",
            "javier.delgado",
            "male",
        )
    )

    # Claire's biological parents

    add_parent(
        family["Claire"][
            "person"
        ],
        family["Jay"][
            "person"
        ],
    )

    add_parent(
        family["Claire"][
            "person"
        ],
        family["Dede"][
            "person"
        ],
    )

    # Joe's biological parents

    add_parent(
        family["Joe"][
            "person"
        ],
        family["Jay"][
            "person"
        ],
    )

    add_parent(
        family["Joe"][
            "person"
        ],
        family["Gloria"][
            "person"
        ],
    )

    # Manny's biological parents

    add_parent(
        family["Manny"][
            "person"
        ],
        family["Gloria"][
            "person"
        ],
    )

    add_parent(
        family["Manny"][
            "person"
        ],
        family["Javier"][
            "person"
        ],
    )

    # Explicit sibling claims.
    #
    # Engine must classify these as HALF,
    # because they share exactly one parent.

    add_sibling(
        family["Claire"][
            "person"
        ],
        family["Joe"][
            "person"
        ],
    )

    add_sibling(
        family["Manny"][
            "person"
        ],
        family["Joe"][
            "person"
        ],
    )

    # Jay + Gloria are explicitly married.

    add_spouse(
        family["Jay"][
            "person"
        ],
        family["Gloria"][
            "person"
        ],
    )

    return family


# ============================================================
# CASE 3
#
# THE SIMPSONS
#
#                     Abe
#                      |
#                    Homer === Marge
#                              /   \
#                         Patty    Selma
#                                   |
#                                  Ling
#
#                    Homer + Marge
#                         |
#                    Bart + Lisa
#
#
# Tests:
# - normal spouse
# - full siblings
# - shared children on spouse edge
# - grandparent
# - aunt
# - cousin
# - in-law
# ============================================================

def seed_simpsons():
    family = {}

    family["Homer"] = (
        create_person_account(
            "Homer Simpson",
            "homer.simpson",
            "male",
        )
    )

    family["Marge"] = (
        create_person_account(
            "Marge Simpson",
            "marge.simpson",
            "female",
        )
    )

    family["Bart"] = (
        create_person_account(
            "Bart Simpson",
            "bart.simpson",
            "male",
        )
    )

    family["Lisa"] = (
        create_person_account(
            "Lisa Simpson",
            "lisa.simpson",
            "female",
        )
    )

    family["Abe"] = (
        create_person_account(
            "Abe Simpson",
            "abe.simpson",
            "male",
        )
    )

    family["Patty"] = (
        create_person_account(
            "Patty Bouvier",
            "patty.bouvier",
            "female",
        )
    )

    family["Selma"] = (
        create_person_account(
            "Selma Bouvier",
            "selma.bouvier",
            "female",
        )
    )

    family["Ling"] = (
        create_person_account(
            "Ling Bouvier",
            "ling.bouvier",
            "female",
        )
    )

    add_spouse(
        family["Homer"][
            "person"
        ],
        family["Marge"][
            "person"
        ],
    )

    add_parent(
        family["Bart"][
            "person"
        ],
        family["Homer"][
            "person"
        ],
    )

    add_parent(
        family["Bart"][
            "person"
        ],
        family["Marge"][
            "person"
        ],
    )

    add_parent(
        family["Lisa"][
            "person"
        ],
        family["Homer"][
            "person"
        ],
    )

    add_parent(
        family["Lisa"][
            "person"
        ],
        family["Marge"][
            "person"
        ],
    )

    add_sibling(
        family["Bart"][
            "person"
        ],
        family["Lisa"][
            "person"
        ],
    )

    add_parent(
        family["Homer"][
            "person"
        ],
        family["Abe"][
            "person"
        ],
    )

    add_sibling(
        family["Marge"][
            "person"
        ],
        family["Patty"][
            "person"
        ],
    )

    add_sibling(
        family["Marge"][
            "person"
        ],
        family["Selma"][
            "person"
        ],
    )

    add_sibling(
        family["Patty"][
            "person"
        ],
        family["Selma"][
            "person"
        ],
    )

    add_parent(
        family["Ling"][
            "person"
        ],
        family["Selma"][
            "person"
        ],
    )

    return family


# ============================================================
# TEST REPORTER
# ============================================================

class TestReporter:

    def __init__(self):
        self.results = []

    def check(
        self,
        name,
        condition,
        success_detail="",
        failure_detail="",
    ):
        result = {
            "name": name,
            "passed": bool(
                condition
            ),
            "detail": (
                success_detail
                if condition
                else failure_detail
            ),
        }

        self.results.append(
            result
        )

    def summary(self):
        passed = sum(
            1
            for result
            in self.results
            if result[
                "passed"
            ]
        )

        total = len(
            self.results
        )

        print()
        print(
            "=" * 70
        )
        print(
            "FAMILY RELATIONSHIP TEST RESULTS"
        )
        print(
            "=" * 70
        )

        for result in (
            self.results
        ):
            icon = (
                "PASS"
                if result[
                    "passed"
                ]
                else "FAIL"
            )

            print(
                f"[{icon}] "
                f"{result['name']}"
            )

            if result[
                "detail"
            ]:
                print(
                    f"       "
                    f"{result['detail']}"
                )

        print(
            "-" * 70
        )

        print(
            f"{passed}/{total} PASSED"
        )

        if passed == total:
            print()
            print(
                "ALL FAMILY TESTS PASSED"
            )

        else:
            print()
            print(
                "SOME FAMILY TESTS FAILED"
            )

        print(
            "=" * 70
        )

        return (
            passed,
            total,
        )


# ============================================================
# TESTS
# ============================================================

def run_tests(
    sopranos,
    modern,
    simpsons,
):
    reporter = TestReporter()

    client = (
        app.test_client()
    )

    # --------------------------------------------------------
    # SOPRANOS
    # --------------------------------------------------------

    janice_tree = get_tree(
        client,
        sopranos[
            "Janice"
        ][
            "user"
        ],
    )

    janice_nodes = (
        nodes_by_name(
            janice_tree
        )
    )

    reporter.check(
        "Sopranos: Janice inherits Livia as mother",
        (
            "Livia Soprano"
            in janice_nodes
            and janice_nodes[
                "Livia Soprano"
            ][
                "derived_relationship"
            ]
            == "Mother"
        ),
        success_detail=(
            "Livia correctly inferred as Janice's mother."
        ),
        failure_detail=(
            "Livia was not inferred as Janice's mother."
        ),
    )

    reporter.check(
        "Sopranos: Janice inherits Johnny Boy as father",
        (
            "Johnny Boy Soprano"
            in janice_nodes
            and janice_nodes[
                "Johnny Boy Soprano"
            ][
                "derived_relationship"
            ]
            == "Father"
        ),
        success_detail=(
            "Johnny Boy correctly inferred as Janice's father."
        ),
        failure_detail=(
            "Johnny Boy was not inferred as Janice's father."
        ),
    )

    barbara_tree = get_tree(
        client,
        sopranos[
            "Barbara"
        ][
            "user"
        ],
    )

    barbara_nodes = (
        nodes_by_name(
            barbara_tree
        )
    )

    reporter.check(
        "Sopranos: Barbara inherits both parents",
        (
            "Livia Soprano"
            in barbara_nodes
            and
            "Johnny Boy Soprano"
            in barbara_nodes
        ),
        success_detail=(
            "Barbara received Tony's known parents."
        ),
        failure_detail=(
            "Barbara did not receive both inferred parents."
        ),
    )

    livia_tree = get_tree(
        client,
        sopranos[
            "Livia"
        ][
            "user"
        ],
    )

    livia_nodes = (
        nodes_by_name(
            livia_tree
        )
    )

    reporter.check(
        "Sopranos: Johnny Boy is Co-parent, not Husband",
        (
            "Johnny Boy Soprano"
            in livia_nodes
            and livia_nodes[
                "Johnny Boy Soprano"
            ][
                "derived_relationship"
            ]
            == "Co-parent"
        ),
        success_detail=(
            "Shared children did not create a fake marriage."
        ),
        failure_detail=(
            "Johnny Boy was incorrectly labelled as spouse/husband."
        ),
    )

    reporter.check(
        "Sopranos: co-parent edge is semantically co_parent",
        (
            relationship_from_to(
                livia_tree,
                "Livia Soprano",
                "Johnny Boy Soprano",
            )
            == "co_parent"
        ),
        success_detail=(
            "Backend semantic edge is co_parent."
        ),
        failure_detail=(
            "Backend semantic edge was not co_parent."
        ),
    )

    # --------------------------------------------------------
    # MODERN FAMILY
    # --------------------------------------------------------

    manny_tree = get_tree(
        client,
        modern[
            "Manny"
        ][
            "user"
        ],
    )

    manny_nodes = (
        nodes_by_name(
            manny_tree
        )
    )

    reporter.check(
        "Modern Family: Joe is Manny's half-brother",
        (
            "Joe Pritchett"
            in manny_nodes
            and manny_nodes[
                "Joe Pritchett"
            ][
                "derived_relationship"
            ]
            == "Half-brother"
        ),
        success_detail=(
            "One shared parent correctly produces half-sibling."
        ),
        failure_detail=(
            "Joe was not labelled Half-brother."
        ),
    )

    joe_manny_edge = (
        get_edge_between(
            manny_tree,
            "Manny Delgado",
            "Joe Pritchett",
        )
    )

    reporter.check(
        "Modern Family: Manny/Joe sibling_type = half",
        (
            joe_manny_edge
            is not None
            and joe_manny_edge.get(
                "sibling_type"
            )
            == "half"
        ),
        success_detail=(
            "Sibling metadata correctly classified as half."
        ),
        failure_detail=(
            "Sibling metadata was not classified as half."
        ),
    )

    claire_tree = get_tree(
        client,
        modern[
            "Claire"
        ][
            "user"
        ],
    )

    claire_nodes = (
        nodes_by_name(
            claire_tree
        )
    )

    reporter.check(
        "Modern Family: Joe is Claire's half-brother",
        (
            "Joe Pritchett"
            in claire_nodes
            and claire_nodes[
                "Joe Pritchett"
            ][
                "derived_relationship"
            ]
            == "Half-brother"
        ),
        success_detail=(
            "Claire and Joe share Jay only."
        ),
        failure_detail=(
            "Claire/Joe half-sibling classification failed."
        ),
    )

    reporter.check(
        "Modern Family: Jay is Manny's stepfather",
        (
            "Jay Pritchett"
            in manny_nodes
            and manny_nodes[
                "Jay Pritchett"
            ][
                "derived_relationship"
            ]
            == "Stepfather"
        ),
        success_detail=(
            "Parent -> explicit spouse correctly produces step-parent."
        ),
        failure_detail=(
            "Jay was not labelled Stepfather for Manny."
        ),
    )

    gloria_tree = get_tree(
        client,
        modern[
            "Gloria"
        ][
            "user"
        ],
    )

    gloria_nodes = (
        nodes_by_name(
            gloria_tree
        )
    )

    reporter.check(
        "Modern Family: Jay stays Husband",
        (
            "Jay Pritchett"
            in gloria_nodes
            and gloria_nodes[
                "Jay Pritchett"
            ][
                "derived_relationship"
            ]
            == "Husband"
        ),
        success_detail=(
            "Explicit spouse relationship stayed spouse."
        ),
        failure_detail=(
            "Explicit spouse relationship was lost."
        ),
    )

    reporter.check(
        "Modern Family: Javier is only Co-parent",
        (
            "Javier Delgado"
            in gloria_nodes
            and gloria_nodes[
                "Javier Delgado"
            ][
                "derived_relationship"
            ]
            == "Co-parent"
        ),
        success_detail=(
            "Javier was not incorrectly treated as husband."
        ),
        failure_detail=(
            "Javier was incorrectly treated as spouse."
        ),
    )

    dede_tree = get_tree(
        client,
        modern[
            "Dede"
        ][
            "user"
        ],
    )

    dede_nodes = (
        nodes_by_name(
            dede_tree
        )
    )

    reporter.check(
        "Modern Family: Jay is only Co-parent to DeDe",
        (
            "Jay Pritchett"
            in dede_nodes
            and dede_nodes[
                "Jay Pritchett"
            ][
                "derived_relationship"
            ]
            == "Co-parent"
        ),
        success_detail=(
            "Former relationship was not invented as current marriage."
        ),
        failure_detail=(
            "Jay was incorrectly inferred as DeDe's husband."
        ),
    )

    modern_stats = (
        manny_tree.get(
            "inference",
            {},
        )
    )

    reporter.check(
        "Modern Family: multiple partners detected",
        (
            modern_stats.get(
                "multiple_partner_people",
                0,
            )
            >= 2
        ),
        success_detail=(
            "Jay and Gloria both have multiple co-parent pairings."
        ),
        failure_detail=(
            "Multiple-partner inference did not detect expected people."
        ),
    )

    # --------------------------------------------------------
    # SIMPSONS
    # --------------------------------------------------------

    bart_tree = get_tree(
        client,
        simpsons[
            "Bart"
        ][
            "user"
        ],
    )

    bart_nodes = (
        nodes_by_name(
            bart_tree
        )
    )

    reporter.check(
        "Simpsons: Lisa is Bart's full sister",
        (
            "Lisa Simpson"
            in bart_nodes
            and bart_nodes[
                "Lisa Simpson"
            ][
                "derived_relationship"
            ]
            == "Sister"
        ),
        success_detail=(
            "Normal full sibling relationship works."
        ),
        failure_detail=(
            "Lisa was not labelled Sister."
        ),
    )

    bart_lisa_edge = (
        get_edge_between(
            bart_tree,
            "Bart Simpson",
            "Lisa Simpson",
        )
    )

    reporter.check(
        "Simpsons: Bart/Lisa sibling_type = full",
        (
            bart_lisa_edge
            is not None
            and bart_lisa_edge.get(
                "sibling_type"
            )
            == "full"
        ),
        success_detail=(
            "Two shared parents correctly classified as full siblings."
        ),
        failure_detail=(
            "Bart/Lisa were not classified as full siblings."
        ),
    )

    reporter.check(
        "Simpsons: Abe is Bart's grandfather",
        (
            "Abe Simpson"
            in bart_nodes
            and bart_nodes[
                "Abe Simpson"
            ][
                "derived_relationship"
            ]
            == "Grandfather"
        ),
        success_detail=(
            "Grandparent traversal works."
        ),
        failure_detail=(
            "Abe was not labelled Grandfather."
        ),
    )

    reporter.check(
        "Simpsons: Patty is Bart's aunt",
        (
            "Patty Bouvier"
            in bart_nodes
            and bart_nodes[
                "Patty Bouvier"
            ][
                "derived_relationship"
            ]
            == "Aunt"
        ),
        success_detail=(
            "Parent -> sibling correctly produced Aunt."
        ),
        failure_detail=(
            "Patty was not labelled Aunt."
        ),
    )

    reporter.check(
        "Simpsons: Ling is Bart's cousin",
        (
            "Ling Bouvier"
            in bart_nodes
            and bart_nodes[
                "Ling Bouvier"
            ][
                "derived_relationship"
            ]
            == "Cousin"
        ),
        success_detail=(
            "Parent -> sibling -> child produced Cousin."
        ),
        failure_detail=(
            "Ling was not labelled Cousin."
        ),
    )

    homer_tree = get_tree(
        client,
        simpsons[
            "Homer"
        ][
            "user"
        ],
    )

    homer_nodes = (
        nodes_by_name(
            homer_tree
        )
    )

    reporter.check(
        "Simpsons: Marge stays Wife",
        (
            "Marge Simpson"
            in homer_nodes
            and homer_nodes[
                "Marge Simpson"
            ][
                "derived_relationship"
            ]
            == "Wife"
        ),
        success_detail=(
            "Explicit marriage works normally."
        ),
        failure_detail=(
            "Marge was not labelled Wife."
        ),
    )

    reporter.check(
        "Simpsons: Patty is Homer's sister-in-law",
        (
            "Patty Bouvier"
            in homer_nodes
            and homer_nodes[
                "Patty Bouvier"
            ][
                "derived_relationship"
            ]
            == "Sister-in-law"
        ),
        success_detail=(
            "Spouse -> sibling produced Sister-in-law."
        ),
        failure_detail=(
            "Patty was not labelled Sister-in-law."
        ),
    )

    homer_marge_edge = (
        get_edge_between(
            homer_tree,
            "Homer Simpson",
            "Marge Simpson",
        )
    )

    expected_child_ids = {
        str(
            simpsons[
                "Bart"
            ][
                "person"
            ].id
        ),
        str(
            simpsons[
                "Lisa"
            ][
                "person"
            ].id
        ),
    }

    actual_child_ids = set(
        (
            homer_marge_edge
            or {}
        ).get(
            "shared_child_ids",
            [],
        )
    )

    reporter.check(
        "Simpsons: spouse pair records both shared children",
        (
            expected_child_ids
            == actual_child_ids
        ),
        success_detail=(
            "Homer/Marge pair contains Bart and Lisa."
        ),
        failure_detail=(
            "Shared-child metadata did not contain both children."
        ),
    )

    return reporter.summary()


# ============================================================
# CREDENTIAL PRINTING
# ============================================================

def print_credentials(
    sopranos,
    modern,
    simpsons,
):
    print()
    print(
        "=" * 70
    )
    print(
        "LOGIN ACCOUNTS"
    )
    print(
        "=" * 70
    )

    print()
    print(
        "THE SOPRANOS"
    )
    print(
        "-" * 70
    )

    for member in (
        sopranos.values()
    ):
        print(
            f"{member['person'].full_name:<28} "
            f"{member['email']}"
        )

    print()
    print(
        "MODERN FAMILY"
    )
    print(
        "-" * 70
    )

    for member in (
        modern.values()
    ):
        print(
            f"{member['person'].full_name:<28} "
            f"{member['email']}"
        )

    print()
    print(
        "THE SIMPSONS"
    )
    print(
        "-" * 70
    )

    for member in (
        simpsons.values()
    ):
        print(
            f"{member['person'].full_name:<28} "
            f"{member['email']}"
        )

    print()
    print(
        f"PASSWORD FOR ALL ACCOUNTS: "
        f"{DEFAULT_PASSWORD}"
    )

    print(
        "=" * 70
    )


# ============================================================
# MAIN
# ============================================================

def main():

    with app.app_context():

        print()
        print(
            "Removing previous family-case test data..."
        )

        clean_previous_test_data()

        print(
            "Creating fictional test families..."
        )

        sopranos = (
            seed_sopranos()
        )

        modern = (
            seed_modern_family()
        )

        simpsons = (
            seed_simpsons()
        )

        db.session.commit()

        print(
            "Families saved to database."
        )

        print_credentials(
            sopranos,
            modern,
            simpsons,
        )

        passed, total = (
            run_tests(
                sopranos,
                modern,
                simpsons,
            )
        )

        print()
        print(
            "NOTE:"
        )

        print(
            "The fictional families were intentionally "
            "LEFT in the database."
        )

        print(
            "Run this script again to delete and recreate "
            "only these test accounts."
        )

        if passed != total:
            raise SystemExit(
                1
            )


if __name__ == "__main__":
    main()