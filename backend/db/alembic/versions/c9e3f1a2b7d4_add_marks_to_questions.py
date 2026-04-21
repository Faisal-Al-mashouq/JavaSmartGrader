"""add marks to questions

Revision ID: c9e3f1a2b7d4
Revises: b8c72e40243c
Create Date: 2026-04-21 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c9e3f1a2b7d4"
down_revision: str | Sequence[str] | None = "b8c72e40243c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "questions",
        sa.Column("marks", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("questions", "marks")
