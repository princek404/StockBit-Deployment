#!/bin/bash
set -e


# Create required directories
mkdir -p instance
mkdir -p uploads

# Install dependencies
pip install -r requirements.txt

# Initialize database migrations
if [ ! -d "migrations" ]; then
    flask db init
fi

# Create migration if needed
flask db migrate -m "Automatic migration" || echo "Migration generation skipped"

# Apply migrations
flask db upgrade

# Verify tables exist
python -c "
from app import app, db
from sqlalchemy import inspect

with app.app_context():
    # Verify tables were created
    inspector = inspect(db.engine)
    required_tables = ['user', 'product', 'sale', 'supplier', 'payment_verification']
    
    missing_tables = [t for t in required_tables if t not in inspector.get_table_names()]
    
    if missing_tables:
        print(f'ERROR: Missing tables: {missing_tables}')
        exit(1)
    else:
        print('All required tables exist in database')
"
