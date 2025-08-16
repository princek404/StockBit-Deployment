#!/bin/bash
set -e

mkdir -p instance
mkdir -p uploads


# Install dependencies
pip install -r requirements.txt

# Run database migrations
flask db upgrade
