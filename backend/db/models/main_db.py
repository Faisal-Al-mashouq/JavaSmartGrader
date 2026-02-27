import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
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


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    role: Mapped[UserRole] = mapped_column(
        SAEnum(UserRole), name="user_role", nullable=False
    )
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    assignments: Mapped[list["Assignment"]] = relationship(
        back_populates="instructor",
        foreign_keys="Assignment.instructor_id",
        cascade="all, delete-orphan",
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


class Assignment(Base):
    __tablename__ = "assignments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    instructor_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    due_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    suggested_grade: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    feedback_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    rubric_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    instructor: Mapped["User"] = relationship(
        back_populates="assignments",
        foreign_keys=[instructor_id],
    )

    testcases: Mapped[list["Testcase"]] = relationship(
        back_populates="assignment",
        cascade="all, delete-orphan",
    )

    submissions: Mapped[list["Submission"]] = relationship(
        back_populates="assignment",
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"Assignment(id={self.id}, instructor_id={self.instructor_id})"


class Submission(Base):
    __tablename__ = "submissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    assignment_id: Mapped[int] = mapped_column(
        ForeignKey("assignments.id"), nullable=False
    )
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
        default=datetime.now,
    )

    assignment: Mapped["Assignment"] = relationship(back_populates="submissions")
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
            f"Submission(id={self.id}, assignment_id={self.assignment_id},"
            f"student_id={self.student_id}, state='{self.state}')"
        )


class Testcase(Base):
    __tablename__ = "testcases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    assignment_id: Mapped[int] = mapped_column(
        ForeignKey("assignments.id"), nullable=False
    )

    input: Mapped[str] = mapped_column(Text, nullable=False)
    expected_output: Mapped[str] = mapped_column(Text, nullable=False)

    assignment: Mapped["Assignment"] = relationship(back_populates="testcases")


class AIFeedback(Base):
    __tablename__ = "ai_feedback"
    __table_args__ = (
        UniqueConstraint("submission_id", name="ai_feedback_submission_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    submission_id: Mapped[int] = mapped_column(
        ForeignKey("submissions.id"), nullable=False
    )

    suggested_grade: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    feedback_text: Mapped[str | None] = mapped_column(Text, nullable=True)

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
    runtime_output: Mapped[str | None] = mapped_column(Text, nullable=True)

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

    feedback_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    submission: Mapped["Submission"] = relationship(back_populates="transcription")


class Grade(Base):
    __tablename__ = "grades"
    __table_args__ = (UniqueConstraint("submission_id", name="grades_submission_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    submission_id: Mapped[int] = mapped_column(
        ForeignKey("submissions.id"), nullable=False
    )
    instructor_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)

    final_grade: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    submission: Mapped["Submission"] = relationship(back_populates="grade")
    instructor: Mapped["User"] = relationship(
        back_populates="grades_given",
        foreign_keys=[instructor_id],
    )
