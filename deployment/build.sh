#!/bin/bash
set -e


# Create required directories
mkdir -p instance
mkdir -p uploads

# Install dependencies
pip install -r requirements.txt

flask db migrate -m "Initial Supabase migration"

flask db upgrade
