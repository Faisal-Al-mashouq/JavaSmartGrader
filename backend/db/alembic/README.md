# Alembic Migrations

This directory stores migration revisions for the backend PostgreSQL schema. Run Alembic from `backend/` so `alembic.ini` and imports resolve correctly (see commands below).

## Where revisions live

- `versions/` contains one file per schema revision.
- Each revision declares:
  - `revision` (current id)
  - `down_revision` (previous id)
  - `upgrade()` and `downgrade()` steps

## Common commands

Run from `backend/`:

```bash
# Generate a migration from model changes
uv run alembic revision --autogenerate -m "describe change"

# Apply all pending migrations
uv run alembic upgrade head

# Roll back one migration
uv run alembic downgrade -1

# Show current migration
uv run alembic current

# Show migration history
uv run alembic history
```

## Notes

- Keep each migration focused and reversible.
- Review generated foreign keys/indexes carefully before committing.
- Use descriptive migration messages (e.g. `add_cascades_for_submission_children`).