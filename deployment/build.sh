#!/bin/bash
set -e


# Create required directories
mkdir -p instance
mkdir -p uploads

# Install dependencies
pip install -r requirements.txt

# Initialize migrations if missing
if [ ! -d "migrations" ]; then
    flask db init
    echo "Initialized migrations directory"
fi

# Create migration scripts
if ! flask db migrate -m "Automated migration"; then
    echo "Migration generation failed, stamping head"
    flask db stamp head
fi

# Apply migrations
flask db upgrade

# Direct initialization fallback
python -c "
from app import app, db
with app.app_context():
    # Check if the is_admin column exists
    from sqlalchemy import inspect
    inspector = inspect(db.engine)
    if 'user' in inspector.get_table_names():
        columns = [col['name'] for col in inspector.get_columns('user')]
        if 'is_admin' not in columns:
            try:
                if app.config['SQLALCHEMY_DATABASE_URI'].startswith('postgresql'):
                    db.session.execute('ALTER TABLE \"user\" ADD COLUMN is_admin BOOLEAN DEFAULT false')
                db.session.commit()
                print('Added is_admin column')
            except Exception as e:
                print(f'Error adding column: {e}')
    
    # Create any missing tables
    db.create_all()
    print('Database initialization complete')
"
