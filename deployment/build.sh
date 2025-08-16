#!/bin/bash
set -e


# Create required directories
mkdir -p instance
mkdir -p uploads
mkdir -p migrations  # Ensure migrations directory exists

# Install dependencies
pip install -r requirements.txt

# Initialize migrations if needed
if [ ! -f "migrations/alembic.ini" ]; then
    echo "Initializing new migrations..."
    flask db init
fi

# Create new migration
flask db migrate -m "Auto migration" || echo "Migration generation might have issues - continuing"

# Apply migrations
if flask db upgrade; then
    echo "Migrations applied successfully"
else
    echo "Migration failed - stamping head version"
    flask db stamp head
    flask db upgrade || echo "Final upgrade attempt failed"
fi

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
        print('✓ All required tables exist in database')
"
        db.create_all()
        print('Database tables verified')
    except Exception as e:
        print(f'Error creating tables: {str(e)}')
"
