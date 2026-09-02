import json
import sys
import uuid
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen


BASE_URL = "http://127.0.0.1:5000/api"

PASSWORD = "FamilyTest123!"


class TestRunner:
    def __init__(self):
        self.passed = 0
        self.failed = 0

        self.sections = {}

    def section(self, name):
        print()
        print("=" * 68)
        print(name)
        print("=" * 68)

        if name not in self.sections:
            self.sections[name] = {
                "passed": 0,
                "failed": 0,
            }

        self.current_section = name

    def check(
        self,
        condition,
        label,
        details=None,
    ):
        section = self.sections[
            self.current_section
        ]

        if condition:
            self.passed += 1
            section["passed"] += 1

            print(
                f"✅ PASS — {label}"
            )

            return True

        self.failed += 1
        section["failed"] += 1

        print(
            f"❌ FAIL — {label}"
        )

        if details is not None:
            print(
                f"   {details}"
            )

        return False

    def summary(self):
        total = (
            self.passed
            + self.failed
        )

        print()
        print()
        print("=" * 68)
        print(
            "FINAL SYSTEM TEST SUMMARY"
        )
        print("=" * 68)

        for (
            section_name,
            result,
        ) in self.sections.items():
            passed = result[
                "passed"
            ]

            failed = result[
                "failed"
            ]

            section_total = (
                passed
                + failed
            )

            if failed == 0:
                status = "PASS"
            else:
                status = "FAIL"

            print(
                f"{section_name:<28}"
                f"{passed:>3}/"
                f"{section_total:<3} "
                f"{status}"
            )

        print("-" * 68)

        print(
            f"TOTAL PASSED: "
            f"{self.passed}/{total}"
        )

        print(
            f"TOTAL FAILED: "
            f"{self.failed}/{total}"
        )

        print("=" * 68)

        if self.failed == 0:
            print()
            print(
                "🎉 FINAL BACKEND REGRESSION PASSED"
            )

            print(
                "Backend is ready for the "
                "final Flutter smoke test."
            )

            return 0

        print()
        print(
            "⚠️ FINAL REGRESSION HAS FAILURES"
        )

        print(
            "Fix the failed checks before "
            "calling Step 10 complete."
        )

        return 1


def clean_exception_message(
    value,
):
    return (
        str(value)
        .replace(
            "\n",
            " ",
        )
        .strip()
    )


def api_request(
    method,
    path,
    *,
    token=None,
    body=None,
    timeout=10,
):
    url = (
        BASE_URL
        + path
    )

    headers = {
        "Accept":
            "application/json",
    }

    encoded_body = None

    if body is not None:
        headers[
            "Content-Type"
        ] = "application/json"

        encoded_body = (
            json.dumps(
                body
            )
            .encode(
                "utf-8"
            )
        )

    if token:
        headers[
            "Authorization"
        ] = (
            f"Bearer {token}"
        )

    request = Request(
        url=url,
        data=encoded_body,
        headers=headers,
        method=method,
    )

    try:
        with urlopen(
            request,
            timeout=timeout,
        ) as response:
            raw = (
                response.read()
                .decode(
                    "utf-8"
                )
            )

            return (
                response.status,
                decode_json(
                    raw
                ),
            )

    except HTTPError as error:
        raw = (
            error.read()
            .decode(
                "utf-8"
            )
        )

        return (
            error.code,
            decode_json(
                raw
            ),
        )

    except Exception as error:
        print()
        print(
            "❌ Cannot reach backend."
        )

        print(
            "   "
            + clean_exception_message(
                error
            )
        )

        print()
        print(
            "Run this in another terminal:"
        )

        print(
            "   cd ~/family_tree_app/backend"
        )

        print(
            "   source .venv/bin/activate"
        )

        print(
            "   python run.py"
        )

        sys.exit(
            1
        )


def decode_json(
    raw,
):
    if not raw:
        return {}

    try:
        data = json.loads(
            raw
        )

        if isinstance(
            data,
            dict,
        ):
            return data

        return {
            "data": data
        }

    except json.JSONDecodeError:
        return {
            "raw": raw
        }


