from io import BytesIO
from pathlib import Path
from uuid import UUID, uuid4

from flask import (
    Blueprint,
    current_app,
    jsonify,
    redirect,
    request,
    send_from_directory,
)

from PIL import (
    Image,
    ImageOps,
    UnidentifiedImageError,
)

from app.extensions import db
from app.models.culture_content import (
    CultureContent,
)
from app.services.media_storage import (
    create_media_download_url,
    delete_media,
    save_media_bytes,
    uses_object_storage,
)
from app.utils.permissions import (
    admin_required,
)


culture_bp = Blueprint(
    "culture",
    __name__,
)


MAX_CULTURE_IMAGE_BYTES = (
    8 * 1024 * 1024
)

MAX_CULTURE_IMAGE_DIMENSION = 1800

MAX_CULTURE_IMAGES = 5

CULTURE_IMAGE_URL_PREFIX = (
    "/api/culture/images/"
)


def server_error_response(
    message,
    error,
):
    response = {
        "message": message,
    }

    if current_app.config[
        "DEBUG"
    ]:
        response[
            "error"
        ] = str(error)

    return jsonify(
        response
    ), 500


def _get_content_or_none(
    content_id,
):
    try:
        content_uuid = UUID(
            str(content_id)
        )

    except (
        ValueError,
        TypeError,
    ):
        return None

    return db.session.get(
        CultureContent,
        content_uuid,
    )


def _content_images(
    content,
):
    images = list(
        content.image_urls
        or []
    )

    if (
        not images
        and content.image_url
    ):
        images = [
            content.image_url
        ]

    return images


def get_culture_image_directory():
    directory = (
        Path(
            current_app.root_path
        ).parent
        / "uploads"
        / "culture_images"
    )

    directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    return directory


def delete_local_culture_image(
    image_url,
):
    if not image_url:
        return

    if not image_url.startswith(
        CULTURE_IMAGE_URL_PREFIX
    ):
        return

    filename = image_url[
        len(
            CULTURE_IMAGE_URL_PREFIX
        ):
    ]

    if (
        not filename
        or Path(filename).name
        != filename
    ):
        return

    media_key = (
        "culture_images/"
        + filename
    )

    try:
        delete_media(
            media_key
        )

    except Exception:
        current_app.logger.exception(
            "Could not delete culture image: %s",
            media_key,
        )


def _prepare_uploaded_image(
    uploaded_file,
):
    raw_bytes = uploaded_file.read(
        MAX_CULTURE_IMAGE_BYTES
        + 1
    )

    if not raw_bytes:
        return None, (
            jsonify({
                "message": (
                    "Image is empty"
                )
            }),
            400,
        )

    if (
        len(raw_bytes)
        > MAX_CULTURE_IMAGE_BYTES
    ):
        return None, (
            jsonify({
                "message": (
                    "Culture image must "
                    "be 8 MB or smaller"
                )
            }),
            413,
        )

    try:
        image = Image.open(
            BytesIO(
                raw_bytes
            )
        )

        image.verify()

        image = Image.open(
            BytesIO(
                raw_bytes
            )
        )

        image = ImageOps.exif_transpose(
            image
        )

        image.thumbnail(
            (
                MAX_CULTURE_IMAGE_DIMENSION,
                MAX_CULTURE_IMAGE_DIMENSION,
            )
        )

        if image.mode not in (
            "RGB",
            "L",
        ):
            background = Image.new(
                "RGB",
                image.size,
                "white",
            )

            if image.mode in (
                "RGBA",
                "LA",
            ):
                alpha = image.getchannel(
                    "A"
                )

                background.paste(
                    image,
                    mask=alpha,
                )

            else:
                background.paste(
                    image
                )

            image = background

        if image.mode != "RGB":
            image = image.convert(
                "RGB"
            )

        output_buffer = BytesIO()

        image.save(
            output_buffer,
            format="JPEG",
            quality=88,
            optimize=True,
        )

        return (
            output_buffer.getvalue(),
            None,
        )

    except (
        UnidentifiedImageError,
        OSError,
        ValueError,
    ):
        return None, (
            jsonify({
                "message": (
                    "Invalid image file"
                )
            }),
            400,
        )


