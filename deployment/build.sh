#!/bin/bash
set -e


# Create required directories
mkdir -p instance
mkdir -p uploads

# Install dependencies
pip install -r requirements.txt

# Check if migrations directory exists
if [ -d "migrations" ]; then
    # Try normal migration
    flask db upgrade || echo "Migration failed, stamping head and continuing"
    flask db stamp head
else
    echo "No migrations directory found"
fi

# Direct database initialization
python -c "
from app import app, db
from sqlalchemy import inspect

with app.app_context():
    # Create tables if they don't exist
    db.create_all()
    
    # Check if the is_admin column exists
    inspector = inspect(db.engine)
    if 'user' in inspector.get_table_names():
        columns = [col['name'] for col in inspector.get_columns('user')]
        if 'is_admin' not in columns:
            print('Adding is_admin column to user table')
            # For PostgreSQL
            if app.config['SQLALCHEMY_DATABASE_URI'].startswith('postgresql'):
                db.session.execute('ALTER TABLE \"user\" ADD COLUMN is_admin BOOLEAN DEFAULT false')
            # For SQLite
            else:
                # SQLite requires table recreation
                db.session.execute('''
                    CREATE TABLE user_temp (
                        id INTEGER PRIMARY KEY,
                        username VARCHAR(80) UNIQUE NOT NULL,
                        email VARCHAR(120) UNIQUE NOT NULL,
                        password VARCHAR(120) NOT NULL,
                        business_name VARCHAR(100) NOT NULL,
                        created_at TIMESTAMP,
                        is_premium BOOLEAN,
                        premium_since TIMESTAMP,
                        phone VARCHAR(20),
                        subscription_active BOOLEAN
                    )
                ''')
                db.session.execute('''
                    INSERT INTO user_temp (id, username, email, password, business_name, created_at, 
                        is_premium, premium_since, phone, subscription_active)
                    SELECT id, username, email, password, business_name, created_at, 
                        is_premium, premium_since, phone, subscription_active
                    FROM \"user\"
                ''')
                db.session.execute('DROP TABLE \"user\"')
                db.session.execute('ALTER TABLE user_temp RENAME TO \"user\"')
                # Now add the is_admin column
                db.session.execute('ALTER TABLE \"user\" ADD COLUMN is_admin BOOLEAN DEFAULT false')
            
            db.session.commit()
    
    print('Database initialization complete')
"
