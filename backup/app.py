#!/usr/bin/env python3
"""
SaaS ERP - Main Application Entry Point
"""

from app import create_app

# Create the Flask application
app = create_app()

if __name__ == '__main__':
    app.run(debug=True, host='localhost', port=5001)
