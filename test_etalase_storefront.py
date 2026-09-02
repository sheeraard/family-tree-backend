import json
import sys
import uuid
from urllib.error import HTTPError
from urllib.request import Request, urlopen


BASE_URL = "http://127.0.0.1:5000/api"

PASSWORD = "FamilyTest123!"


class TestRunner:
    def __init__(self):
        self.passed = 0
        self.failed = 0

    def check(
        self,
        condition,
        label,
        details=None,
    ):
        if condition:
            self.passed += 1
            print(
                f"✅ PASS — {label}"
            )
            return

        self.failed += 1

        print(
            f"❌ FAIL — {label}"
        )

        if details is not None:
            print(
                f"   {details}"
            )

    def summary(self):
        total = (
            self.passed
            + self.failed
        )

        print()
        print(
            "=" * 60
        )
        print(
            "ETALASE STOREFRONT "
            "TEST SUMMARY"
        )
        print(
            "=" * 60
        )

        print(
            f"Passed: "
            f"{self.passed}"
            f"/{total}"
        )

        print(
            f"Failed: "
            f"{self.failed}"
            f"/{total}"
        )

        if self.failed == 0:
            print()
            print(
                "🎉 9.3 STOREFRONT "
                "BACKEND TEST PASSED"
            )

            return 0

        print()
        print(
            "⚠️ Some 9.3 tests failed."
        )

        return 1


def api_request(
    method,
    path,
    *,
    token=None,
    body=None,
):
    url = (
        BASE_URL
        + path
    )

    headers = {
        "Accept":
            "application/json",
    }

    data = None

    if body is not None:
        headers[
            "Content-Type"
        ] = "application/json"

        data = json.dumps(
            body
        ).encode(
            "utf-8"
        )

    if token:
        headers[
            "Authorization"
        ] = (
            f"Bearer {token}"
        )

    request = Request(
        url=url,
        data=data,
        headers=headers,
        method=method,
    )

    try:
        with urlopen(
            request,
            timeout=10,
        ) as response:
            raw = (
                response
                .read()
                .decode(
                    "utf-8"
                )
            )

            try:
                parsed = (
                    json.loads(
                        raw
                    )
                    if raw
                    else {}
                )

            except json.JSONDecodeError:
                parsed = {
                    "raw":
                        raw
                }

            return (
                response.status,
                parsed,
            )

    except HTTPError as error:
        raw = (
            error
            .read()
            .decode(
                "utf-8"
            )
        )

        try:
            parsed = (
                json.loads(
                    raw
                )
                if raw
                else {}
            )

        except json.JSONDecodeError:
            parsed = {
                "raw":
                    raw
            }

        return (
            error.code,
            parsed,
        )

    except Exception as error:
        print()
        print(
            "❌ Could not reach backend:"
        )
        print(
            f"   {error}"
        )
        print()
        print(
            "Make sure this is running "
            "in another terminal:"
        )
        print(
            "   python run.py"
        )

        sys.exit(
            1
        )


def register_user(
    email,
    full_name,
):
    status, data = (
        api_request(
            "POST",
            "/auth/register",
            body={
                "email":
                    email,

                "password":
                    PASSWORD,

                "full_name":
                    full_name,
            },
        )
    )

    if status not in {
        200,
        201,
    }:
        raise RuntimeError(
            "Registration failed "
            f"for {email}: "
            f"{status} {data}"
        )


def login_user(
    email,
):
    status, data = (
        api_request(
            "POST",
            "/auth/login",
            body={
                "email":
                    email,

                "password":
                    PASSWORD,
            },
        )
    )

    if status != 200:
        raise RuntimeError(
            "Login failed "
            f"for {email}: "
            f"{status} {data}"
        )

    token = (
        data.get(
            "access_token"
        )
        or data.get(
            "token"
        )
    )

    if not token:
        raise RuntimeError(
            "Login succeeded but "
            "no access token was "
            f"returned: {data}"
        )

    return token