def auth_header_exists(
    data,
):
    return bool(
        data.get(
            "access_token"
        )
        or data.get(
            "token"
        )
    )


def get_token(
    data,
):
    return (
        data.get(
            "access_token"
        )
        or data.get(
            "token"
        )
    )


def extract_person_id(
    data,
):
    """
    Extract the genealogy Person UUID.

    IMPORTANT:
    User.id and Person.id are different UUIDs.
    Always prefer the explicit person object.
    """

    if not isinstance(
        data,
        dict,
    ):
        return None

    # ----------------------------------------
    # Preferred response:
    #
    # {
    #     "user": {...},
    #     "person": {
    #         "id": "PERSON UUID"
    #     }
    # }
    # ----------------------------------------

    person = data.get(
        "person"
    )

    if isinstance(
        person,
        dict,
    ):
        person_id = (
            person.get(
                "id"
            )
        )

        if person_id:
            return str(
                person_id
            )

    # ----------------------------------------
    # Profile-style nested response
    # ----------------------------------------

    profile = data.get(
        "profile"
    )

    if isinstance(
        profile,
        dict,
    ):
        nested_person = (
            profile.get(
                "person"
            )
        )

        if isinstance(
            nested_person,
            dict,
        ):
            person_id = (
                nested_person.get(
                    "id"
                )
            )

            if person_id:
                return str(
                    person_id
                )

        person_id = (
            profile.get(
                "person_id"
            )
        )

        if person_id:
            return str(
                person_id
            )

    # ----------------------------------------
    # Some responses may expose person_id
    # directly.
    # ----------------------------------------

    direct_person_id = (
        data.get(
            "person_id"
        )
    )

    if direct_person_id:
        return str(
            direct_person_id
        )

    user = data.get(
        "user"
    )

    if isinstance(
        user,
        dict,
    ):
        nested_person = (
            user.get(
                "person"
            )
        )

        if isinstance(
            nested_person,
            dict,
        ):
            person_id = (
                nested_person.get(
                    "id"
                )
            )

            if person_id:
                return str(
                    person_id
                )

        person_id = (
            user.get(
                "person_id"
            )
        )

        if person_id:
            return str(
                person_id
            )

    return None


def extract_created_person(
    data,
):
    for key in (
        "person",
        "relative",
        "created_person",
    ):
        obj = data.get(
            key
        )

        if isinstance(
            obj,
            dict,
        ):
            if obj.get(
                "id"
            ):
                return obj

    return None


def extract_request_list(
    data,
):
    for key in (
        "requests",
        "incoming",
        "relationship_requests",
    ):
        value = data.get(
            key
        )

        if isinstance(
            value,
            list,
        ):
            return value

    return []


def extract_request_id(
    data,
):
    for key in (
        "request",
        "relationship_request",
    ):
        obj = data.get(
            key
        )

        if isinstance(
            obj,
            dict,
        ):
            value = obj.get(
                "id"
            )

            if value:
                return str(
                    value
                )

    if data.get(
        "id"
    ):
        return str(
            data["id"]
        )

    return None


def extract_products(
    data,
):
    products = data.get(
        "products"
    )

    if isinstance(
        products,
        list,
    ):
        return products

    return []


def product_ids(
    products,
):
    return {
        str(
            product.get(
                "id"
            )
        )
        for product
        in products
        if product.get(
            "id"
        )
    }


def find_product(
    products,
    product_id,
):
    for product in products:
        if (
            str(
                product.get(
                    "id"
                )
            )
            == str(
                product_id
            )
        ):
            return product

    return None


def register(
    email,
    full_name,
    *,
    claim_code=None,
):
    body = {
        "email":
            email,

        "password":
            PASSWORD,

        "full_name":
            full_name,
    }

    if claim_code:
        body[
            "claim_code"
        ] = claim_code

    return api_request(
        "POST",
        "/auth/register",
        body=body,
    )


def login(
    email,
    password=PASSWORD,
):
    return api_request(
        "POST",
        "/auth/login",
        body={
            "email":
                email,

            "password":
                password,
        },
    )


