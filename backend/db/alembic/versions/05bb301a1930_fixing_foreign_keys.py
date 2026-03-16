"""fixing foreign keys

Revision ID: 05bb301a1930
Revises: 484284b2c0ac
Create Date: 2026-03-02 06:27:51.434798

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "05bb301a1930"
down_revision: str | Sequence[str] | None = "484284b2c0ac"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("CREATE SEQUENCE IF NOT EXISTS questions_id_seq")
    op.execute("ALTER SEQUENCE questions_id_seq OWNED BY questions.id")
    op.execute(
        "ALTER TABLE questions ALTER COLUMN id SET DEFAULT nextval('questions_id_seq')"
    )
    op.execute(
        "SELECT setval('questions_id_seq',"
        " COALESCE((SELECT MAX(id) FROM questions), 1))"
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("ALTER TABLE questions ALTER COLUMN id DROP DEFAULT")
    op.execute("DROP SEQUENCE IF EXISTS questions_id_seq")
