#!/usr/bin/env bash

# Exit immediately if a command exits with a non-zero status
set -e

MESSAGE=$1

if [ -z "$MESSAGE" ]; then
  echo "❌ Error: Migration message required."
  echo "Usage: task push \"your migration message\""
  exit 1
fi

echo "🔨 [1/3] Generating local migration: $MESSAGE"
task mm "$MESSAGE"

echo "⚙️  [2/3] Applying migration to local database..."
task migrate

echo "🚀 [3/3] Pushing migration to Neon DB (Production)..."
task migrate_prod

echo "✅ Migration pipeline complete!"