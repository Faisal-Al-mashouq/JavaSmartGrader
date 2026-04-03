#!/bin/sh

set -eu

(cd /app/db && uv run alembic upgrade head)

exec "$@"
