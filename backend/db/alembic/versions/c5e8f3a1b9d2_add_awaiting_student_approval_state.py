"""add awaiting_student_approval to submission_state enum

Revision ID: c5e8f3a1b9d2
Revises: a3f8e1c2d4b6
Create Date: 2026-04-20 12:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

revision: str = "c5e8f3a1b9d2"
down_revision: str | Sequence[str] | None = "a3f8e1c2d4b6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TYPE submission_state ADD VALUE IF NOT EXISTS 'awaiting_student_approval'")


def downgrade() -> None:
    # Postgres doesn't support removing a single enum value safely without
    # rewriting the type. Any rows currently in the new state would need to
    # be migrated off it first, so downgrade is a no-op.
    pass
