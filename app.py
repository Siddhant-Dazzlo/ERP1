#!/usr/bin/env python3
"""
SaaS ERP - Development Server Entry Point
For production deployment, use wsgi.py
"""

import os
import sys

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app

if __name__ == '__main__':
    # Create the Flask application
    app = create_app()
    
    # Get port from environment variable (Railway sets this)
    port = int(os.environ.get('PORT', 5001))
    debug = os.environ.get('FLASK_ENV') == 'development'
    
    print(f"🚀 Starting Flask development server on port {port}")
    print(f"🔧 Debug mode: {debug}")
    print(f"🌐 Host: 0.0.0.0")
    print("💡 For production, use: gunicorn --config gunicorn.conf.py wsgi:app")
    
    app.run(debug=debug, host='0.0.0.0', port=port)
