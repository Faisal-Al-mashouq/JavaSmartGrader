from datetime import datetime
import enum
from typing import Optional
from .base import Base
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import JSON, Boolean, DateTime, String, ForeignKey, Integer, Numeric, Text, UniqueConstraint
from sqlalchemy.types import Enum as SAEnum


class UserRole(str, enum.Enum):
    student = "student"
    instructor = "instructor"

class SubmissionState(str, enum.Enum):
    submitted = "submitted"
    processing = "processing"
    graded = "graded"
    failed = "failed"


class User(Base):
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    role: Mapped[UserRole] = mapped_column(SAEnum(UserRole), name="user_role", nullable=False)
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

    suggested_grade: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    feedback_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    rubric_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    instructor: Mapped["User"] = relationship(
        back_populates="assignments",
        foreign_keys=[instructor_id],
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
    assignment_id: Mapped[int] = mapped_column(ForeignKey("assignments.id"), nullable=False)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)

    image_url: Mapped[Optional[str]] = mapped_column(String(2048), nullable=True)
    state: Mapped[SubmissionState] = mapped_column(
        SAEnum(SubmissionState, name="submission_state"),
        nullable=False,
        default=SubmissionState.submitted,
    )
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.now(),
    )

    assignment: Mapped["Assignment"] = relationship(back_populates="submissions")
    student: Mapped["User"] = relationship(
        back_populates="submissions",
        foreign_keys=[student_id],
    )

    testcases: Mapped[list["Testcase"]] = relationship(
        back_populates="submission",
        cascade="all, delete-orphan",
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
        return f"Submission(id={self.id}, assignment_id={self.assignment_id}, student_id={self.student_id}, state='{self.state}')"


class Testcase(Base):
    __tablename__ = "testcases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    submission_id: Mapped[int] = mapped_column(ForeignKey("submissions.id"), nullable=False)

    input: Mapped[str] = mapped_column(Text, nullable=False)
    suggested_output: Mapped[str] = mapped_column(Text, nullable=False)

    submission: Mapped["Submission"] = relationship(back_populates="testcases")


class AIFeedback(Base):
    __tablename__ = "ai_feedback"
    __table_args__ = (UniqueConstraint("submission_id", name="ai_feedback_submission_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    submission_id: Mapped[int] = mapped_column(ForeignKey("submissions.id"), nullable=False)

    suggested_grade: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    feedback_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    submission: Mapped["Submission"] = relationship(back_populates="ai_feedback")


class CompileResult(Base):
    __tablename__ = "compile_results"
    __table_args__ = (UniqueConstraint("submission_id", name="compile_results_submission_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    submission_id: Mapped[int] = mapped_column(ForeignKey("submissions.id"), nullable=False)

    compiled_ok: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    compile_errors: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    runtime_output: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    submission: Mapped["Submission"] = relationship(back_populates="compile_results")


class Transcription(Base):
    __tablename__ = "transcriptions"
    __table_args__ = (UniqueConstraint("submission_id", name="transcriptions_submission_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    submission_id: Mapped[int] = mapped_column(ForeignKey("submissions.id"), nullable=False)

    feedback_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    submission: Mapped["Submission"] = relationship(back_populates="transcription")


class Grade(Base):
    __tablename__ = "grades"
    __table_args__ = (UniqueConstraint("submission_id", name="grades_submission_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    submission_id: Mapped[int] = mapped_column(ForeignKey("submissions.id"), nullable=False)
    instructor_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)

    final_grade: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    submission: Mapped["Submission"] = relationship(back_populates="grade")
    instructor: Mapped["User"] = relationship(
        back_populates="grades_given",
        foreign_keys=[instructor_id],
    )