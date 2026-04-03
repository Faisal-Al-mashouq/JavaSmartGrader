# Database Layer

Async PostgreSQL data layer built with SQLAlchemy 2.x and Alembic.

## Layout

```text
db/
├── models/       # ORM models
├── crud/         # DB operation helpers used by routes/services
├── alembic/      # Migration versions
├── alembic.ini   # Alembic config
├── session.py    # Async engine/session factory
└── settings.py   # Re-exports shared `backend/settings.py` (`settings`)
```

## Core Entities

- `User` (student/instructor roles)
- `Course` + `course_students` (enrollment)
- `Assignment`
- `Question` (composite key with assignment scope)
- `Testcase`
- `Submission` (handwritten image stored as an S3 object key in `image_url` after API upload)
- `CompileResult`
- `Transcription`
- `ConfidenceFlag`
- `AIFeedback`
- `Grade`
- `GenerateReport`

## Migration Commands

Run from `backend/`:

```bash
# Create migration from model changes
uv run alembic revision --autogenerate -m "description"

# Upgrade to latest
uv run alembic upgrade head

# Downgrade one revision
uv run alembic downgrade -1
```

More Alembic details: `db/alembic/README.md`.
