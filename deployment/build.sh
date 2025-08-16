#!/bin/bash
set -e  # Exit immediately on error

# Install dependencies
pip install -r requirements.txt

# Run migrations
flask db upgrade

# Create necessary directories
mkdir -p instance
mkdir -p uploads
