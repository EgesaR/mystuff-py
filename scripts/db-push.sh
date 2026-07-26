#!/usr/bin/env bash

set -e
uv run alembic revision --autogenerate -m "$1"
uv run alembic upgrade head
echo "✅ Migration '$1' created and applied"