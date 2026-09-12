from pathlib import Path, PurePosixPath

import boto3
from botocore.config import Config as BotoConfig
from flask import current_app


MEDIA_PRESIGNED_URL_SECONDS = 3600
MEDIA_CACHE_CONTROL = (
    "public, max-age=86400"
)


def _normalize_key(key):
    normalized = PurePosixPath(
        str(key)
    )

    if (
        normalized.is_absolute()
        or not normalized.parts
        or ".." in normalized.parts
    ):
        raise ValueError(
            "Invalid media key"
        )

    return normalized.as_posix()


def uses_object_storage():
    return (
        current_app.config.get(
            "MEDIA_STORAGE_BACKEND"
        )
        == "s3"
    )


def get_local_media_root():
    directory = (
        Path(
            current_app.root_path
        ).parent
        / "uploads"
    )

    directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    return directory


def _get_s3_client():
    client = (
        current_app.extensions.get(
            "media_storage_s3_client"
        )
    )

    if client is not None:
        return client

    client = boto3.client(
        "s3",
        endpoint_url=(
            current_app.config[
                "AWS_ENDPOINT_URL"
            ]
        ),
        aws_access_key_id=(
            current_app.config[
                "AWS_ACCESS_KEY_ID"
            ]
        ),
        aws_secret_access_key=(
            current_app.config[
                "AWS_SECRET_ACCESS_KEY"
            ]
        ),
        region_name=(
            current_app.config[
                "AWS_DEFAULT_REGION"
            ]
        ),
        config=BotoConfig(
            signature_version="s3v4",
            s3={
                "addressing_style": (
                    current_app.config[
                        "AWS_S3_URL_STYLE"
                    ]
                )
            },
        ),
    )

    current_app.extensions[
        "media_storage_s3_client"
    ] = client

    return client


def save_media_bytes(
    key,
    data,
    *,
    content_type="application/octet-stream",
):
    normalized_key = (
        _normalize_key(
            key
        )
    )

    if uses_object_storage():
        _get_s3_client().put_object(
            Bucket=(
                current_app.config[
                    "AWS_S3_BUCKET_NAME"
                ]
            ),
            Key=normalized_key,
            Body=data,
            ContentType=content_type,
            CacheControl=(
                MEDIA_CACHE_CONTROL
            ),
        )

        return

    path = (
        get_local_media_root()
        / Path(
            *PurePosixPath(
                normalized_key
            ).parts
        )
    )

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_bytes(
        data
    )


def delete_media(
    key,
):
    normalized_key = (
        _normalize_key(
            key
        )
    )

    if uses_object_storage():
        _get_s3_client().delete_object(
            Bucket=(
                current_app.config[
                    "AWS_S3_BUCKET_NAME"
                ]
            ),
            Key=normalized_key,
        )

        return

    path = (
        get_local_media_root()
        / Path(
            *PurePosixPath(
                normalized_key
            ).parts
        )
    )

    path.unlink(
        missing_ok=True
    )


def create_media_download_url(
    key,
):
    if not uses_object_storage():
        return None

    normalized_key = (
        _normalize_key(
            key
        )
    )

    return (
        _get_s3_client()
        .generate_presigned_url(
            "get_object",
            Params={
                "Bucket": (
                    current_app.config[
                        "AWS_S3_BUCKET_NAME"
                    ]
                ),
                "Key": normalized_key,
            },
            ExpiresIn=(
                MEDIA_PRESIGNED_URL_SECONDS
            ),
        )
    )