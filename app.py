#!/usr/bin/env python3
"""
SaaS ERP - Main Application Entry Point
"""

import os
from app import create_app

# Create the Flask application
app = create_app()

if __name__ == '__main__':
    # Get port from environment variable (Railway sets this)
    port = int(os.environ.get('PORT', 5001))
    debug = os.environ.get('FLASK_ENV') == 'development'
    
    print(f"🚀 Starting Flask application on port {port}")
    print(f"🔧 Debug mode: {debug}")
    print(f"🌐 Host: 0.0.0.0")
    
    app.run(debug=debug, host='0.0.0.0', port=port)
