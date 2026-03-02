import logging

from api.routes import (
    assignments,
    confidence_flags,
    courses,
    generate_report,
    grading,
    questions,
    submissions,
    users,
)
from fastapi import FastAPI
from logs import setup_logging

app = FastAPI()
setup_logging()
logger = logging.getLogger(__name__)

logger.info("Starting JavaSmartGrader API server")
logger.debug("Debug Mode: On")

app.include_router(users.router, prefix="/users", tags=["users"])
app.include_router(courses.router, prefix="/courses", tags=["courses"])
app.include_router(assignments.router, prefix="/assignments", tags=["assignments"])
app.include_router(
    questions.router,
    prefix="/assignments/{assignment_id}/questions",
    tags=["questions"],
)
app.include_router(submissions.router, prefix="/submissions", tags=["submissions"])
app.include_router(grading.router, prefix="/grading", tags=["grading"])
app.include_router(
    confidence_flags.router,
    prefix="/confidence-flags",
    tags=["confidence-flags"],
)
app.include_router(generate_report.router, prefix="/reports", tags=["reports"])

logger.info("All routers registered successfully")
