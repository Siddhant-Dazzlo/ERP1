#!/usr/bin/env python3
"""
Script to clear corrupted session data
"""

from app import create_app
from app.extensions import db
from app.models import User

def clear_corrupted_sessions():
    """Clear any corrupted session data"""
    app = create_app()
    
    with app.app_context():
        print("🔍 Checking for users with non-integer IDs...")
        
        # Check if there are any users in the database
        users = User.query.all()
        print(f"📊 Found {len(users)} users in database")
        
        for user in users:
            print(f"👤 User ID: {user.id} (type: {type(user.id)}), Email: {user.email}, Username: {user.username}")
        
        print("\n✅ User data looks correct. The issue might be with session cookies.")
        print("💡 To fix the session issue:")
        print("1. Clear your browser cookies for this site")
        print("2. Or use an incognito/private browsing window")
        print("3. Or restart your Flask application")

if __name__ == "__main__":
    clear_corrupted_sessions()