@culture_bp.get("")
def get_culture_contents():
    contents = (
        CultureContent.query
        .filter_by(
            is_published=True
        )
        .order_by(
            CultureContent.created_at.desc()
        )
        .all()
    )

    return jsonify({
        "items": [
            content.to_dict()
            for content in contents
        ],
        "count": len(contents),
    }), 200


@culture_bp.get("/<content_id>")
def get_culture_content(
    content_id,
):
    content = _get_content_or_none(
        content_id
    )

    if (
        content is None
        or not content.is_published
    ):
        return jsonify({
            "message": (
                "Culture content not found"
            )
        }), 404

    return jsonify(
        content.to_dict()
    ), 200


@culture_bp.get("/admin")
@admin_required
def get_admin_culture_contents():
    contents = (
        CultureContent.query
        .order_by(
            CultureContent.created_at.desc()
        )
        .all()
    )

    return jsonify({
        "items": [
            content.to_dict()
            for content in contents
        ],
        "count": len(contents),
    }), 200


@culture_bp.post("")
@admin_required
def create_culture_content():
    data = request.get_json(
        silent=True
    ) or {}

    title = str(
        data.get(
            "title",
            "",
        )
    ).strip()

    description = str(
        data.get(
            "description",
            "",
        )
    ).strip()

    category = data.get(
        "category"
    )

    location = data.get(
        "location"
    )

    image_url = data.get(
        "image_url"
    )

    is_published = data.get(
        "is_published",
        True,
    )

    if not title:
        return jsonify({
            "message": (
                "Title is required"
            )
        }), 400

    if not description:
        return jsonify({
            "message": (
                "Description is required"
            )
        }), 400

    if category is not None:
        category = str(
            category
        ).strip() or None

    if location is not None:
        location = str(
            location
        ).strip() or None

    if image_url is not None:
        image_url = str(
            image_url
        ).strip() or None

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

    initial_images = (
        [image_url]
        if image_url
        else []
    )

    content = CultureContent(
        title=title,
        description=description,
        category=category,
        location=location,
        image_url=image_url,
        image_urls=initial_images,
        is_published=is_published,
    )

    db.session.add(
        content
    )

    db.session.commit()

    return jsonify({
        "message": (
            "Culture content created"
        ),
        "item": content.to_dict(),
    }), 201


