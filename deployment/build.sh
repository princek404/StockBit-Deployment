#!/bin/bash
set -e  # Exit immediately on error

# Install dependencies
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
else
    echo "ERROR: requirements.txt not found!"
    echo "Contents of current directory:"
    ls -la
    exit 1
fi

# Run database migrations
flask db upgrade
