"""set document_extractions created_at default

Revision ID: af1d6d7f3c2b
Revises: 8f4f6a3bb57d
Create Date: 2026-05-11 00:58:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "af1d6d7f3c2b"
down_revision: Union[str, Sequence[str], None] = "8f4f6a3bb57d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "document_extractions",
        "created_at",
        existing_type=sa.DateTime(),
        nullable=False,
        server_default=sa.text("CURRENT_TIMESTAMP"),
    )


def downgrade() -> None:
    op.alter_column(
        "document_extractions",
        "created_at",
        existing_type=sa.DateTime(),
        nullable=False,
        server_default=None,
    )
