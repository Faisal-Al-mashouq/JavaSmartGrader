# Database Layer

Async PostgreSQL database layer using SQLAlchemy 2.0 ORM and Alembic for migrations.

## Structure

```
db/
├── models/
│   ├── base.py              # Declarative base
│   ├── main_db.py           # All ORM models
│   └── __init__.py          # Re-exports models
├── crud/
│   ├── users.py             # User CRUD operations
│   ├── courses.py           # Course CRUD, student enrollment/unenrollment
│   ├── assignments.py       # Assignment CRUD operations
│   ├── questions.py         # Question and Testcase CRUD operations
│   ├── submissions.py       # Submission CRUD operations
│   ├── grading.py           # CompileResult, Transcription, AIFeedback, Grade CRUD
│   ├── confidence_flags.py  # ConfidenceFlag CRUD operations
│   ├── generate_report.py   # GenerateReport CRUD operations
│   └── __init__.py          # Re-exports all CRUD functions
├── alembic/                 # Migration versions
├── alembic.ini              # Alembic configuration
├── session.py               # Async engine and session factory
└── README.md                # This file
```

## Models

| Model | Table | Description |
|-------|-------|-------------|
| `User` | `users` | Students and instructors (role-based) |
| `Course` | `courses` | Courses with instructor ownership |
| `course_students` | `course_students` | Many-to-many join table for course enrollment |
| `Assignment` | `assignments` | Assignments linked to courses with due dates and rubrics |
| `Question` | `questions` | Questions within assignments (composite PK: id + assignment_id) |
| `Testcase` | `testcases` | Input/output test cases per question |
| `Submission` | `submissions` | Student submissions linked to questions |
| `CompileResult` | `compile_results` | Compilation and runtime results per submission |
| `Transcription` | `transcriptions` | OCR/transcription output per submission |
| `ConfidenceFlag` | `confidence_flags` | OCR confidence scores and suggestions per transcription |
| `AIFeedback` | `ai_feedback` | AI-suggested grade and feedback per submission |
| `Grade` | `grades` | Final instructor grade per submission |
| `GenerateReport` | `generate_reports` | Generated reports per assignment |

## Relationships

- `User` 1:N `Course` (instructor creates courses)
- `User` N:M `Course` (students enroll in courses via `course_students`)
- `Course` 1:N `Assignment` (course has assignments)
- `Assignment` 1:N `Question` (assignment has questions)
- `Assignment` 1:N `GenerateReport` (assignment has reports)
- `Question` 1:N `Testcase` (question has test cases)
- `Question` 1:N `Submission` (question receives submissions)
- `User` 1:N `Submission` (student submits work)
- `Submission` 1:1 `CompileResult`, `Transcription`, `AIFeedback`, `Grade`
- `Transcription` 1:N `ConfidenceFlag` (transcription has confidence flags)
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