@culture_bp.put("/<content_id>")
@admin_required
def update_culture_content(
    content_id,
):
    content = _get_content_or_none(
        content_id
    )

    if content is None:
        return jsonify({
            "message": (
                "Culture content not found"
            )
        }), 404

    data = request.get_json(
        silent=True
    ) or {}

    if "title" in data:
        title = str(
            data.get(
                "title",
                "",
            )
        ).strip()

        if not title:
            return jsonify({
                "message": (
                    "Title cannot be empty"
                )
            }), 400

        content.title = title

    if "description" in data:
        description = str(
            data.get(
                "description",
                "",
            )
        ).strip()

        if not description:
            return jsonify({
                "message": (
                    "Description cannot "
                    "be empty"
                )
            }), 400

        content.description = description

    if "category" in data:
        category = data.get(
            "category"
        )

        content.category = (
            str(category).strip()
            if category is not None
            else None
        )

        if content.category == "":
            content.category = None

    if "location" in data:
        location = data.get(
            "location"
        )

        content.location = (
            str(location).strip()
            if location is not None
            else None
        )

        if content.location == "":
            content.location = None

    # Kept for compatibility with older clients.
    # New clients upload images through /image.
    if "image_url" in data:
        image_url = data.get(
            "image_url"
        )

        content.image_url = (
            str(image_url).strip()
            if image_url is not None
            else None
        )

        if content.image_url == "":
            content.image_url = None

        if not content.image_urls:
            content.image_urls = (
                [content.image_url]
                if content.image_url
                else []
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

        content.is_published = is_published

    db.session.commit()

    return jsonify({
        "message": (
            "Culture content updated"
        ),
        "item": content.to_dict(),
    }), 200


@culture_bp.delete("/<content_id>")
@admin_required
def delete_culture_content(
    content_id,
):
    content = _get_content_or_none(
        content_id
    )

    if content is None:
        return jsonify({
            "message": (
                "Culture content not found"
            )
        }), 404

    old_images = _content_images(
        content
    )

    try:
        db.session.delete(
            content
        )

        db.session.commit()

        for image_url in old_images:
            delete_local_culture_image(
                image_url
            )

        return jsonify({
            "message": (
                "Culture content deleted"
            )
        }), 200

    except Exception as error:
        db.session.rollback()

        return server_error_response(
            "Failed to delete culture content",
            error,
        )


@culture_bp.post("/<content_id>/image")
@admin_required
def upload_culture_image(
    content_id,
):
    content = _get_content_or_none(
        content_id
    )

    if content is None:
        return jsonify({
            "message": (
                "Culture content not found"
            )
        }), 404

    uploaded_file = request.files.get(
        "image"
    )

    if not uploaded_file:
        return jsonify({
            "message": (
                "Image is required"
            )
        }), 400

    current_images = _content_images(
        content
    )

    if (
        len(current_images)
        >= MAX_CULTURE_IMAGES
    ):
        return jsonify({
            "message": (
                "A culture item can have "
                "at most 5 images"
            )
        }), 400

    image_bytes, error_response = (
        _prepare_uploaded_image(
            uploaded_file
        )
    )

    if error_response:
        return error_response

    filename = (
        f"{uuid4().hex}.jpg"
    )

    media_key = (
        "culture_images/"
        + filename
    )

    try:
        save_media_bytes(
            media_key,
            image_bytes,
            content_type="image/jpeg",
        )

        new_image_url = (
            CULTURE_IMAGE_URL_PREFIX
            + filename
        )

        current_images.append(
            new_image_url
        )

        content.image_urls = (
            current_images
        )

        content.image_url = (
            current_images[0]
        )

        db.session.commit()

        return jsonify({
            "message": (
                "Culture image uploaded"
            ),
            "item": content.to_dict(),
        }), 200

    except Exception as error:
        db.session.rollback()

        try:
            delete_media(
                media_key
            )

        except Exception:
            current_app.logger.exception(
                "Failed to clean up "
                "culture image after error"
            )

        return server_error_response(
            "Failed to upload culture image",
            error,
        )


@culture_bp.delete("/<content_id>/image")
@admin_required
def delete_culture_image(
    content_id,
):
    content = _get_content_or_none(
        content_id
    )

    if content is None:
        return jsonify({
            "message": (
                "Culture content not found"
            )
        }), 404

    current_images = _content_images(
        content
    )

    if not current_images:
        return jsonify({
            "message": (
                "Culture item has no image"
            ),
            "item": content.to_dict(),
        }), 200

    data = request.get_json(
        silent=True
    ) or {}

    image_url = str(
        data.get(
            "image_url",
            "",
        )
    ).strip()

    if not image_url:
        image_url = current_images[0]

    if image_url not in current_images:
        return jsonify({
            "message": (
                "Culture image not found"
            )
        }), 404

    updated_images = [
        url
        for url in current_images
        if url != image_url
    ]

    try:
        content.image_urls = (
            updated_images
        )

        content.image_url = (
            updated_images[0]
            if updated_images
            else None
        )

        db.session.commit()

        delete_local_culture_image(
            image_url
        )

        return jsonify({
            "message": (
                "Culture image deleted"
            ),
            "item": content.to_dict(),
        }), 200

    except Exception as error:
        db.session.rollback()

        return server_error_response(
            "Failed to delete culture image",
            error,
        )


@culture_bp.get("/images/<filename>")
def serve_culture_image(
    filename,
):
    if (
        Path(filename).name
        != filename
    ):
        return jsonify({
            "message": (
                "Invalid filename"
            )
        }), 400

    media_key = (
        "culture_images/"
        + filename
    )

    if uses_object_storage():
        try:
            return redirect(
                create_media_download_url(
                    media_key
                ),
                code=302,
            )

        except Exception as error:
            return server_error_response(
                "Failed to load culture image",
                error,
            )

    return send_from_directory(
        get_culture_image_directory(),
        filename,
    )