def create_product(
    token,
    *,
    name,
    price,
    category,
    description,
    contact,
):
    status, data = (
        api_request(
            "POST",
            "/products",
            token=token,
            body={
                "name":
                    name,

                "price":
                    price,

                "category":
                    category,

                "description":
                    description,

                "contact":
                    contact,
            },
        )
    )

    if status != 201:
        raise RuntimeError(
            "Product creation "
            f"failed: "
            f"{status} {data}"
        )

    product = (
        data.get(
            "product"
        )
    )

    if not product:
        raise RuntimeError(
            "Product creation "
            "returned no product: "
            f"{data}"
        )

    return product


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
    }


def main():
    tests = TestRunner()

    suffix = (
        uuid.uuid4()
        .hex[:10]
    )

    seller_a_email = (
        f"walter.white."
        f"{suffix}"
        "@etalase.test"
    )

    seller_b_email = (
        f"gus.fring."
        f"{suffix}"
        "@etalase.test"
    )

    print(
        "=" * 60
    )
    print(
        "PHASE 9.3 — "
        "SELLER STOREFRONT TEST"
    )
    print(
        "=" * 60
    )

    print()
    print(
        "Creating temporary "
        "test sellers..."
    )

    try:
        register_user(
            seller_a_email,
            "Walter White",
        )

        register_user(
            seller_b_email,
            "Gus Fring",
        )

        token_a = login_user(
            seller_a_email
        )

        token_b = login_user(
            seller_b_email
        )

    except RuntimeError as error:
        print(
            f"❌ SETUP FAILED — {error}"
        )
        return 1

    print(
        "✅ Test sellers ready"
    )

    print()
    print(
        "Creating test products..."
    )

    try:
        blue_sky = (
            create_product(
                token_a,
                name=(
                    "Blue Sky "
                    "Candy"
                ),
                price=25000,
                category="Food",
                description=(
                    "Definitely just "
                    "blue candy."
                ),
                contact=(
                    "081234567890"
                ),
            )
        )

        car_wash = (
            create_product(
                token_a,
                name=(
                    "A1 Car Wash "
                    "Voucher"
                ),
                price=75000,
                category="Service",
                description=(
                    "Premium car wash "
                    "voucher."
                ),
                contact=(
                    "081234567890"
                ),
            )
        )

        chicken = (
            create_product(
                token_b,
                name=(
                    "Los Pollos "
                    "Chicken"
                ),
                price=45000,
                category="Food",
                description=(
                    "Signature fried "
                    "chicken."
                ),
                contact=(
                    "https://example.com"
                ),
            )
        )

    except RuntimeError as error:
        print(
            f"❌ SETUP FAILED — {error}"
        )
        return 1

    seller_a_id = str(
        blue_sky.get(
            "seller_user_id"
        )
    )

    seller_b_id = str(
        chicken.get(
            "seller_user_id"
        )
    )

    tests.check(
        bool(
            seller_a_id
        )
        and seller_a_id
        != "None",

        "Created product exposes "
        "seller_user_id",

        blue_sky,
    )

    tests.check(
        seller_a_id
        != seller_b_id,

        "Different users have "
        "different seller IDs",
    )

    print()
    print(
        "Testing storefront "
        "filter..."
    )

    status, data = (
        api_request(
            "GET",
            (
                "/products"
                "?seller_user_id="
                f"{seller_a_id}"
            ),
            token=token_a,
        )
    )

    products = (
        data.get(
            "products",
            [],
        )
    )

    ids = product_ids(
        products
    )

    tests.check(
        status == 200,

        "Seller A storefront "
        "returns HTTP 200",

        (
            f"status={status}, "
            f"body={data}"
        ),
    )

    tests.check(
        str(
            blue_sky["id"]
        )
        in ids
        and str(
            car_wash["id"]
        )
        in ids,

        "Seller A storefront "
        "contains both Seller A "
        "products",

        products,
    )

    tests.check(
        str(
            chicken["id"]
        )
        not in ids,

        "Seller A storefront does "
        "not leak Seller B product",

        products,
    )

    tests.check(
        all(
            str(
                product.get(
                    "seller_user_id"
                )
            )
            == seller_a_id
            for product
            in products
        ),

        "Every Seller A storefront "
        "result belongs to Seller A",

        products,
    )

    print()
    print(
        "Testing Seller B "
        "storefront..."
    )

    status_b, data_b = (
        api_request(
            "GET",
            (
                "/products"
                "?seller_user_id="
                f"{seller_b_id}"
            ),
            token=token_a,
        )
    )

    products_b = (
        data_b.get(
            "products",
            [],
        )
    )

    ids_b = product_ids(
        products_b
    )

    tests.check(
        status_b == 200
        and str(
            chicken["id"]
        )
        in ids_b
        and str(
            blue_sky["id"]
        )
        not in ids_b,

        "Seller B storefront "
        "contains only Seller B "
        "test product",

        products_b,
    )

    print()
    print(
        "Testing hidden "
        "product behavior..."
    )

    hide_status, hide_data = (
        api_request(
            "PATCH",
            (
                "/products/"
                f"{car_wash['id']}"
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

    status, data = (
        api_request(
            "GET",
            (
                "/products"
                "?seller_user_id="
                f"{seller_a_id}"
            ),
            token=token_a,
        )
    )

    public_products = (
        data.get(
            "products",
            [],
        )
    )

    public_ids = (
        product_ids(
            public_products
        )
    )

    tests.check(
        str(
            blue_sky["id"]
        )
        in public_ids
        and str(
            car_wash["id"]
        )
        not in public_ids,

        "Hidden product disappears "
        "from seller storefront",

        public_products,
    )

    mine_status, mine_data = (
        api_request(
            "GET",
            "/products/mine",
            token=token_a,
        )
    )

    mine_products = (
        mine_data.get(
            "products",
            [],
        )
    )

    mine_ids = (
        product_ids(
            mine_products
        )
    )

    tests.check(
        mine_status == 200
        and str(
            car_wash["id"]
        )
        in mine_ids,

        "Hidden product remains in "
        "owner's My Products",

        mine_products,
    )

    hidden_entry = next(
        (
            product
            for product
            in mine_products
            if str(
                product.get(
                    "id"
                )
            )
            == str(
                car_wash["id"]
            )
        ),
        None,
    )

    tests.check(
        hidden_entry
        is not None
        and hidden_entry.get(
            "is_active"
        )
        is False,

        "My Products marks hidden "
        "product is_active=false",

        hidden_entry,
    )

    print()
    print(
        "Testing ownership "
        "protection..."
    )

    foreign_status, foreign_data = (
        api_request(
            "PATCH",
            (
                "/products/"
                f"{blue_sky['id']}"
            ),
            token=token_b,
            body={
                "name":
                    "Gus stole this",
            },
        )
    )

    tests.check(
        foreign_status == 403,

        "Another seller cannot "
        "edit Seller A product",

        (
            f"status="
            f"{foreign_status}, "
            f"body={foreign_data}"
        ),
    )

    print()
    print(
        "Testing invalid seller "
        "filter..."
    )

    invalid_status, invalid_data = (
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
        invalid_status == 400,

        "Invalid seller_user_id "
        "returns HTTP 400",

        (
            f"status="
            f"{invalid_status}, "
            f"body={invalid_data}"
        ),
    )

    print()
    print(
        "Restoring hidden "
        "test product..."
    )

    restore_status, restore_data = (
        api_request(
            "PATCH",
            (
                "/products/"
                f"{car_wash['id']}"
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

        "Owner can show hidden "
        "product again",

        (
            f"status="
            f"{restore_status}, "
            f"body={restore_data}"
        ),
    )

    print()
    print(
        "Final storefront "
        "verification..."
    )

    final_status, final_data = (
        api_request(
            "GET",
            (
                "/products"
                "?seller_user_id="
                f"{seller_a_id}"
            ),
            token=token_b,
        )
    )

    final_products = (
        final_data.get(
            "products",
            [],
        )
    )

    final_ids = (
        product_ids(
            final_products
        )
    )

    tests.check(
        final_status == 200
        and str(
            blue_sky["id"]
        )
        in final_ids
        and str(
            car_wash["id"]
        )
        in final_ids,

        "Restored product returns "
        "to Seller A storefront",

        final_products,
    )

    return tests.summary()


if __name__ == "__main__":
    sys.exit(
        main()
    )