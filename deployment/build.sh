#!/bin/bash
set -e



# Create required directories
mkdir -p instance
mkdir -p uploads

# Install dependencies
pip install -r requirements.txt


# Generate and apply migrations
flask db migrate -m "Initial migration"
flask db upgrade

# ... rest of your script ...
