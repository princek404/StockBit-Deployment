#!/bin/bash
set -e

cd deployment

# Create required directories
mkdir -p instance
mkdir -p uploads

# Install dependencies
pip install -r requirements.txt

# Reinitialize migrations if directory is missing
if [ ! -d "migrations" ]; then
    flask db init
    echo "Reinitialized migrations directory"
fi

# Generate and apply migrations
flask db migrate -m "Initial migration"
flask db upgrade

# ... rest of your script ...
