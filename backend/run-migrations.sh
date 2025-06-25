#!/bin/sh

# Exit on error
set -e

# Wait for PostgreSQL to be ready
echo "Waiting for postgres..."
while ! nc -z postgres 5432; do
  sleep 1
done
echo "PostgreSQL started"

# Run migrations
echo "Running migrations..."
alembic stamp head
alembic upgrade head
echo "Migrations complete."

# Start the application
echo "Starting application..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 