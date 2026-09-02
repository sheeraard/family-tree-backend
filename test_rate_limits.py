from app import create_app


app = create_app()


EXPECTED_LIMITS = {
    "auth.register": "5 per hour",
    "auth.login": "10 per minute",
    "people.search_people": "30 per minute",
    "people.get_person_claim_code": "5 per hour",
    "people.create_non_user_relative": "20 per hour",
    "relationships.send_relationship_request": "20 per hour",
}


def print_result(
    name,
    passed,
    detail="",
):
    status = (
        "PASS"
        if passed
        else "FAIL"
    )

    print(
        f"[{status}] {name}"
    )

    if detail:
        print(
            f"       {detail}"
        )

    return passed


def main():
    results = []

    with app.app_context():

        #
        # TEST 1
        # Required routes exist.
        #

        for endpoint in EXPECTED_LIMITS:
            exists = (
                endpoint
                in app.view_functions
            )

            results.append(
                print_result(
                    (
                        "Endpoint exists: "
                        f"{endpoint}"
                    ),
                    exists,
                )
            )

        #
        # TEST 2
        # Login rate limit actually triggers.
        #
        # Invalid credentials are intentional.
        #
        # We only care that request #11
        # becomes HTTP 429.
        #

        client = app.test_client()

        statuses = []

        for number in range(
            1,
            12,
        ):
            response = client.post(
                "/api/auth/login",
                json={
                    "email": (
                        "__rate_limit_test__"
                        "@test.local"
                    ),
                    "password": (
                        "DefinitelyWrong123!"
                    ),
                },
            )

            statuses.append(
                response.status_code
            )

            print(
                f"Login request "
                f"{number:02d}: "
                f"HTTP "
                f"{response.status_code}"
            )

        first_ten_not_limited = (
            429
            not in statuses[:10]
        )

        eleventh_limited = (
            statuses[10]
            == 429
        )

        results.append(
            print_result(
                (
                    "First 10 login attempts "
                    "are allowed through limiter"
                ),
                first_ten_not_limited,
                (
                    f"Statuses: "
                    f"{statuses[:10]}"
                ),
            )
        )

        results.append(
            print_result(
                (
                    "11th login attempt "
                    "returns HTTP 429"
                ),
                eleventh_limited,
                (
                    f"Status: "
                    f"{statuses[10]}"
                ),
            )
        )

        #
        # TEST 3
        # 429 response is JSON.
        #

        response = client.post(
            "/api/auth/login",
            json={
                "email": (
                    "__rate_limit_test__"
                    "@test.local"
                ),
                "password": (
                    "DefinitelyWrong123!"
                ),
            },
        )

        json_body = (
            response.get_json(
                silent=True
            )
        )

        valid_json_error = (
            response.status_code
            == 429
            and isinstance(
                json_body,
                dict,
            )
            and json_body.get(
                "message"
            )
            == (
                "Too many requests. "
                "Please try again later."
            )
        )

        results.append(
            print_result(
                (
                    "Rate-limit response "
                    "uses JSON"
                ),
                valid_json_error,
                str(
                    json_body
                ),
            )
        )

    passed = sum(
        1
        for result
        in results
        if result
    )

    total = len(
        results
    )

    print()
    print(
        "=" * 60
    )

    print(
        f"{passed}/{total} PASSED"
    )

    if passed == total:
        print(
            "7.5 RATE LIMITING PASSED"
        )

    else:
        print(
            "7.5 RATE LIMITING FAILED"
        )

    print(
        "=" * 60
    )

    if passed != total:
        raise SystemExit(
            1
        )


if __name__ == "__main__":
    main()