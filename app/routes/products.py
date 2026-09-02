from io import BytesIO
from pathlib import Path
from uuid import UUID, uuid4

from flask import (
    Blueprint,
    current_app,
    jsonify,
    request,
    send_from_directory,
)

from flask_jwt_extended import (
    get_jwt_identity,
    jwt_required,
)

from PIL import (
    Image,
    ImageOps,
    UnidentifiedImageError,
)

from app.extensions import db
from app.models import Product, User


products_bp = Blueprint(
    "products",
    __name__,
)


MAX_PRODUCT_IMAGE_BYTES = (
    8 * 1024 * 1024
)

MAX_PRODUCT_IMAGE_DIMENSION = 1800

PRODUCT_IMAGE_URL_PREFIX = (
    "/api/products/images/"
)


def server_error_response(
    message,
    error,
):
    response = {
        "message": message
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


def get_current_user():
    user_id = (
        get_jwt_identity()
    )

    try:
        user_uuid = UUID(
            str(user_id)
        )

    except (
        ValueError,
        TypeError,
    ):
        return None

    return db.session.get(
        User,
        user_uuid,
    )


def get_product_image_directory():
    directory = (
        Path(
            current_app.root_path
        ).parent
        / "uploads"
        / "product_images"
    )

    directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    return directory


def delete_local_product_image(
    image_url,
):
    if not image_url:
        return

    if not image_url.startswith(
        PRODUCT_IMAGE_URL_PREFIX
    ):
        return

    filename = image_url[
        len(
            PRODUCT_IMAGE_URL_PREFIX
        ):
    ]

    if (
        not filename
        or Path(filename).name
        != filename
    ):
        return

    path = (
        get_product_image_directory()
        / filename
    )

    try:
        path.unlink(
            missing_ok=True
        )

    except OSError:
        current_app.logger.warning(
            "Could not delete "
            "product image: %s",
            path,
        )


def seller_name(
    product,
):
    if (
        product.seller
        and product.seller.person
    ):
        return (
            product
            .seller
            .person
            .full_name
        )

    if product.seller:
        return (
            product.seller.email
        )

    return "Unknown seller"


def serialize_product(
    product,
    current_user_id=None,
):
    return {
        "id": str(
            product.id
        ),

        "seller_user_id": str(
            product.seller_user_id
        ),

        "seller_name": (
            seller_name(
                product
            )
        ),

        "name": product.name,

        "description": (
            product.description
        ),

        "price": (
            product.price
        ),

        "category": (
            product.category
        ),

        "contact": (
            product.contact
        ),

        "image_url": (
            product.image_url
        ),

        "image_urls": (
            list(
                product.image_urls
                or []
            )
            or (
                [product.image_url]
                if product.image_url
                else []
            )
        ),

        "is_active": (
            product.is_active
        ),

        "is_owner": (
            current_user_id
            is not None
            and product.seller_user_id
            == current_user_id
        ),

        "created_at": (
            product.created_at
            .isoformat()
            if product.created_at
            else None
        ),

        "updated_at": (
            product.updated_at
            .isoformat()
            if product.updated_at
            else None
        ),
    }


def parse_price(
    value,
):
    if isinstance(
        value,
        bool,
    ):
        return None

    try:
        price = int(
            value
        )

    except (
        ValueError,
        TypeError,
    ):
        return None

    if price < 0:
        return None

    return price


def validate_text(
    value,
    max_length,
    field_name,
):
    if value is None:
        return None, None

    text = str(
        value
    ).strip()

    if not text:
        return None, None

    if len(text) > max_length:
        return None, (
            f"{field_name} "
            f"must be at most "
            f"{max_length} characters"
        )

    return text, None


def get_owned_product(
    product_id,
    user,
):
    try:
        product_uuid = UUID(
            str(product_id)
        )

    except (
        ValueError,
        TypeError,
    ):
        return None, (
            jsonify({
                "message": (
                    "Invalid product ID"
                )
            }),
            400,
        )

    product = db.session.get(
        Product,
        product_uuid,
    )

    if not product:
        return None, (
            jsonify({
                "message": (
                    "Product not found"
                )
            }),
            404,
        )

    if (
        product.seller_user_id
        != user.id
    ):
        return None, (
            jsonify({
                "message": (
                    "You can only edit "
                    "your own products"
                )
            }),
            403,
        )

    return product, None


@products_bp.route(
    "",
    methods=["GET"],
)
@jwt_required()
def list_products():
    user = get_current_user()

    if not user:
        return jsonify({
            "message": "Invalid user"
        }), 401

    category = str(
        request.args.get(
            "category",
            "",
        )
    ).strip()

    search = str(
        request.args.get(
            "q",
            "",
        )
    ).strip()

    seller_user_id_raw = str(
        request.args.get(
            "seller_user_id",
            "",
        )
    ).strip()

    statement = (
        db.select(
            Product
        )
        .where(
            Product.is_active
            .is_(True)
        )
        .order_by(
            Product.created_at
            .desc()
        )
    )

    if category:
        statement = (
            statement.where(
                Product.category.ilike(
                    category
                )
            )
        )

    if seller_user_id_raw:
        try:
            seller_user_id = UUID(
                seller_user_id_raw
            )

        except (
            ValueError,
            TypeError,
        ):
            return jsonify({
                "message": (
                    "Invalid seller_user_id"
                )
            }), 400

        statement = (
            statement.where(
                Product.seller_user_id
                == seller_user_id
            )
        )

    if search:
        search_term = (
            f"%{search}%"
        )

        statement = (
            statement.where(
                db.or_(
                    Product.name.ilike(
                        search_term
                    ),

                    Product.description
                    .ilike(
                        search_term
                    ),

                    Product.category.ilike(
                        search_term
                    ),
                )
            )
        )

    products = (
        db.session.scalars(
            statement.limit(
                100
            )
        )
        .all()
    )

    return jsonify({
        "products": [
            serialize_product(
                product,
                current_user_id=(
                    user.id
                ),
            )
            for product
            in products
        ],

        "count": len(
            products
        ),
    }), 200


@products_bp.route(
    "/mine",
    methods=["GET"],
)
@jwt_required()
def list_my_products():
    user = get_current_user()

    if not user:
        return jsonify({
            "message": (
                "Invalid user"
            )
        }), 401

    products = (
        db.session.scalars(
            db.select(
                Product
            )
            .where(
                Product.seller_user_id
                == user.id
            )
            .order_by(
                Product.created_at
                .desc()
            )
        )
        .all()
    )

    return jsonify({
        "products": [
            serialize_product(
                product,
                current_user_id=(
                    user.id
                ),
            )
            for product
            in products
        ],

        "count": len(
            products
        ),
    }), 200


@products_bp.route(
    "",
    methods=["POST"],
)
@jwt_required()
def create_product():
    user = get_current_user()

    if not user:
        return jsonify({
            "message": (
                "Invalid user"
            )
        }), 401

    data = request.get_json(
        silent=True
    )

    if not data:
        return jsonify({
            "message": (
                "Request body "
                "must be JSON"
            )
        }), 400

    name, error = (
        validate_text(
            data.get(
                "name"
            ),
            160,
            "name",
        )
    )

    if error:
        return jsonify({
            "message": error
        }), 400

    if not name:
        return jsonify({
            "message": (
                "Product name "
                "is required"
            )
        }), 400

    price = parse_price(
        data.get(
            "price"
        )
    )

    if price is None:
        return jsonify({
            "message": (
                "price must be a "
                "non-negative "
                "whole number"
            )
        }), 400

    description, error = (
        validate_text(
            data.get(
                "description"
            ),
            3000,
            "description",
        )
    )

    if error:
        return jsonify({
            "message": error
        }), 400

    category, error = (
        validate_text(
            data.get(
                "category"
            ),
            80,
            "category",
        )
    )

    if error:
        return jsonify({
            "message": error
        }), 400

    contact, error = (
        validate_text(
            data.get(
                "contact"
            ),
            255,
            "contact",
        )
    )

    if error:
        return jsonify({
            "message": error
        }), 400

    try:
        product = Product(
            seller_user_id=(
                user.id
            ),

            name=name,

            description=(
                description
            ),

            price=price,

            category=(
                category
            ),

            contact=(
                contact
            ),

            is_active=True,
        )

        db.session.add(
            product
        )

        db.session.commit()

        return jsonify({
            "message": (
                "Product created"
            ),

            "product": (
                serialize_product(
                    product,
                    current_user_id=(
                        user.id
                    ),
                )
            ),
        }), 201

    except Exception as error:
        db.session.rollback()

        return (
            server_error_response(
                "Failed to "
                "create product",
                error,
            )
        )


@products_bp.route(
    "/<product_id>",
    methods=["PATCH"],
)
@jwt_required()
def update_product(
    product_id,
):
    user = get_current_user()

    if not user:
        return jsonify({
            "message": (
                "Invalid user"
            )
        }), 401

    (
        product,
        error_response,
    ) = get_owned_product(
        product_id,
        user,
    )

    if error_response:
        return error_response

    data = request.get_json(
        silent=True
    )

    if not data:
        return jsonify({
            "message": (
                "Request body "
                "must be JSON"
            )
        }), 400

    if "name" in data:
        name, error = (
            validate_text(
                data.get(
                    "name"
                ),
                160,
                "name",
            )
        )

        if error:
            return jsonify({
                "message": error
            }), 400

        if not name:
            return jsonify({
                "message": (
                    "Product name "
                    "cannot be empty"
                )
            }), 400

        product.name = name

    if "price" in data:
        price = parse_price(
            data.get(
                "price"
            )
        )

        if price is None:
            return jsonify({
                "message": (
                    "price must be a "
                    "non-negative "
                    "whole number"
                )
            }), 400

        product.price = price

    if "description" in data:
        description, error = (
            validate_text(
                data.get(
                    "description"
                ),
                3000,
                "description",
            )
        )

        if error:
            return jsonify({
                "message": error
            }), 400

        product.description = (
            description
        )

    if "category" in data:
        category, error = (
            validate_text(
                data.get(
                    "category"
                ),
                80,
                "category",
            )
        )

        if error:
            return jsonify({
                "message": error
            }), 400

        product.category = (
            category
        )

    if "contact" in data:
        contact, error = (
            validate_text(
                data.get(
                    "contact"
                ),
                255,
                "contact",
            )
        )

        if error:
            return jsonify({
                "message": error
            }), 400

        product.contact = (
            contact
        )

    if "is_active" in data:
        is_active = data.get(
            "is_active"
        )

        if not isinstance(
            is_active,
            bool,
        ):
            return jsonify({
                "message": (
                    "is_active must "
                    "be true or false"
                )
            }), 400

        product.is_active = (
            is_active
        )

    try:
        db.session.commit()

        return jsonify({
            "message": (
                "Product updated"
            ),

            "product": (
                serialize_product(
                    product,
                    current_user_id=(
                        user.id
                    ),
                )
            ),
        }), 200

    except Exception as error:
        db.session.rollback()

        return (
            server_error_response(
                "Failed to "
                "update product",
                error,
            )
        )


@products_bp.route(
    "/<product_id>",
    methods=["DELETE"],
)
@jwt_required()
def delete_product(
    product_id,
):
    user = get_current_user()

    if not user:
        return jsonify({
            "message": (
                "Invalid user"
            )
        }), 401

    (
        product,
        error_response,
    ) = get_owned_product(
        product_id,
        user,
    )

    if error_response:
        return error_response

    old_image_urls = list(
        product.image_urls
        or []
    )

    if (
        not old_image_urls
        and product.image_url
    ):
        old_image_urls = [
            product.image_url
        ]

    try:
        db.session.delete(
            product
        )

        db.session.commit()

        for image_url in old_image_urls:
            delete_local_product_image(
                image_url
            )

        return jsonify({
            "message": (
                "Product deleted"
            )
        }), 200

    except Exception as error:
        db.session.rollback()

        return (
            server_error_response(
                "Failed to "
                "delete product",
                error,
            )
        )


@products_bp.route(
    "/<product_id>/image",
    methods=["POST"],
)
@jwt_required()
def upload_product_image(
    product_id,
):
    user = get_current_user()

    if not user:
        return jsonify({
            "message": (
                "Invalid user"
            )
        }), 401

    (
        product,
        error_response,
    ) = get_owned_product(
        product_id,
        user,
    )

    if error_response:
        return error_response

    uploaded_file = (
        request.files.get(
            "image"
        )
    )

    if not uploaded_file:
        return jsonify({
            "message": (
                "Image is required"
            )
        }), 400

    raw_bytes = (
        uploaded_file.read(
            MAX_PRODUCT_IMAGE_BYTES
            + 1
        )
    )

    if not raw_bytes:
        return jsonify({
            "message": (
                "Image is empty"
            )
        }), 400

    if (
        len(raw_bytes)
        > MAX_PRODUCT_IMAGE_BYTES
    ):
        return jsonify({
            "message": (
                "Product image must "
                "be 8 MB or smaller"
            )
        }), 413

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

        image = (
            ImageOps
            .exif_transpose(
                image
            )
        )

        image.thumbnail(
            (
                MAX_PRODUCT_IMAGE_DIMENSION,
                MAX_PRODUCT_IMAGE_DIMENSION,
            )
        )

        if image.mode not in (
            "RGB",
            "L",
        ):
            background = (
                Image.new(
                    "RGB",
                    image.size,
                    "white",
                )
            )

            if image.mode in (
                "RGBA",
                "LA",
            ):
                alpha = (
                    image.getchannel(
                        "A"
                    )
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

    except (
        UnidentifiedImageError,
        OSError,
        ValueError,
    ):
        return jsonify({
            "message": (
                "Invalid image file"
            )
        }), 400

    current_images = list(
        product.image_urls
        or []
    )

    if (
        not current_images
        and product.image_url
    ):
        current_images.append(
            product.image_url
        )

    if len(current_images) >= 5:
        return jsonify({
            "message": (
                "A product can have "
                "at most 5 images"
            )
        }), 400

    filename = (
        f"{uuid4().hex}.jpg"
    )

    output_path = (
        get_product_image_directory()
        / filename
    )

    try:
        image.save(
            output_path,
            format="JPEG",
            quality=88,
            optimize=True,
        )

        new_image_url = (
            PRODUCT_IMAGE_URL_PREFIX
            + filename
        )

        current_images.append(
            new_image_url
        )

        product.image_urls = (
            current_images
        )

        # Keep the first image as the
        # product cover for old clients.
        product.image_url = (
            current_images[0]
        )

        db.session.commit()

        return jsonify({
            "message": (
                "Product image uploaded"
            ),

            "product": (
                serialize_product(
                    product,
                    current_user_id=(
                        user.id
                    ),
                )
            ),
        }), 200

    except Exception as error:
        db.session.rollback()

        try:
            output_path.unlink(
                missing_ok=True
            )

        except OSError:
            pass

        return (
            server_error_response(
                "Failed to upload "
                "product image",
                error,
            )
        )


@products_bp.route(
    "/<product_id>/image",
    methods=["DELETE"],
)
@jwt_required()
def delete_product_image(
    product_id,
):
    user = get_current_user()

    if not user:
        return jsonify({
            "message": (
                "Invalid user"
            )
        }), 401

    (
        product,
        error_response,
    ) = get_owned_product(
        product_id,
        user,
    )

    if error_response:
        return error_response

    current_images = list(
        product.image_urls
        or []
    )

    if (
        not current_images
        and product.image_url
    ):
        current_images.append(
            product.image_url
        )

    if not current_images:
        return jsonify({
            "message": (
                "Product has no image"
            ),

            "product": (
                serialize_product(
                    product,
                    current_user_id=(
                        user.id
                    ),
                )
            ),
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

    # Backward compatibility:
    # old clients that don't send an
    # image URL delete the first image.
    if not image_url:
        image_url = (
            current_images[0]
        )

    if image_url not in current_images:
        return jsonify({
            "message": (
                "Product image not found"
            )
        }), 404

    updated_images = [
        url
        for url in current_images
        if url != image_url
    ]

    try:
        product.image_urls = (
            updated_images
        )

        product.image_url = (
            updated_images[0]
            if updated_images
            else None
        )

        db.session.commit()

        delete_local_product_image(
            image_url
        )

        return jsonify({
            "message": (
                "Product image deleted"
            ),

            "product": (
                serialize_product(
                    product,
                    current_user_id=(
                        user.id
                    ),
                )
            ),
        }), 200

    except Exception as error:
        db.session.rollback()

        return (
            server_error_response(
                "Failed to delete "
                "product image",
                error,
            )
        )


@products_bp.route(
    "/images/<filename>",
    methods=["GET"],
)
def serve_product_image(
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

    return send_from_directory(
        get_product_image_directory(),
        filename,
    )