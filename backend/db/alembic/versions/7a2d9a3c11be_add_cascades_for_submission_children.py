"""add cascades for submission child tables

Revision ID: 7a2d9a3c11be
Revises: 05bb301a1930
Create Date: 2026-03-06 10:20:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7a2d9a3c11be"
down_revision: str | Sequence[str] | None = "05bb301a1930"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        """
        ALTER TABLE ai_feedback
        DROP CONSTRAINT IF EXISTS ai_feedback_submission_id_fkey,
        ADD CONSTRAINT ai_feedback_submission_id_fkey
            FOREIGN KEY (submission_id)
            REFERENCES submissions(id)
            ON DELETE CASCADE
        """
    )
    op.execute(
        """
        ALTER TABLE compile_results
        DROP CONSTRAINT IF EXISTS compile_results_submission_id_fkey,
        ADD CONSTRAINT compile_results_submission_id_fkey
            FOREIGN KEY (submission_id)
            REFERENCES submissions(id)
            ON DELETE CASCADE
        """
    )
    op.execute(
        """
        ALTER TABLE transcriptions
        DROP CONSTRAINT IF EXISTS transcriptions_submission_id_fkey,
        ADD CONSTRAINT transcriptions_submission_id_fkey
            FOREIGN KEY (submission_id)
            REFERENCES submissions(id)
            ON DELETE CASCADE
        """
    )
    op.execute(
        """
        ALTER TABLE grades
        DROP CONSTRAINT IF EXISTS grades_submission_id_fkey,
        ADD CONSTRAINT grades_submission_id_fkey
            FOREIGN KEY (submission_id)
            REFERENCES submissions(id)
            ON DELETE CASCADE
        """
    )
    op.execute(
        """
        ALTER TABLE confidence_flags
        DROP CONSTRAINT IF EXISTS confidence_flags_transcription_id_fkey,
        ADD CONSTRAINT confidence_flags_transcription_id_fkey
            FOREIGN KEY (transcription_id)
            REFERENCES transcriptions(id)
            ON DELETE CASCADE
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(
        """
        ALTER TABLE ai_feedback
        DROP CONSTRAINT IF EXISTS ai_feedback_submission_id_fkey,
        ADD CONSTRAINT ai_feedback_submission_id_fkey
            FOREIGN KEY (submission_id)
            REFERENCES submissions(id)
        """
    )
    op.execute(
        """
        ALTER TABLE compile_results
        DROP CONSTRAINT IF EXISTS compile_results_submission_id_fkey,
        ADD CONSTRAINT compile_results_submission_id_fkey
            FOREIGN KEY (submission_id)
            REFERENCES submissions(id)
        """
    )
    op.execute(
        """
        ALTER TABLE transcriptions
        DROP CONSTRAINT IF EXISTS transcriptions_submission_id_fkey,
        ADD CONSTRAINT transcriptions_submission_id_fkey
            FOREIGN KEY (submission_id)
            REFERENCES submissions(id)
        """
    )
    op.execute(
        """
        ALTER TABLE grades
        DROP CONSTRAINT IF EXISTS grades_submission_id_fkey,
        ADD CONSTRAINT grades_submission_id_fkey
            FOREIGN KEY (submission_id)
            REFERENCES submissions(id)
        """
    )
    op.execute(
        """
        ALTER TABLE confidence_flags
        DROP CONSTRAINT IF EXISTS confidence_flags_transcription_id_fkey,
        ADD CONSTRAINT confidence_flags_transcription_id_fkey
            FOREIGN KEY (transcription_id)
            REFERENCES transcriptions(id)
        """
    )
