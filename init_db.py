#!/usr/bin/env python3
"""
Database initialization script for SaaS ERP
"""

from app import create_app
from app.extensions import db
from app.models import User, Company, UserRole, SubscriptionPlan

def init_db():
    """Initialize the database with all tables"""
    app = create_app()
    
    with app.app_context():
        # Create all tables
        db.create_all()
        print("Database tables created successfully!")
        
        # Check if we need to create a default company for testing
        if not Company.query.first():
            # Create a default company for testing
            default_company = Company(
                name="Demo Company",
                subdomain="demo",
                domain="demo.example.com",
                address="123 Demo Street",
                city="Demo City",
                state="Demo State",
                zip_code="12345",
                country="US",
                industry="Technology",
                size="1-10",
                phone="+1-555-123-4567",
                email="admin@democompany.com",
                website="https://democompany.com",
                is_active=True
            )
            db.session.add(default_company)
            db.session.flush()
            
            # Create a default admin user
            admin_user = User(
                company_id=default_company.id,
                email="admin@democompany.com",
                username="admin",
                first_name="Admin",
                last_name="User",
                role=UserRole.ADMIN,
                is_active=True
            )
            admin_user.set_password("admin123")
            
            db.session.add(admin_user)
            db.session.commit()
            
            print("Default company and admin user created!")
            print("Login: admin@democompany.com")
            print("Password: admin123")

if __name__ == "__main__":
    init_db()
