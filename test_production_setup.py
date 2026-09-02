import os
import subprocess
import sys


def result(
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
    checks = []

    #
    # Gunicorn installed
    #

    try:
        import gunicorn

        checks.append(
            result(
                "Gunicorn installed",
                True,
            )
        )

    except ImportError:
        checks.append(
            result(
                "Gunicorn installed",
                False,
                "pip install gunicorn",
            )
        )

    #
    # Production should reject
    # missing secrets.
    #

    environment = (
        os.environ.copy()
    )

    environment[
        "APP_ENV"
    ] = "production"

    #
    # Keep these variables present but
    # intentionally empty.
    #
    # This prevents python-dotenv from
    # silently loading the local .env
    # values back into the subprocess.
    #

    environment[
        "SECRET_KEY"
    ] = ""

    environment[
        "JWT_SECRET_KEY"
    ] = ""

    environment[
        "DATABASE_URL"
    ] = ""

    #
    # The import itself may raise the
    # expected RuntimeError because
    # Config is evaluated during import.
    #

    code = (
        "try:\n"
        "    from app import create_app\n"
        "    create_app()\n"
        "except RuntimeError:\n"
        "    raise SystemExit(0)\n"
        "\n"
        "raise SystemExit(1)\n"
    )

    process = subprocess.run(
        [
            sys.executable,
            "-c",
            code,
        ],
        env=environment,
    )

    checks.append(
        result(
            (
                "Production rejects "
                "missing secrets"
            ),
            process.returncode
            == 0,
        )
    )

    #
    # Production should start when all
    # required environment variables
    # are present.
    #

    environment[
        "SECRET_KEY"
    ] = (
        "test-production-secret"
    )

    environment[
        "JWT_SECRET_KEY"
    ] = (
        "test-production-jwt-secret"
    )

    environment[
        "DATABASE_URL"
    ] = (
        os.getenv(
            "DATABASE_URL",
            "postgresql+psycopg://localhost/family_tree",
        )
    )

    #
    # If DATABASE_URL is somehow blank in
    # the current shell, use the local
    # development database explicitly.
    #

    if not environment[
        "DATABASE_URL"
    ]:
        environment[
            "DATABASE_URL"
        ] = (
            "postgresql+psycopg://"
            "localhost/family_tree"
        )

    code = (
        "from app import create_app\n"
        "\n"
        "app = create_app()\n"
        "\n"
        "assert app.config['IS_PRODUCTION'] is True\n"
        "assert app.config['DEBUG'] is False\n"
        "\n"
        "print('Production app created')\n"
    )

    process = subprocess.run(
        [
            sys.executable,
            "-c",
            code,
        ],
        env=environment,
    )

    checks.append(
        result(
            (
                "Production app "
                "configuration loads"
            ),
            process.returncode
            == 0,
        )
    )

    #
    # Development still works.
    #

    from app import create_app

    development_app = (
        create_app()
    )

    checks.append(
        result(
            "Development app starts",
            development_app
            is not None,
        )
    )

    #
    # Health route still exists.
    #

    client = (
        development_app
        .test_client()
    )

    response = client.get(
        "/api/health"
    )

    checks.append(
        result(
            "Health endpoint reachable",
            response.status_code
            == 200,
            (
                f"HTTP "
                f"{response.status_code}"
            ),
        )
    )

    #
    # Final report
    #

    passed = sum(
        1
        for check
        in checks
        if check
    )

    total = len(
        checks
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
            "7.6 PRODUCTION SETUP PASSED"
        )

    else:
        print(
            "7.6 PRODUCTION SETUP FAILED"
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