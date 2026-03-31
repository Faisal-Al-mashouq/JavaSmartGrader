import asyncio
import logging
import os
from contextlib import asynccontextmanager

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
from core.job_queue import start as start_job_queue
from db.session import engine
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from logs import setup_logging
from settings import settings

setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting JavaSmartGrader API server")
    logger.debug("Debug Mode: On")

    app.state.db = await engine.connect()
    logger.info("Database connected successfully")

    app.state.job_queue = asyncio.create_task(start_job_queue())
    logger.info("Job queue started successfully")

    if settings.app_env == "all":
        from ai_grader.main import start as start_grader_worker
        from ocr.main import start as start_ocr_worker
        from sandbox.sandbox_worker import start as start_sandbox_worker

        app.state.ocr_worker = asyncio.create_task(start_ocr_worker())
        app.state.sandbox_worker = asyncio.create_task(start_sandbox_worker())
        app.state.grader_worker = asyncio.create_task(start_grader_worker())
        logger.debug("Sandbox, OCR and Grader workers started successfully")

    try:
        yield
    except Exception:
        logger.error("Error in lifespan")
        raise
    finally:
        logger.info("Shutting down JavaSmartGrader API server")

        app.state.job_queue.cancel()
        try:
            await app.state.job_queue
        except asyncio.CancelledError:
            pass
        logger.debug("Job queue shut down successfully")

        if settings.app_env == "all":
            app.state.ocr_worker.cancel()
            try:
                await app.state.ocr_worker
            except asyncio.CancelledError:
                pass
            app.state.sandbox_worker.cancel()
            try:
                await app.state.sandbox_worker
            except asyncio.CancelledError:
                pass
            app.state.grader_worker.cancel()
            try:
                await app.state.grader_worker
            except asyncio.CancelledError:
                pass
            logger.debug("Sandbox, OCR and Grader workers shut down successfully")

        await engine.dispose()
        logger.info("Shutdown complete")
        os._exit(0)


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
