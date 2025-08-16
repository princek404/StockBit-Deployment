#!/bin/bash
set -e

mkdir -p instance
mkdir -p uploads


# Install dependencies
pip install -r requirements.txt

# Run database migrations
flask db upgrade

# Create tables if migrations fail
python -c "
from app import app, db
with app.app_context():
    try:
        db.create_all()
        print('Database tables created successfully')
    except Exception as e:
        print(f'Error creating tables: {str(e)}')
"
