from .assignments import (
    AssignmentBase,
)
from .confidence_flags import (
    ConfidenceFlagBase,
)
from .courses import (
    CourseBase,
)
from .generate_reports import (
    GenerateReportBase,
)
from .grading import (
    AIFeedbackBase,
    CompileResultBase,
    GradeBase,
    TranscriptionBase,
)
from .questions import (
    QuestionBase,
    TestcaseBase,
)
from .shared import JobStatus, TestCase
from .submissions import (
    SubmissionBase,
)
from .users import (
    LoginRequest,
    RegisterRequest,
    UserBase,
)

__all__ = [
    "AssignmentBase",
    "ConfidenceFlagBase",
    "CourseBase",
    "GenerateReportBase",
    "QuestionBase",
    "TestcaseBase",
    "LoginRequest",
    "RegisterRequest",
    "UserBase",
    "SubmissionBase",
    "TranscriptionBase",
    "CompileResultBase",
    "AIFeedbackBase",
    "GradeBase",
    "Job",
    "JobRequest",
    "JobStatus",
    "JobType",
    "OCRPayload",
    "OCRResult",
    "SandboxPayload",
    "SandboxResult",
    "GraderPayload",
    "GraderResult",
    "FinalResult",
    "TestCase",
    "JobRequestPayload",
    "JobResultPayload",
]

_JOB_ATTRS = {
    "Job",
    "JobRequest",
    "JobRequestPayload",
    "JobResultPayload",
    "JobType",
    "OCRPayload",
    "OCRResult",
    "SandboxPayload",
    "SandboxResult",
    "GraderPayload",
    "GraderResult",
    "FinalResult",
}


def __getattr__(name: str):
    if name in _JOB_ATTRS:
        from . import jobs as _jobs

        return getattr(_jobs, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(list(globals().keys()) + list(_JOB_ATTRS))
