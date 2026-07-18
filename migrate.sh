#!/usr/bin/env bash
# ==============================================================================
# Volta Memory Migration Utility
# Runs Postgres database migrations against the configured DATABASE_URL.
# ==============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Checking dependencies..."
if ! python3 -c "import psycopg" &>/dev/null; then
    echo "psycopg not found. Installing psycopg and python-dotenv..."
    pip3 install --user psycopg[binary] python-dotenv
fi

echo "Running migrations..."
python3 "${SCRIPT_DIR}/scripts/run_migrations.py"
