#!/bin/bash
set -e


# Create required directories
mkdir -p instance
mkdir -p uploads

# Install dependencies
pip install -r requirements.txt

# Handle migrations
if [ -d "migrations" ]; then
    if [ ! -f "migrations/env.py" ]; then
        echo "Migrations directory exists but is incomplete - recreating"
        rm -rf migrations
        flask db init
    fi
else
    echo "Initializing new migrations"
    flask db init
fi

# Create new migration
flask db migrate -m "Auto migration" || echo "Migration generation skipped"

# Apply migrations
if flask db upgrade; then
    echo "Migrations applied successfully"
else
    echo "Migration failed - forcing table creation"
    python -c "
    from app import app, db
    with app.app_context():
        db.create_all()
        print('✓ Database tables created directly')
    "
fi

# Create admin user
python -c "
from app import app, db
from app import User
from werkzeug.security import generate_password_hash

with app.app_context():
    # Create admin user if not exists
    if not User.query.filter_by(is_admin=True).first():
        admin = User(
            username='admin',
            email='admin@example.com',
            password=generate_password_hash('adminpassword'),
            business_name='Admin Business',
            is_admin=True
        )
        db.session.add(admin)
        db.session.commit()
        print('✓ Admin user created')
    else:
        print('Admin user already exists')
"
