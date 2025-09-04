#!/usr/bin/env python3
"""
SaaS ERP Setup Script
This script initializes the database and creates the first admin user.
"""

import os
import sys
from datetime import datetime, timedelta

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import Company, User, UserRole, Subscription, SubscriptionPlan

def create_platform_admin():
    """Create the platform administrator company and user"""
    print("Creating platform administrator...")
    
    # Create platform company
    platform_company = Company(
        name='Sales ERP Platform',
        subdomain='admin',
        domain='saas-erp.com',
        subscription_plan=SubscriptionPlan.ENTERPRISE,
        max_users=1000,
        max_storage_gb=1000,
        is_active=True
    )
    
    db.session.add(platform_company)
    db.session.commit()
    
    print(f"✓ Platform company created with ID: {platform_company.id}")
    
    # Create platform admin user
    admin_user = User(
        company_id=platform_company.id,
        email='admin@saas-erp.com',
        username='platform_admin',
        first_name='Platform',
        last_name='Administrator',
        role=UserRole.ADMIN,
        is_active=True
    )
    admin_user.set_password('admin123')
    
    db.session.add(admin_user)
    db.session.commit()
    
    print(f"✓ Platform admin user created with ID: {admin_user.id}")
    print("  Email: admin@saas-erp.com")
    print("  Password: admin123")
    
    # Create subscription record
    subscription = Subscription(
        company_id=platform_company.id,
        plan=SubscriptionPlan.ENTERPRISE,
        status='active',
        current_period_start=datetime.utcnow(),
        current_period_end=datetime.utcnow() + timedelta(days=365)
    )
    
    db.session.add(subscription)
    db.session.commit()
    
    print("✓ Platform subscription created")
    
    return platform_company, admin_user

def create_demo_company():
    """Create a demo company for testing"""
    print("\nCreating demo company...")
    
    # Create demo company
    demo_company = Company(
        name='Demo Company',
        subdomain='demo',
        domain='saas-erp.com',
        subscription_plan=SubscriptionPlan.PRO,
        max_users=20,
        max_storage_gb=100,
        is_active=True
    )
    
    db.session.add(demo_company)
    db.session.commit()
    
    print(f"✓ Demo company created with ID: {demo_company.id}")
    
    # Create demo users
    demo_users = [
        {
            'email': 'manager@demo.com',
            'username': 'demo_manager',
            'first_name': 'John',
            'last_name': 'Manager',
            'role': UserRole.MANAGER,
            'password': 'demo123'
        },
        {
            'email': 'sales1@demo.com',
            'username': 'demo_sales1',
            'first_name': 'Sarah',
            'last_name': 'Sales',
            'role': UserRole.SALES_EXECUTIVE,
            'password': 'demo123'
        },
        {
            'email': 'sales2@demo.com',
            'username': 'demo_sales2',
            'first_name': 'Mike',
            'last_name': 'Sales',
            'role': UserRole.SALES_EXECUTIVE,
            'password': 'demo123'
        }
    ]
    
    for user_data in demo_users:
        user = User(
            company_id=demo_company.id,
            email=user_data['email'],
            username=user_data['username'],
            first_name=user_data['first_name'],
            last_name=user_data['last_name'],
            role=user_data['role'],
            is_active=True
        )
        user.set_password(user_data['password'])
        db.session.add(user)
    
    db.session.commit()
    
    print("✓ Demo users created:")
    for user_data in demo_users:
        print(f"  {user_data['email']} / {user_data['password']}")
    
    # Create subscription record
    subscription = Subscription(
        company_id=demo_company.id,
        plan=SubscriptionPlan.PRO,
        status='active',
        current_period_start=datetime.utcnow(),
        current_period_end=datetime.utcnow() + timedelta(days=30)
    )
    
    db.session.add(subscription)
    db.session.commit()
    
    print("✓ Demo subscription created")
    
    return demo_company

def main():
    """Main setup function"""
    print("🚀 SaaS ERP Setup Script")
    print("=" * 50)
    
    try:
        # Create Flask app
        app = create_app()
        
        with app.app_context():
            # Create database tables
            print("Creating database tables...")
            db.create_all()
            print("✓ Database tables created")
            
            # Check if platform admin already exists
            existing_admin = Company.query.filter_by(subdomain='admin').first()
            if existing_admin:
                print("⚠ Platform administrator already exists, skipping...")
            else:
                # Create platform admin
                platform_company, admin_user = create_platform_admin()
            
            # Check if demo company already exists
            existing_demo = Company.query.filter_by(subdomain='demo').first()
            if existing_demo:
                print("⚠ Demo company already exists, skipping...")
            else:
                # Create demo company
                demo_company = create_demo_company()
            
            print("\n🎉 Setup completed successfully!")
            print("\nAccess URLs:")
            print("  Platform Admin: http://admin.saas-erp.com")
            print("  Demo Company: http://demo.saas-erp.com")
            print("\nDefault Credentials:")
            print("  Platform Admin: admin@saas-erp.com / admin123")
            print("  Demo Manager: manager@demo.com / demo123")
            print("  Demo Sales: sales1@demo.com / demo123")
            
    except Exception as e:
        print(f"❌ Setup failed: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main()
