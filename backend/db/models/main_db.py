import enum
from datetime import UTC, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    Numeric,
    String,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Enum as SAEnum

from .base import Base


class UserRole(enum.Enum):
    student = "student"
    instructor = "instructor"


class SubmissionState(enum.Enum):
    submitted = "submitted"
    processing = "processing"
    graded = "graded"
    failed = "failed"


course_students = Table(
    "course_students",
    Base.metadata,
    Column("course_id", ForeignKey("courses.id"), primary_key=True),
    Column("student_id", ForeignKey("users.id"), primary_key=True),
)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    role: Mapped[UserRole] = mapped_column(
        SAEnum(UserRole), name="user_role", nullable=False
    )
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    courses: Mapped[list["Course"]] = relationship(
        back_populates="instructor",
        foreign_keys="[Course.instructor_id]",
        cascade="all, delete-orphan",
    )
    enrolled_courses: Mapped[list["Course"]] = relationship(
        secondary=course_students,
        back_populates="students",
    )
    grades_given: Mapped[list["Grade"]] = relationship(
        back_populates="instructor",
        foreign_keys="Grade.instructor_id",
        cascade="all, delete-orphan",
    )
    submissions: Mapped[list["Submission"]] = relationship(
        back_populates="student",
        foreign_keys="Submission.student_id",
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"User(id={self.id}, username='{self.username}', role='{self.role}')"


class Course(Base):
    __tablename__ = "courses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    instructor_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)

    instructor: Mapped["User"] = relationship(
        back_populates="courses",
        foreign_keys=[instructor_id],
    )
    students: Mapped[list["User"]] = relationship(
        secondary=course_students,
        back_populates="enrolled_courses",
    )
    assignments: Mapped[list["Assignment"]] = relationship(
        back_populates="course",
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return (
            f"Course(id={self.id}, name='{self.name}',"
            " instructor_id={self.instructor_id})"
        )


class Assignment(Base):
    __tablename__ = "assignments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    due_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    rubric_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    course: Mapped["Course"] = relationship(
        back_populates="assignments",
        foreign_keys=[course_id],
    )
    questions: Mapped[list["Question"]] = relationship(
        back_populates="assignment",
        cascade="all, delete-orphan",
    )
    generate_reports: Mapped[list["GenerateReport"]] = relationship(
        back_populates="assignment",
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return (
            f"Assignment(id={self.id}, course_id={self.course_id},"
            " title='{self.title}')"
        )


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    assignment_id: Mapped[int] = mapped_column(
        ForeignKey("assignments.id"), nullable=False, primary_key=True
    )
    question_text: Mapped[str] = mapped_column(Text, nullable=False)

    assignment: Mapped["Assignment"] = relationship(back_populates="questions")
    submissions: Mapped[list["Submission"]] = relationship(
        back_populates="question",
        cascade="all, delete-orphan",
    )
    testcases: Mapped[list["Testcase"]] = relationship(
        back_populates="question",
        cascade="all, delete-orphan",
    )


class Submission(Base):
    __tablename__ = "submissions"
    __table_args__ = (
        ForeignKeyConstraint(
            ["question_id", "assignment_id"],
            ["questions.id", "questions.assignment_id"],
            name="fk_submissions_question_id_assignment_id",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    question_id: Mapped[int] = mapped_column(nullable=False)
    assignment_id: Mapped[int] = mapped_column(nullable=False)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)

    image_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    state: Mapped[SubmissionState] = mapped_column(
        SAEnum(SubmissionState, name="submission_state"),
        nullable=False,
        default=SubmissionState.submitted,
    )
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )

    question: Mapped["Question"] = relationship(back_populates="submissions")
    student: Mapped["User"] = relationship(
        back_populates="submissions",
        foreign_keys=[student_id],
    )
    ai_feedback: Mapped[Optional["AIFeedback"]] = relationship(
        back_populates="submission",
        uselist=False,
        cascade="all, delete-orphan",
    )
    compile_results: Mapped[Optional["CompileResult"]] = relationship(
        back_populates="submission",
        uselist=False,
        cascade="all, delete-orphan",
    )
    transcription: Mapped[Optional["Transcription"]] = relationship(
        back_populates="submission",
        uselist=False,
        cascade="all, delete-orphan",
    )
    grade: Mapped[Optional["Grade"]] = relationship(
        back_populates="submission",
        uselist=False,
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return (
            f"Submission(id={self.id}, question_id={self.question_id}"
            f", student_id={self.student_id}, state='{self.state}')"
        )


class Testcase(Base):
    __tablename__ = "testcases"
    __table_args__ = (
        ForeignKeyConstraint(
            ["question_id", "assignment_id"],
            ["questions.id", "questions.assignment_id"],
            name="fk_testcases_question_id_assignment_id",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    question_id: Mapped[int] = mapped_column(nullable=False)
    assignment_id: Mapped[int] = mapped_column(nullable=False)

    input: Mapped[str] = mapped_column(Text, nullable=False)
    expected_output: Mapped[str] = mapped_column(Text, nullable=False)

    question: Mapped["Question"] = relationship(back_populates="testcases")


class AIFeedback(Base):
    __tablename__ = "ai_feedback"
    __table_args__ = (
        UniqueConstraint("submission_id", name="ai_feedback_submission_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    submission_id: Mapped[int] = mapped_column(
        ForeignKey("submissions.id"), nullable=False
    )

    suggested_grade: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2), nullable=True
    )
    instructor_guidance: Mapped[str | None] = mapped_column(Text, nullable=True)
    student_feedback: Mapped[str | None] = mapped_column(Text, nullable=True)

    submission: Mapped["Submission"] = relationship(back_populates="ai_feedback")


class CompileResult(Base):
    __tablename__ = "compile_results"
    __table_args__ = (
        UniqueConstraint("submission_id", name="compile_results_submission_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    submission_id: Mapped[int] = mapped_column(
        ForeignKey("submissions.id"), nullable=False
    )

    compiled_ok: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    compile_errors: Mapped[str | None] = mapped_column(Text, nullable=True)
    runtime_errors: Mapped[str | None] = mapped_column(Text, nullable=True)
    runtime_outputs: Mapped[str | None] = mapped_column(Text, nullable=True)

    submission: Mapped["Submission"] = relationship(back_populates="compile_results")


class Transcription(Base):
    __tablename__ = "transcriptions"
    __table_args__ = (
        UniqueConstraint("submission_id", name="transcriptions_submission_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    submission_id: Mapped[int] = mapped_column(
        ForeignKey("submissions.id"), nullable=False
    )

    transcribed_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    submission: Mapped["Submission"] = relationship(back_populates="transcription")
    confidence_flags: Mapped[list["ConfidenceFlag"]] = relationship(
        back_populates="transcription",
        cascade="all, delete-orphan",
    )


class ConfidenceFlag(Base):
    __tablename__ = "confidence_flags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    transcription_id: Mapped[int] = mapped_column(
        ForeignKey("transcriptions.id"), nullable=False
    )
    text_segment: Mapped[str] = mapped_column(Text, nullable=False)
    confidence_score: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    coordinates: Mapped[str | None] = mapped_column(Text, nullable=True)
    suggestions: Mapped[str | None] = mapped_column(Text, nullable=True)

    transcription: Mapped["Transcription"] = relationship(
        back_populates="confidence_flags"
    )


class Grade(Base):
    __tablename__ = "grades"
    __table_args__ = (UniqueConstraint("submission_id", name="grades_submission_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    submission_id: Mapped[int] = mapped_column(
        ForeignKey("submissions.id"), nullable=False
    )
    instructor_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)

    final_grade: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def __repr__(self):
        return (
            f"Grade(id={self.id}, submission_id={self.submission_id},"
            " final_grade={self.final_grade})"
        )

    submission: Mapped["Submission"] = relationship(back_populates="grade")
    instructor: Mapped["User"] = relationship(
        back_populates="grades_given",
        foreign_keys=[instructor_id],
    )


class GenerateReport(Base):
    __tablename__ = "generate_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    assignment_id: Mapped[int] = mapped_column(
        ForeignKey("assignments.id"), nullable=False
    )
    report_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    assignment: Mapped["Assignment"] = relationship(back_populates="generate_reports")
