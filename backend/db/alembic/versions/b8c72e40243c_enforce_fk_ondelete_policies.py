"""enforce_fk_ondelete_policies

Revision ID: b8c72e40243c
Revises: d2540b3257a7
Create Date: 2026-04-08 10:36:27.343392

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b8c72e40243c"
down_revision: str | Sequence[str] | None = "d2540b3257a7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Align live DB foreign keys with model intent (and avoid autogenerate churn).
    #
    # CASCADE: structural parent-child relationships
    op.execute("""
        ALTER TABLE questions
        DROP CONSTRAINT IF EXISTS questions_assignment_id_fkey,
        ADD CONSTRAINT questions_assignment_id_fkey
            FOREIGN KEY (assignment_id)
            REFERENCES assignments(id)
            ON DELETE CASCADE
        """)
    op.execute("""
        ALTER TABLE testcases
        DROP CONSTRAINT IF EXISTS fk_testcases_question_id_assignment_id,
        ADD CONSTRAINT fk_testcases_question_id_assignment_id
            FOREIGN KEY (question_id, assignment_id)
            REFERENCES questions(id, assignment_id)
            ON DELETE CASCADE
        """)
    op.execute("""
        ALTER TABLE submissions
        DROP CONSTRAINT IF EXISTS fk_submissions_question_id_assignment_id,
        ADD CONSTRAINT fk_submissions_question_id_assignment_id
            FOREIGN KEY (question_id, assignment_id)
            REFERENCES questions(id, assignment_id)
            ON DELETE CASCADE
        """)
    op.execute("""
        ALTER TABLE assignments
        DROP CONSTRAINT IF EXISTS assignments_course_id_fkey,
        ADD CONSTRAINT assignments_course_id_fkey
            FOREIGN KEY (course_id)
            REFERENCES courses(id)
            ON DELETE CASCADE
        """)
    op.execute("""
        ALTER TABLE course_students
        DROP CONSTRAINT IF EXISTS course_students_course_id_fkey,
        ADD CONSTRAINT course_students_course_id_fkey
            FOREIGN KEY (course_id)
            REFERENCES courses(id)
            ON DELETE CASCADE
        """)
    op.execute("""
        ALTER TABLE course_students
        DROP CONSTRAINT IF EXISTS course_students_student_id_fkey,
        ADD CONSTRAINT course_students_student_id_fkey
            FOREIGN KEY (student_id)
            REFERENCES users(id)
            ON DELETE CASCADE
        """)
    op.execute("""
        ALTER TABLE generate_reports
        DROP CONSTRAINT IF EXISTS generate_reports_assignment_id_fkey,
        ADD CONSTRAINT generate_reports_assignment_id_fkey
            FOREIGN KEY (assignment_id)
            REFERENCES assignments(id)
            ON DELETE CASCADE
        """)

    # RESTRICT: user-owned data (block delete if children exist)
    op.execute("""
        ALTER TABLE courses
        DROP CONSTRAINT IF EXISTS courses_instructor_id_fkey,
        ADD CONSTRAINT courses_instructor_id_fkey
            FOREIGN KEY (instructor_id)
            REFERENCES users(id)
            ON DELETE RESTRICT
        """)
    op.execute("""
        ALTER TABLE submissions
        DROP CONSTRAINT IF EXISTS submissions_student_id_fkey,
        ADD CONSTRAINT submissions_student_id_fkey
            FOREIGN KEY (student_id)
            REFERENCES users(id)
            ON DELETE RESTRICT
        """)
    op.execute("""
        ALTER TABLE grades
        DROP CONSTRAINT IF EXISTS grades_instructor_id_fkey,
        ADD CONSTRAINT grades_instructor_id_fkey
            FOREIGN KEY (instructor_id)
            REFERENCES users(id)
            ON DELETE RESTRICT
        """)


def downgrade() -> None:
    """Downgrade schema."""
    # Revert to default (NO ACTION) behavior.
    op.execute("""
        ALTER TABLE grades
        DROP CONSTRAINT IF EXISTS grades_instructor_id_fkey,
        ADD CONSTRAINT grades_instructor_id_fkey
            FOREIGN KEY (instructor_id)
            REFERENCES users(id)
        """)
    op.execute("""
        ALTER TABLE submissions
        DROP CONSTRAINT IF EXISTS submissions_student_id_fkey,
        ADD CONSTRAINT submissions_student_id_fkey
            FOREIGN KEY (student_id)
            REFERENCES users(id)
        """)
    op.execute("""
        ALTER TABLE courses
        DROP CONSTRAINT IF EXISTS courses_instructor_id_fkey,
        ADD CONSTRAINT courses_instructor_id_fkey
            FOREIGN KEY (instructor_id)
            REFERENCES users(id)
        """)

    op.execute("""
        ALTER TABLE generate_reports
        DROP CONSTRAINT IF EXISTS generate_reports_assignment_id_fkey,
        ADD CONSTRAINT generate_reports_assignment_id_fkey
            FOREIGN KEY (assignment_id)
            REFERENCES assignments(id)
        """)
    op.execute("""
        ALTER TABLE course_students
        DROP CONSTRAINT IF EXISTS course_students_student_id_fkey,
        ADD CONSTRAINT course_students_student_id_fkey
            FOREIGN KEY (student_id)
            REFERENCES users(id)
        """)
    op.execute("""
        ALTER TABLE course_students
        DROP CONSTRAINT IF EXISTS course_students_course_id_fkey,
        ADD CONSTRAINT course_students_course_id_fkey
            FOREIGN KEY (course_id)
            REFERENCES courses(id)
        """)
    op.execute("""
        ALTER TABLE assignments
        DROP CONSTRAINT IF EXISTS assignments_course_id_fkey,
        ADD CONSTRAINT assignments_course_id_fkey
            FOREIGN KEY (course_id)
            REFERENCES courses(id)
        """)
    op.execute("""
        ALTER TABLE submissions
        DROP CONSTRAINT IF EXISTS fk_submissions_question_id_assignment_id,
        ADD CONSTRAINT fk_submissions_question_id_assignment_id
            FOREIGN KEY (question_id, assignment_id)
            REFERENCES questions(id, assignment_id)
        """)
    op.execute("""
        ALTER TABLE testcases
        DROP CONSTRAINT IF EXISTS fk_testcases_question_id_assignment_id,
        ADD CONSTRAINT fk_testcases_question_id_assignment_id
            FOREIGN KEY (question_id, assignment_id)
            REFERENCES questions(id, assignment_id)
        """)
    op.execute("""
        ALTER TABLE questions
        DROP CONSTRAINT IF EXISTS questions_assignment_id_fkey,
        ADD CONSTRAINT questions_assignment_id_fkey
            FOREIGN KEY (assignment_id)
            REFERENCES assignments(id)
        """)
