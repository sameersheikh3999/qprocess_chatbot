#!/bin/bash
set -e

# Run your environment initialization command
echo "Running initialization..."
python manage.py migrate

# Now run the main server command
echo "Starting server..."
exec python manage.py runserver 0.0.0.0:8000

