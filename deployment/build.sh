#!/bin/bash
set -e


# Create required directories
mkdir -p instance
mkdir -p uploads
mkdir -p migrations/versions  # Ensure migrations directory exists

# Install dependencies
pip install -r requirements.txt

# Initialize migrations if needed
if [ ! -f "migrations/alembic.ini" ]; then
    echo "Initializing new migrations..."
    flask db init
fi

# Create new migration
flask db migrate -m "Auto migration" || echo "Migration generation might have issues - continuing"

# Apply migrations with error handling
flask db upgrade || (
    echo "Migration failed - attempting to resolve"
    # Handle specific "duplicate column" error
    if grep -q "duplicate column name: is_admin" logs.txt; then
        echo "Column already exists - stamping head version"
        flask db stamp head
    fi
    
    # Final upgrade attempt
    flask db upgrade || echo "Final upgrade attempt failed"
)

# Fallback table creation
python -c "
from app import app, db
with app.app_context():
    try:
        db.create_all()
        print('Database tables verified')
    except Exception as e:
        print(f'Error creating tables: {str(e)}')
"
