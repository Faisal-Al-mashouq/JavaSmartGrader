from fastapi import FastAPI

from api.routes import assignments, grading, submissions, users

app = FastAPI()

app.include_router(users.router, prefix="/users", tags=["users"])
app.include_router(assignments.router, prefix="/assignments", tags=["assignments"])
app.include_router(submissions.router, prefix="/submissions", tags=["submissions"])
app.include_router(grading.router, prefix="/grading", tags=["grading"])
