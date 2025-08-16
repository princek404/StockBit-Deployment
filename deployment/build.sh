#!/bin/bash
set -e

cd deployment

# Create required directories
mkdir -p instance
mkdir -p uploads

# Install dependencies
pip install -r requirements.txt

# Run migrations
flask db upgrade
