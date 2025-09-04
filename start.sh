#!/bin/bash

# Railway startup script
# This script ensures proper port binding for Railway deployment

# Set default port if PORT environment variable is not set
export PORT=${PORT:-5000}

echo "🚀 Starting SaaS ERP application on port $PORT"

# Start the application with gunicorn
exec gunicorn --bind 0.0.0.0:$PORT app:app
