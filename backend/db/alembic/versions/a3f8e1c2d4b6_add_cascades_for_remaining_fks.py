"""add cascades for remaining foreign keys

Revision ID: a3f8e1c2d4b6
Revises: b1d4c7e9a2f0
Create Date: 2026-04-04 12:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a3f8e1c2d4b6"
down_revision: str | Sequence[str] | None = "b1d4c7e9a2f0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add ON DELETE CASCADE / RESTRICT to remaining FK constraints."""

    # --- CASCADE: structural parent-child relationships ---

    # questions.assignment_id -> assignments.id
    op.execute("""
        ALTER TABLE questions
        DROP CONSTRAINT IF EXISTS questions_assignment_id_fkey,
        ADD CONSTRAINT questions_assignment_id_fkey
            FOREIGN KEY (assignment_id)
            REFERENCES assignments(id)
            ON DELETE CASCADE
    """)

    # testcases.(question_id, assignment_id) -> questions(id, assignment_id)
    op.execute("""
        ALTER TABLE testcases
        DROP CONSTRAINT IF EXISTS fk_testcases_question_id_assignment_id,
        ADD CONSTRAINT fk_testcases_question_id_assignment_id
            FOREIGN KEY (question_id, assignment_id)
            REFERENCES questions(id, assignment_id)
            ON DELETE CASCADE
    """)

    # submissions.(question_id, assignment_id) -> questions(id, assignment_id)
    op.execute("""
        ALTER TABLE submissions
        DROP CONSTRAINT IF EXISTS fk_submissions_question_id_assignment_id,
        ADD CONSTRAINT fk_submissions_question_id_assignment_id
            FOREIGN KEY (question_id, assignment_id)
            REFERENCES questions(id, assignment_id)
            ON DELETE CASCADE
    """)

    # assignments.course_id -> courses.id
    op.execute("""
        ALTER TABLE assignments
        DROP CONSTRAINT IF EXISTS assignments_course_id_fkey,
        ADD CONSTRAINT assignments_course_id_fkey
            FOREIGN KEY (course_id)
            REFERENCES courses(id)
            ON DELETE CASCADE
    """)

    # course_students.course_id -> courses.id
    op.execute("""
        ALTER TABLE course_students
        DROP CONSTRAINT IF EXISTS course_students_course_id_fkey,
        ADD CONSTRAINT course_students_course_id_fkey
            FOREIGN KEY (course_id)
            REFERENCES courses(id)
            ON DELETE CASCADE
    """)

    # course_students.student_id -> users.id
    op.execute("""
        ALTER TABLE course_students
        DROP CONSTRAINT IF EXISTS course_students_student_id_fkey,
        ADD CONSTRAINT course_students_student_id_fkey
            FOREIGN KEY (student_id)
            REFERENCES users(id)
            ON DELETE CASCADE
    """)

    # generate_reports.assignment_id -> assignments.id
    op.execute("""
        ALTER TABLE generate_reports
        DROP CONSTRAINT IF EXISTS generate_reports_assignment_id_fkey,
        ADD CONSTRAINT generate_reports_assignment_id_fkey
            FOREIGN KEY (assignment_id)
            REFERENCES assignments(id)
            ON DELETE CASCADE
    """)

    # --- RESTRICT: user-owned data (block delete if children exist) ---

    # courses.instructor_id -> users.id
    op.execute("""
        ALTER TABLE courses
        DROP CONSTRAINT IF EXISTS courses_instructor_id_fkey,
        ADD CONSTRAINT courses_instructor_id_fkey
            FOREIGN KEY (instructor_id)
            REFERENCES users(id)
            ON DELETE RESTRICT
    """)

    # submissions.student_id -> users.id
    op.execute("""
        ALTER TABLE submissions
        DROP CONSTRAINT IF EXISTS submissions_student_id_fkey,
        ADD CONSTRAINT submissions_student_id_fkey
            FOREIGN KEY (student_id)
            REFERENCES users(id)
            ON DELETE RESTRICT
    """)

    # grades.instructor_id -> users.id
    op.execute("""
        ALTER TABLE grades
        DROP CONSTRAINT IF EXISTS grades_instructor_id_fkey,
        ADD CONSTRAINT grades_instructor_id_fkey
            FOREIGN KEY (instructor_id)
            REFERENCES users(id)
            ON DELETE RESTRICT
    """)


def downgrade() -> None:
    """Remove ON DELETE clauses, reverting to default (NO ACTION)."""

    # --- Revert CASCADE constraints ---

    op.execute("""
        ALTER TABLE questions
        DROP CONSTRAINT IF EXISTS questions_assignment_id_fkey,
        ADD CONSTRAINT questions_assignment_id_fkey
            FOREIGN KEY (assignment_id)
            REFERENCES assignments(id)
    """)

    op.execute("""
        ALTER TABLE testcases
        DROP CONSTRAINT IF EXISTS fk_testcases_question_id_assignment_id,
        ADD CONSTRAINT fk_testcases_question_id_assignment_id
            FOREIGN KEY (question_id, assignment_id)
            REFERENCES questions(id, assignment_id)
    """)

    op.execute("""
        ALTER TABLE submissions
        DROP CONSTRAINT IF EXISTS fk_submissions_question_id_assignment_id,
        ADD CONSTRAINT fk_submissions_question_id_assignment_id
            FOREIGN KEY (question_id, assignment_id)
            REFERENCES questions(id, assignment_id)
    """)

    op.execute("""
        ALTER TABLE assignments
        DROP CONSTRAINT IF EXISTS assignments_course_id_fkey,
        ADD CONSTRAINT assignments_course_id_fkey
            FOREIGN KEY (course_id)
            REFERENCES courses(id)
    """)

    op.execute("""
        ALTER TABLE course_students
        DROP CONSTRAINT IF EXISTS course_students_course_id_fkey,
        ADD CONSTRAINT course_students_course_id_fkey
            FOREIGN KEY (course_id)
            REFERENCES courses(id)
    """)

    op.execute("""
        ALTER TABLE course_students
        DROP CONSTRAINT IF EXISTS course_students_student_id_fkey,
        ADD CONSTRAINT course_students_student_id_fkey
            FOREIGN KEY (student_id)
            REFERENCES users(id)
    """)

    op.execute("""
        ALTER TABLE generate_reports
        DROP CONSTRAINT IF EXISTS generate_reports_assignment_id_fkey,
        ADD CONSTRAINT generate_reports_assignment_id_fkey
            FOREIGN KEY (assignment_id)
            REFERENCES assignments(id)
    """)

    # --- Revert RESTRICT constraints ---

    op.execute("""
        ALTER TABLE courses
        DROP CONSTRAINT IF EXISTS courses_instructor_id_fkey,
        ADD CONSTRAINT courses_instructor_id_fkey
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
        ALTER TABLE grades
        DROP CONSTRAINT IF EXISTS grades_instructor_id_fkey,
        ADD CONSTRAINT grades_instructor_id_fkey
            FOREIGN KEY (instructor_id)
            REFERENCES users(id)
    """)