def create_product(
    token,
    name,
    price,
    category,
):
    return api_request(
        "POST",
        "/products",
        token=token,
        body={
            "name":
                name,

            "price":
                price,

            "description":
                (
                    f"Final regression "
                    f"product: {name}"
                ),

            "category":
                category,

            "contact":
                "081234567890",
        },
    )


def main():
    tests = TestRunner()

    suffix = (
        uuid.uuid4()
        .hex[:10]
    )

    email_a = (
        f"tony.soprano."
        f"{suffix}"
        "@final.test"
    )

    email_b = (
        f"silvio.dante."
        f"{suffix}"
        "@final.test"
    )

    email_claim = (
        f"christopher.moltisanti."
        f"{suffix}"
        "@final.test"
    )

    product_a_name = (
        f"Satriale Sandwich "
        f"{suffix}"
    )

    product_b_name = (
        f"Bada Bing Shirt "
        f"{suffix}"
    )

    print()
    print("=" * 68)
    print(
        "FAMILY TREE APP — "
        "FINAL SYSTEM REGRESSION"
    )
    print("=" * 68)

    print(
        "Run ID:",
        suffix,
    )

    print(
        "This test intentionally creates "
        "temporary database records."
    )

    # ==================================================
    # HEALTH / SECURITY
    # ==================================================

    tests.section(
        "Health & Security"
    )

    status, data = (
        api_request(
            "GET",
            "/health",
        )
    )

    tests.check(
        status == 200,
        "Health endpoint returns 200",
        (
            f"status={status}, "
            f"body={data}"
        ),
    )

    status, data = (
        api_request(
            "GET",
            "/auth/me",
        )
    )

    tests.check(
        status == 401,
        "Protected auth endpoint rejects no JWT",
        (
            f"status={status}, "
            f"body={data}"
        ),
    )

    status, data = (
        api_request(
            "GET",
            "/family/tree?depth=6",
        )
    )

    tests.check(
        status == 401,
        "Family tree rejects unauthenticated request",
        (
            f"status={status}, "
            f"body={data}"
        ),
    )

    status, data = (
        api_request(
            "GET",
            "/products",
        )
    )

    tests.check(
        status == 401,
        "Etalase rejects unauthenticated request",
        (
            f"status={status}, "
            f"body={data}"
        ),
    )

    # ==================================================
    # AUTH
    # ==================================================

    tests.section(
        "Authentication"
    )

    status_a, register_a = (
        register(
            email_a,
            "Tony Soprano",
        )
    )

    tests.check(
        status_a in {
            200,
            201,
        },
        "Register user A",
        (
            f"status={status_a}, "
            f"body={register_a}"
        ),
    )

    status_b, register_b = (
        register(
            email_b,
            "Silvio Dante",
        )
    )

    tests.check(
        status_b in {
            200,
            201,
        },
        "Register user B",
        (
            f"status={status_b}, "
            f"body={register_b}"
        ),
    )

    duplicate_status, duplicate_data = (
        register(
            email_a,
            "Duplicate Tony",
        )
    )

    tests.check(
        duplicate_status in {
            400,
            409,
        },
        "Duplicate email is rejected",
        (
            f"status="
            f"{duplicate_status}, "
            f"body={duplicate_data}"
        ),
    )

    bad_status, bad_data = (
        login(
            email_a,
            password=(
                "WrongPassword123!"
            ),
        )
    )

    tests.check(
        bad_status == 401,
        "Wrong password is rejected",
        (
            f"status={bad_status}, "
            f"body={bad_data}"
        ),
    )

    login_a_status, login_a_data = (
        login(
            email_a
        )
    )

    tests.check(
        login_a_status == 200
        and auth_header_exists(
            login_a_data
        ),
        "User A login returns token",
        (
            f"status="
            f"{login_a_status}, "
            f"body={login_a_data}"
        ),
    )

    login_b_status, login_b_data = (
        login(
            email_b
        )
    )

    tests.check(
        login_b_status == 200
        and auth_header_exists(
            login_b_data
        ),
        "User B login returns token",
        (
            f"status="
            f"{login_b_status}, "
            f"body={login_b_data}"
        ),
    )

    token_a = get_token(
        login_a_data
    )

    token_b = get_token(
        login_b_data
    )

    if not token_a or not token_b:
        print()
        print(
            "❌ Cannot continue without "
            "both login tokens."
        )

        return tests.summary()

    me_a_status, me_a = (
        api_request(
            "GET",
            "/auth/me",
            token=token_a,
        )
    )

    tests.check(
        me_a_status == 200,
        "GET /auth/me works for A",
        (
            f"status={me_a_status}, "
            f"body={me_a}"
        ),
    )

    me_b_status, me_b = (
        api_request(
            "GET",
            "/auth/me",
            token=token_b,
        )
    )

    tests.check(
        me_b_status == 200,
        "GET /auth/me works for B",
        (
            f"status={me_b_status}, "
            f"body={me_b}"
        ),
    )

    # ==================================================
    # PROFILE
    # ==================================================

    tests.section(
        "Profile"
    )

    profile_a_status, profile_a = (
        api_request(
            "GET",
            "/profile/me",
            token=token_a,
        )
    )

    tests.check(
        profile_a_status == 200,
        "Profile A loads",
        (
            f"status="
            f"{profile_a_status}, "
            f"body={profile_a}"
        ),
    )

    profile_b_status, profile_b = (
        api_request(
            "GET",
            "/profile/me",
            token=token_b,
        )
    )

    tests.check(
        profile_b_status == 200,
        "Profile B loads",
        (
            f"status="
            f"{profile_b_status}, "
            f"body={profile_b}"
        ),
    )

    person_a_id = (
        extract_person_id(
            profile_a
        )
        or extract_person_id(
            me_a
        )
    )

    person_b_id = (
        extract_person_id(
            profile_b
        )
        or extract_person_id(
            me_b
        )
    )

    tests.check(
        bool(
            person_a_id
        ),
        "User A has Person identity",
        profile_a,
    )

    tests.check(
        bool(
            person_b_id
        ),
        "User B has Person identity",
        profile_b,
    )

    if (
        not person_a_id
        or not person_b_id
    ):
        print()
        print(
            "❌ Cannot continue genealogy "
            "tests without person IDs."
        )

        return tests.summary()

    # ==================================================
    # PEOPLE SEARCH
    # ==================================================

    tests.section(
        "People Search"
    )

    search_status, search_data = (
        api_request(
            "GET",
            (
                "/people/search?q="
                + quote(
                    "Silvio Dante"
                )
            ),
            token=token_a,
        )
    )

    tests.check(
        search_status == 200,
        "People search returns 200",
        (
            f"status="
            f"{search_status}, "
            f"body={search_data}"
        ),
    )

    search_blob = (
        json.dumps(
            search_data
        )
        .lower()
    )

    tests.check(
        "silvio" in search_blob,
        "People search can find user B",
        search_data,
    )

    # ==================================================
    # RELATIONSHIP REQUEST
    # ==================================================

    tests.section(
        "Relationship Requests"
    )

    relationship_status, relationship_data = (
        api_request(
            "POST",
            "/relationships/requests",
            token=token_a,
            body={
                "receiver_person_id":
                    person_b_id,

                "relationship_type":
                    "sibling",
            },
        )
    )

    tests.check(
        relationship_status
        in {
            200,
            201,
        },
        "A sends sibling request to B",
        (
            f"status="
            f"{relationship_status}, "
            f"body={relationship_data}"
        ),
    )

    request_id = (
        extract_request_id(
            relationship_data
        )
    )

    incoming_status, incoming_data = (
        api_request(
            "GET",
            (
                "/relationships/"
                "requests/incoming"
            ),
            token=token_b,
        )
    )

    tests.check(
        incoming_status == 200,
        "B can load incoming requests",
        (
            f"status="
            f"{incoming_status}, "
            f"body={incoming_data}"
        ),
    )

    incoming = (
        extract_request_list(
            incoming_data
        )
    )

    if not request_id:
        for item in incoming:
            if not isinstance(
                item,
                dict,
            ):
                continue

            candidate_id = (
                item.get(
                    "id"
                )
            )

            if candidate_id:
                request_id = str(
                    candidate_id
                )

                break

    tests.check(
        bool(
            request_id
        ),
        "Relationship request ID can be resolved",
        incoming_data,
    )

    if request_id:
        accept_status, accept_data = (
            api_request(
                "POST",
                (
                    "/relationships/"
                    "requests/"
                    f"{request_id}/accept"
                ),
                token=token_b,
            )
        )

        tests.check(
            accept_status
            in {
                200,
                201,
            },
            "B accepts sibling request",
            (
                f"status="
                f"{accept_status}, "
                f"body={accept_data}"
            ),
        )

    # ==================================================
    # FAMILY
    # ==================================================

    tests.section(
        "Family & Tree"
    )

    family_status, family_data = (
        api_request(
            "GET",
            "/family",
            token=token_a,
        )
    )

    tests.check(
        family_status == 200,
        "GET /family returns 200",
        (
            f"status="
            f"{family_status}, "
            f"body={family_data}"
        ),
    )

    family_blob = (
        json.dumps(
            family_data
        )
        .lower()
    )

    tests.check(
        (
            "silvio" in family_blob
            or person_b_id.lower()
            in family_blob
        ),
        "Accepted sibling appears in family",
        family_data,
    )

    tree_status, tree_data = (
        api_request(
            "GET",
            "/family/tree?depth=6",
            token=token_a,
        )
    )

    tests.check(
        tree_status == 200,
        "Family tree depth 6 returns 200",
        (
            f"status="
            f"{tree_status}, "
            f"body={tree_data}"
        ),
    )

    nodes = tree_data.get(
        "nodes",
        []
    )

    tests.check(
        isinstance(
            nodes,
            list,
        )
        and len(
            nodes
        ) >= 2,
        "Tree contains at least A and B",
        tree_data,
    )

    tree_blob = (
        json.dumps(
            tree_data
        )
        .lower()
    )

    tests.check(
        (
            "silvio" in tree_blob
            or person_b_id.lower()
            in tree_blob
        ),
        "Sibling exists in tree payload",
        tree_data,
    )

    inference = tree_data.get(
        "inference"
    )

    tests.check(
        isinstance(
            inference,
            dict,
        ),
        "Tree exposes inference statistics",
        tree_data,
    )

    invalid_depth_status, invalid_depth_data = (
        api_request(
            "GET",
            "/family/tree?depth=abc",
            token=token_a,
        )
    )

    tests.check(
        invalid_depth_status == 400,
        "Invalid tree depth is rejected",
        (
            f"status="
            f"{invalid_depth_status}, "
            f"body={invalid_depth_data}"
        ),
    )

    # ==================================================
    # NON-USER RELATIVE
    # ==================================================

    tests.section(
        "Non-user Relative & Claim"
    )

    relative_status, relative_data = (
        api_request(
            "POST",
            "/people/non-user-relative",
            token=token_a,
            body={
                "relative_to_person_id":
                    person_a_id,

                "full_name":
                    (
                        "Christopher "
                        "Moltisanti "
                        f"{suffix}"
                    ),

                "relationship_type":
                    "child",

                "gender":
                    "male",
            },
        )
    )

    tests.check(
        relative_status
        in {
            200,
            201,
        },
        "Create non-user child",
        (
            f"status="
            f"{relative_status}, "
            f"body={relative_data}"
        ),
    )

    created_person = (
        extract_created_person(
            relative_data
        )
    )

    relative_person_id = (
        str(
            created_person[
                "id"
            ]
        )
        if created_person
        else None
    )

    tests.check(
        bool(
            relative_person_id
        ),
        "Created relative exposes person ID",
        relative_data,
    )

    if relative_person_id:
        tree_after_status, tree_after = (
            api_request(
                "GET",
                "/family/tree?depth=6",
                token=token_a,
            )
        )

        after_blob = (
            json.dumps(
                tree_after
            )
            .lower()
        )

        tests.check(
            tree_after_status == 200
            and relative_person_id.lower()
            in after_blob,
            "New child appears in family tree",
            tree_after,
        )

        unauthorized_claim_status, unauthorized_claim = (
            api_request(
                "GET",
                (
                    "/people/"
                    f"{relative_person_id}"
                    "/claim-code"
                ),
                token=token_b,
            )
        )

        tests.check(
            unauthorized_claim_status
            in {
                403,
                404,
            },
            "Other user cannot retrieve claim code",
            (
                f"status="
                f"{unauthorized_claim_status}, "
                f"body={unauthorized_claim}"
            ),
        )

        claim_status, claim_data = (
            api_request(
                "GET",
                (
                    "/people/"
                    f"{relative_person_id}"
                    "/claim-code"
                ),
                token=token_a,
            )
        )

        tests.check(
            claim_status == 200,
            "Creator can retrieve claim code",
            (
                f"status="
                f"{claim_status}, "
                f"body={claim_data}"
            ),
        )

        claim_code = (
            claim_data.get(
                "claim_code"
            )
            or claim_data.get(
                "code"
            )
        )

        tests.check(
            bool(
                claim_code
            ),
            "Claim code is returned",
            claim_data,
        )

        if claim_code:
            claimed_status, claimed_data = (
                register(
                    email_claim,
                    (
                        "Christopher "
                        "Moltisanti"
                    ),
                    claim_code=(
                        claim_code
                    ),
                )
            )

            tests.check(
                claimed_status
                in {
                    200,
                    201,
                },
                "Claim code can register account",
                (
                    f"status="
                    f"{claimed_status}, "
                    f"body={claimed_data}"
                ),
            )

    invalid_relative_status, invalid_relative_data = (
        api_request(
            "POST",
            "/people/non-user-relative",
            token=token_a,
            body={
                "relative_to_person_id":
                    person_a_id,

                "full_name":
                    "Bad Relative",

                "relationship_type":
                    "archnemesis",
            },
        )
    )

    tests.check(
        invalid_relative_status == 400,
        "Invalid relationship type is rejected",
        (
            f"status="
            f"{invalid_relative_status}, "
            f"body={invalid_relative_data}"
        ),
    )

    # ==================================================
    # ETALASE
    # ==================================================

    tests.section(
        "Etalase CRUD"
    )

    product_a_status, product_a_data = (
        create_product(
            token_a,
            product_a_name,
            45000,
            "Food",
        )
    )

    tests.check(
        product_a_status == 201,
        "Seller A creates product",
        (
            f"status="
            f"{product_a_status}, "
            f"body={product_a_data}"
        ),
    )

    product_a = (
        product_a_data.get(
            "product"
        )
    )

    product_a_id = (
        str(
            product_a.get(
                "id"
            )
        )
        if isinstance(
            product_a,
            dict,
        )
        and product_a.get(
            "id"
        )
        else None
    )

    tests.check(
        bool(
            product_a_id
        ),
        "Created product A exposes ID",
        product_a_data,
    )

    product_b_status, product_b_data = (
        create_product(
            token_b,
            product_b_name,
            125000,
            "Fashion",
        )
    )

    tests.check(
        product_b_status == 201,
        "Seller B creates product",
        (
            f"status="
            f"{product_b_status}, "
            f"body={product_b_data}"
        ),
    )

    product_b = (
        product_b_data.get(
            "product"
        )
    )

    product_b_id = (
        str(
            product_b.get(
                "id"
            )
        )
        if isinstance(
            product_b,
            dict,
        )
        and product_b.get(
            "id"
        )
        else None
    )

    tests.check(
        bool(
            product_b_id
        ),
        "Created product B exposes ID",
        product_b_data,
    )

    invalid_price_status, invalid_price_data = (
        api_request(
            "POST",
            "/products",
            token=token_a,
            body={
                "name":
                    "Invalid Product",

                "price":
                    -100,
            },
        )
    )

    tests.check(
        invalid_price_status == 400,
        "Negative product price is rejected",
        (
            f"status="
            f"{invalid_price_status}, "
            f"body={invalid_price_data}"
        ),
    )

    public_status, public_data = (
        api_request(
            "GET",
            "/products",
            token=token_a,
        )
    )

    public_products = (
        extract_products(
            public_data
        )
    )

    public_ids = (
        product_ids(
            public_products
        )
    )

    tests.check(
        public_status == 200,
        "Public Etalase returns 200",
        (
            f"status="
            f"{public_status}, "
            f"body={public_data}"
        ),
    )

    tests.check(
        (
            not product_a_id
            or product_a_id
            in public_ids
        )
        and (
            not product_b_id
            or product_b_id
            in public_ids
        ),
        "Public Etalase contains both test products",
        public_products,
    )

    search_status, search_products_data = (
        api_request(
            "GET",
            (
                "/products?q="
                + quote(
                    product_a_name
                )
            ),
            token=token_a,
        )
    )

    search_products = (
        extract_products(
            search_products_data
        )
    )

    search_ids = (
        product_ids(
            search_products
        )
    )

    tests.check(
        search_status == 200
        and (
            product_a_id is None
            or product_a_id
            in search_ids
        ),
        "Etalase search finds product A",
        search_products_data,
    )

    category_status, category_data = (
        api_request(
            "GET",
            (
                "/products"
                "?category=Food"
            ),
            token=token_a,
        )
    )

    category_products = (
        extract_products(
            category_data
        )
    )

    tests.check(
        category_status == 200
        and all(
            str(
                item.get(
                    "category",
                    "",
                )
            ).lower()
            == "food"
            for item
            in category_products
        ),
        "Category filter only returns Food",
        category_data,
    )

    # ==================================================
    # STOREFRONT
    # ==================================================

    tests.section(
        "Seller Storefront"
    )

    seller_a_id = (
        str(
            product_a.get(
                "seller_user_id"
            )
        )
        if isinstance(
            product_a,
            dict,
        )
        else ""
    )

    seller_b_id = (
        str(
            product_b.get(
                "seller_user_id"
            )
        )
        if isinstance(
            product_b,
            dict,
        )
        else ""
    )

    tests.check(
        bool(
            seller_a_id
        )
        and seller_a_id
        != "None",
        "Product A exposes seller_user_id",
        product_a,
    )

    tests.check(
        seller_a_id
        != seller_b_id,
        "Seller A and B have different IDs",
    )

    storefront_status, storefront_data = (
        api_request(
            "GET",
            (
                "/products"
                "?seller_user_id="
                + quote(
                    seller_a_id
                )
            ),
            token=token_b,
        )
    )

    storefront_products = (
        extract_products(
            storefront_data
        )
    )

    storefront_ids = (
        product_ids(
            storefront_products
        )
    )

    tests.check(
        storefront_status == 200,
        "Seller storefront returns 200",
        storefront_data,
    )

    tests.check(
        (
            product_a_id is None
            or product_a_id
            in storefront_ids
        )
        and (
            product_b_id is None
            or product_b_id
            not in storefront_ids
        ),
        "Seller storefront isolates seller products",
        storefront_products,
    )

    invalid_seller_status, invalid_seller_data = (
        api_request(
            "GET",
            (
                "/products"
                "?seller_user_id="
                "not-a-uuid"
            ),
            token=token_a,
        )
    )

    tests.check(
        invalid_seller_status == 400,
        "Invalid seller UUID is rejected",
        (
            f"status="
            f"{invalid_seller_status}, "
            f"body={invalid_seller_data}"
        ),
    )

    # ==================================================
    # PRODUCT OWNERSHIP / HIDDEN
    # ==================================================

    tests.section(
        "Etalase Ownership"
    )

    if product_a_id:
        unauthorized_edit_status, unauthorized_edit = (
            api_request(
                "PATCH",
                (
                    "/products/"
                    f"{product_a_id}"
                ),
                token=token_b,
                body={
                    "name":
                        "Stolen Product",
                },
            )
        )

        tests.check(
            unauthorized_edit_status == 403,
            "Other seller cannot edit product A",
            (
                f"status="
                f"{unauthorized_edit_status}, "
                f"body={unauthorized_edit}"
            ),
        )

        hide_status, hide_data = (
            api_request(
                "PATCH",
                (
                    "/products/"
                    f"{product_a_id}"
                ),
                token=token_a,
                body={
                    "is_active":
                        False,
                },
            )
        )

        tests.check(
            hide_status == 200,
            "Owner can hide product",
            (
                f"status="
                f"{hide_status}, "
                f"body={hide_data}"
            ),
        )

        after_hide_status, after_hide_data = (
            api_request(
                "GET",
                "/products",
                token=token_a,
            )
        )

        after_hide_ids = (
            product_ids(
                extract_products(
                    after_hide_data
                )
            )
        )

        tests.check(
            after_hide_status == 200
            and product_a_id
            not in after_hide_ids,
            "Hidden product disappears publicly",
            after_hide_data,
        )

        mine_status, mine_data = (
            api_request(
                "GET",
                "/products/mine",
                token=token_a,
            )
        )

        mine_products = (
            extract_products(
                mine_data
            )
        )

        mine_ids = (
            product_ids(
                mine_products
            )
        )

        tests.check(
            mine_status == 200
            and product_a_id
            in mine_ids,
            "Hidden product remains in My Products",
            mine_data,
        )

        mine_product = (
            find_product(
                mine_products,
                product_a_id,
            )
        )

        tests.check(
            isinstance(
                mine_product,
                dict,
            )
            and mine_product.get(
                "is_active"
            )
            is False,
            "Hidden product reports is_active=false",
            mine_product,
        )

        tests.check(
            isinstance(
                mine_product,
                dict,
            )
            and mine_product.get(
                "is_owner"
            )
            is True,
            "My product reports is_owner=true",
            mine_product,
        )

        restore_status, restore_data = (
            api_request(
                "PATCH",
                (
                    "/products/"
                    f"{product_a_id}"
                ),
                token=token_a,
                body={
                    "is_active":
                        True,
                },
            )
        )

        tests.check(
            restore_status == 200,
            "Owner can restore hidden product",
            (
                f"status="
                f"{restore_status}, "
                f"body={restore_data}"
            ),
        )

    # ==================================================
    # DELETE PRODUCT
    # ==================================================

    tests.section(
        "Etalase Delete"
    )

    if product_a_id:
        foreign_delete_status, foreign_delete = (
            api_request(
                "DELETE",
                (
                    "/products/"
                    f"{product_a_id}"
                ),
                token=token_b,
            )
        )

        tests.check(
            foreign_delete_status == 403,
            "Other seller cannot delete product A",
            (
                f"status="
                f"{foreign_delete_status}, "
                f"body={foreign_delete}"
            ),
        )

        delete_status, delete_data = (
            api_request(
                "DELETE",
                (
                    "/products/"
                    f"{product_a_id}"
                ),
                token=token_a,
            )
        )

        tests.check(
            delete_status == 200,
            "Owner can delete product A",
            (
                f"status="
                f"{delete_status}, "
                f"body={delete_data}"
            ),
        )

        final_products_status, final_products_data = (
            api_request(
                "GET",
                "/products",
                token=token_a,
            )
        )

        final_ids = (
            product_ids(
                extract_products(
                    final_products_data
                )
            )
        )

        tests.check(
            final_products_status == 200
            and product_a_id
            not in final_ids,
            "Deleted product stays gone",
            final_products_data,
        )

    # ==================================================
    # FINAL FAMILY RECHECK
    # ==================================================

    tests.section(
        "Final Regression"
    )

    final_family_status, final_family = (
        api_request(
            "GET",
            "/family",
            token=token_a,
        )
    )

    tests.check(
        final_family_status == 200,
        "Family API still works after all operations",
        final_family,
    )

    final_tree_status, final_tree = (
        api_request(
            "GET",
            "/family/tree?depth=6",
            token=token_a,
        )
    )

    tests.check(
        final_tree_status == 200,
        "Family tree still works after all operations",
        final_tree,
    )

    final_profile_status, final_profile = (
        api_request(
            "GET",
            "/profile/me",
            token=token_a,
        )
    )

    tests.check(
        final_profile_status == 200,
        "Profile still works after all operations",
        final_profile,
    )

    final_products_status, final_products = (
        api_request(
            "GET",
            "/products",
            token=token_a,
        )
    )

    tests.check(
        final_products_status == 200,
        "Etalase still works after all operations",
        final_products,
    )

    return tests.summary()


if __name__ == "__main__":
    sys.exit(
        main()
    )