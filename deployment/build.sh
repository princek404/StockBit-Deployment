#!/bin/bash
set -e


# Create required directories
mkdir -p instance
mkdir -p uploads

# Install dependencies
pip install -r requirements.txt

# Run migrations if possible
if command -v flask &> /dev/null; then
    # Initialize migrations if needed
    if [ ! -d "migrations" ]; then
        flask db init
    fi
    
    # Try to run migrations
    flask db migrate -m "Automated migration" || echo "Migration generation failed, continuing"
    flask db upgrade || echo "Migration upgrade failed, continuing"
else
    echo "Flask command not found, skipping migrations"
fi

# Direct database initialization
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
                # For PostgreSQL
                if app.config['SQLALCHEMY_DATABASE_URI'].startswith('postgresql'):
                    db.session.execute('ALTER TABLE \\\"user\\\" ADD COLUMN is_admin BOOLEAN DEFAULT false')
                # For SQLite
                else:
                    # SQLite doesn't support ALTER TABLE ADD COLUMN easily
                    # We'll create a new table and migrate data
                    db.session.execute('''
                        CREATE TABLE user_temp (
                            id INTEGER PRIMARY KEY,
                            username VARCHAR(80) UNIQUE NOT NULL,
                            email VARCHAR(120) UNIQUE NOT NULL,
                            password VARCHAR(120) NOT NULL,
                            business_name VARCHAR(100) NOT NULL,
                            created_at DATETIME,
                            is_premium BOOLEAN,
                            premium_since DATETIME,
                            phone VARCHAR(20),
                            subscription_active BOOLEAN,
                            is_admin BOOLEAN
                        )
                    ''')
                    db.session.execute('''
                        INSERT INTO user_temp (id, username, email, password, business_name, created_at, 
                            is_premium, premium_since, phone, subscription_active, is_admin)
                        SELECT id, username, email, password, business_name, created_at, 
                            is_premium, premium_since, phone, subscription_active, false
                        FROM \\\"user\\\"
                    ''')
                    db.session.execute('DROP TABLE \\\"user\\\"')
                    db.session.execute('ALTER TABLE user_temp RENAME TO \\\"user\\\"')
                
                db.session.commit()
                print(\"Added is_admin column to user table\")
            except Exception as e:
                print(f\"Error adding is_admin column: {str(e)}\")
                db.session.rollback()
    
    # Create tables if needed
    db.create_all()
    print('Database initialized directly')
"
