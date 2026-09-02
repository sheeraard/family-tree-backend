"""add products

Revision ID: c91a7f4d0e21
Revises: 809bf6b7e406
"""

from alembic import op
import sqlalchemy as sa

from sqlalchemy.dialects import (
    postgresql,
)


revision = (
    "c91a7f4d0e21"
)

down_revision = (
    "809bf6b7e406"
)

branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "products",

        sa.Column(
            "id",
            postgresql.UUID(
                as_uuid=True
            ),
            nullable=False,
        ),

        sa.Column(
            "seller_user_id",
            postgresql.UUID(
                as_uuid=True
            ),
            nullable=False,
        ),

        sa.Column(
            "name",
            sa.String(
                length=160
            ),
            nullable=False,
        ),

        sa.Column(
            "description",
            sa.Text(),
            nullable=True,
        ),

        sa.Column(
            "price",
            sa.BigInteger(),
            nullable=False,
        ),

        sa.Column(
            "category",
            sa.String(
                length=80
            ),
            nullable=True,
        ),

        sa.Column(
            "contact",
            sa.String(
                length=255
            ),
            nullable=True,
        ),

        sa.Column(
            "image_url",
            sa.Text(),
            nullable=True,
        ),

        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=(
                sa.text(
                    "true"
                )
            ),
            nullable=False,
        ),

        sa.Column(
            "created_at",
            sa.DateTime(
                timezone=True
            ),
            server_default=(
                sa.text(
                    "now()"
                )
            ),
            nullable=False,
        ),

        sa.Column(
            "updated_at",
            sa.DateTime(
                timezone=True
            ),
            server_default=(
                sa.text(
                    "now()"
                )
            ),
            nullable=False,
        ),

        sa.ForeignKeyConstraint(
            [
                "seller_user_id"
            ],
            [
                "users.id"
            ],
            ondelete="CASCADE",
        ),

        sa.PrimaryKeyConstraint(
            "id"
        ),
    )

    op.create_index(
        op.f(
            "ix_products_category"
        ),
        "products",
        [
            "category"
        ],
        unique=False,
    )

    op.create_index(
        op.f(
            "ix_products_is_active"
        ),
        "products",
        [
            "is_active"
        ],
        unique=False,
    )

    op.create_index(
        op.f(
            "ix_products_name"
        ),
        "products",
        [
            "name"
        ],
        unique=False,
    )

    op.create_index(
        op.f(
            "ix_products_seller_user_id"
        ),
        "products",
        [
            "seller_user_id"
        ],
        unique=False,
    )


def downgrade():
    op.drop_index(
        op.f(
            "ix_products_seller_user_id"
        ),
        table_name="products",
    )

    op.drop_index(
        op.f(
            "ix_products_name"
        ),
        table_name="products",
    )

    op.drop_index(
        op.f(
            "ix_products_is_active"
        ),
        table_name="products",
    )

    op.drop_index(
        op.f(
            "ix_products_category"
        ),
        table_name="products",
    )

    op.drop_table(
        "products"
    )