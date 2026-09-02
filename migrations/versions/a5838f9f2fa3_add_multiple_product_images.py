"""add multiple product images

Revision ID: a5838f9f2fa3
Revises: 6597ceb7afac
Create Date: 2026-09-02 17:23:47.045115
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = 'a5838f9f2fa3'
down_revision = '6597ceb7afac'
branch_labels = None
depends_on = None


def upgrade():
    # Add the new JSONB column first.
    with op.batch_alter_table(
        'products',
        schema=None,
    ) as batch_op:
        batch_op.add_column(
            sa.Column(
                'image_urls',
                postgresql.JSONB(
                    astext_type=sa.Text(),
                ),
                server_default='[]',
                nullable=False,
            )
        )

    # After the column exists, migrate old
    # single-image data into the array.
    op.execute("""
        UPDATE products
        SET image_urls =
            CASE
                WHEN image_url IS NOT NULL
                THEN jsonb_build_array(image_url)
                ELSE '[]'::jsonb
            END
    """)


def downgrade():
    with op.batch_alter_table(
        'products',
        schema=None,
    ) as batch_op:
        batch_op.drop_column(
            'image_urls'
        )