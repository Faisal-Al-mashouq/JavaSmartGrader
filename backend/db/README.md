# Database Layer

Async PostgreSQL database layer using SQLAlchemy 2.0 ORM and Alembic for migrations.

## Structure

```
db/
├── models/
│   ├── base.py          # Declarative base
│   ├── main_db.py       # All ORM models
│   └── __init__.py      # Re-exports models
├── crud/
│   ├── users.py         # User CRUD operations
│   ├── assignments.py   # Assignment CRUD operations
│   ├── submissions.py   # Submission CRUD operations
│   ├── grading.py       # Testcase, CompileResult, Transcription, AIFeedback, Grade CRUD
│   └── __init__.py      # Re-exports all CRUD functions
├── alembic/             # Migration versions
├── alembic.ini          # Alembic configuration
├── session.py           # Async engine and session factory
└── README.md            # This file
```

## Models

| Model | Table | Description |
|-------|-------|-------------|
| `User` | `users` | Students and instructors (role-based) |
| `Assignment` | `assignments` | Instructor-created assignments with questions and test cases |
| `Submission` | `submissions` | Student submissions linked to assignments |
| `Testcase` | `testcases` | Input/output test cases per assignment |
| `CompileResult` | `compile_results` | Compilation and runtime results per submission |
| `Transcription` | `transcriptions` | OCR/transcription output per submission |
| `AIFeedback` | `ai_feedback` | AI-suggested grade and feedback per submission |
| `Grade` | `grades` | Final instructor grade per submission |

## Relationships

- `User` 1:N `Assignment` (instructor creates assignments)
- `User` 1:N `Submission` (student submits work)
- `Assignment` 1:N `Testcase` (assignment has test cases)
- `Assignment` 1:N `Submission` (assignment receives submissions)
- `Submission` 1:1 `CompileResult`, `Transcription`, `AIFeedback`, `Grade`
- `User` 1:N `Grade` (instructor gives grades)

## Migrations

```bash
# Generate a new migration after model changes
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1
```
