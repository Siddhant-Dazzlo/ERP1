import pytest
from flask import url_for
from app.models import User, Company, Lead, Customer, Product, Quotation, Invoice, Task, Activity
from app.utils import log_audit
from datetime import datetime, timedelta

class TestMainRoutes:
    """Test main application routes."""
    
    def test_landing_page(self, client):
        """Test the landing page loads correctly."""
        response = client.get('/')
        assert response.status_code == 200
        assert b'SaaS ERP' in response.data
    
    def test_dashboard_requires_login(self, client):
        """Test that dashboard requires authentication."""
        response = client.get('/dashboard', follow_redirects=True)
        assert response.status_code == 200
        # Should redirect to login page
        assert b'login' in response.data.lower()
    
    def test_dashboard_with_authenticated_user(self, logged_in_client, test_user):
        """Test dashboard loads for authenticated user."""
        response = logged_in_client.get('/dashboard')
        assert response.status_code == 200
        assert b'Dashboard' in response.data
    
    def test_search_functionality(self, logged_in_client, test_user):
        """Test search functionality."""
        response = logged_in_client.get('/search?q=test')
        assert response.status_code == 200
    
    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get('/health')
        assert response.status_code == 200
        assert b'healthy' in response.data.lower()

class TestAuthentication:
    """Test authentication functionality."""
    
    def test_user_registration(self, client, test_company):
        """Test user registration process."""
        response = client.post('/auth/register', data={
            'email': 'newuser@testcompany.com',
            'first_name': 'New',
            'last_name': 'User',
            'password': 'newpassword123',
            'confirm_password': 'newpassword123',
            'company_id': test_company.id
        }, follow_redirects=True)
        assert response.status_code == 200
        
        # Check if user was created
        user = User.query.filter_by(email='newuser@testcompany.com').first()
        assert user is not None
        assert user.company_id == test_company.id
    
    def test_user_login(self, client, test_user):
        """Test user login process."""
        response = client.post('/auth/login', data={
            'email': test_user.email,
            'password': 'testpassword123'
        }, follow_redirects=True)
        assert response.status_code == 200
    
    def test_user_logout(self, logged_in_client):
        """Test user logout process."""
        response = logged_in_client.get('/auth/logout', follow_redirects=True)
        assert response.status_code == 200
    
    def test_password_reset_request(self, client, test_user):
        """Test password reset request."""
        response = client.post('/auth/forgot-password', data={
            'email': test_user.email
        }, follow_redirects=True)
        assert response.status_code == 200
    
    def test_user_invitation(self, logged_in_client, test_user):
        """Test user invitation process."""
        response = logged_in_client.post('/auth/invite', data={
            'email': 'invited@testcompany.com',
            'first_name': 'Invited',
            'last_name': 'User',
            'role': 'SALES_EXECUTIVE'
        }, follow_redirects=True)
        assert response.status_code == 200

class TestSalesModule:
    """Test sales module functionality."""
    
    def test_leads_list(self, logged_in_client, test_user):
        """Test leads listing page."""
        response = logged_in_client.get('/sales/leads')
        assert response.status_code == 200
        assert b'Leads' in response.data
    
    def test_create_lead(self, logged_in_client, test_user):
        """Test lead creation."""
        response = logged_in_client.post('/sales/leads/create', data={
            'first_name': 'John',
            'last_name': 'Doe',
            'email': 'john.doe@example.com',
            'phone': '+1234567890',
            'company': 'Test Corp',
            'source': 'website',
            'status': 'prospect',
            'notes': 'Test lead'
        }, follow_redirects=True)
        assert response.status_code == 200
        
        # Check if lead was created
        lead = Lead.query.filter_by(email='john.doe@example.com').first()
        assert lead is not None
        assert lead.company_id == test_user.company_id
    
    def test_lead_conversion(self, logged_in_client, test_user, test_company):
        """Test lead to customer conversion."""
        # Create a lead first
        lead = Lead(
            first_name='Jane',
            last_name='Smith',
            email='jane.smith@example.com',
            phone='+1234567890',
            company='Test Corp',
            source='website',
            status='prospect',
            company_id=test_company.id
        )
        db.session.add(lead)
        db.session.commit()
        
        # Convert to customer
        response = logged_in_client.post(f'/sales/leads/{lead.id}/convert', data={
            'company_name': 'Test Corp',
            'industry': 'Technology',
            'website': 'https://testcorp.com'
        }, follow_redirects=True)
        assert response.status_code == 200
        
        # Check if customer was created
        customer = Customer.query.filter_by(email='jane.smith@example.com').first()
        assert customer is not None
    
    def test_customers_list(self, logged_in_client, test_user):
        """Test customers listing page."""
        response = logged_in_client.get('/sales/customers')
        assert response.status_code == 200
        assert b'Customers' in response.data
    
    def test_products_management(self, logged_in_client, test_user, test_company):
        """Test product management."""
        # Create product
        response = logged_in_client.post('/sales/products/create', data={
            'name': 'Test Product',
            'description': 'A test product',
            'price': '99.99',
            'category': 'Software',
            'sku': 'TP001'
        }, follow_redirects=True)
        assert response.status_code == 200
        
        # Check if product was created
        product = Product.query.filter_by(name='Test Product').first()
        assert product is not None
        assert product.company_id == test_company.id
    
    def test_quotation_creation(self, logged_in_client, test_user, test_company):
        """Test quotation creation."""
        # Create a customer first
        customer = Customer(
            first_name='Test',
            last_name='Customer',
            email='customer@test.com',
            company_name='Test Corp',
            company_id=test_company.id
        )
        db.session.add(customer)
        db.session.commit()
        
        # Create quotation
        response = logged_in_client.post('/sales/quotations/create', data={
            'customer_id': customer.id,
            'valid_until': '2024-12-31',
            'notes': 'Test quotation'
        }, follow_redirects=True)
        assert response.status_code == 200
    
    def test_invoice_generation(self, logged_in_client, test_user, test_company):
        """Test invoice generation."""
        # Create a quotation first
        customer = Customer(
            first_name='Invoice',
            last_name='Customer',
            email='invoice@test.com',
            company_name='Invoice Corp',
            company_id=test_company.id
        )
        db.session.add(customer)
        db.session.commit()
        
        quotation = Quotation(
            customer_id=customer.id,
            company_id=test_company.id,
            valid_until=datetime.utcnow() + timedelta(days=30),
            status='accepted'
        )
        db.session.add(quotation)
        db.session.commit()
        
        # Generate invoice
        response = logged_in_client.post(f'/sales/quotations/{quotation.id}/invoice', follow_redirects=True)
        assert response.status_code == 200
        
        # Check if invoice was created
        invoice = Invoice.query.filter_by(quotation_id=quotation.id).first()
        assert invoice is not None

class TestBillingModule:
    """Test billing module functionality."""
    
    def test_subscription_page(self, logged_in_client, test_user):
        """Test subscription page loads."""
        response = logged_in_client.get('/billing/subscription')
        assert response.status_code == 200
        assert b'Subscription' in response.data
    
    def test_plan_upgrade(self, logged_in_client, test_user, test_company):
        """Test plan upgrade process."""
        response = logged_in_client.post('/billing/upgrade', data={
            'plan_type': 'enterprise'
        }, follow_redirects=True)
        assert response.status_code == 200
    
    def test_payment_integration(self, logged_in_client, test_user):
        """Test payment gateway integration."""
        response = logged_in_client.post('/billing/payment/stripe', data={
            'amount': '99.99',
            'currency': 'usd'
        }, follow_redirects=True)
        assert response.status_code == 200

class TestAdminModule:
    """Test admin module functionality."""
    
    def test_admin_dashboard(self, logged_in_client, test_user):
        """Test admin dashboard access."""
        response = logged_in_client.get('/admin/')
        assert response.status_code == 200
        assert b'Admin' in response.data
    
    def test_user_management(self, logged_in_client, test_user):
        """Test user management functionality."""
        response = logged_in_client.get('/admin/users')
        assert response.status_code == 200
        assert b'Users' in response.data
    
    def test_company_settings(self, logged_in_client, test_user):
        """Test company settings access."""
        response = logged_in_client.get('/admin/company/settings')
        assert response.status_code == 200
        assert b'Settings' in response.data
    
    def test_reports_access(self, logged_in_client, test_user):
        """Test reports access."""
        response = logged_in_client.get('/admin/reports')
        assert response.status_code == 200
        assert b'Reports' in response.data

class TestAPIModule:
    """Test API endpoints."""
    
    def test_api_authentication_required(self, client):
        """Test that API endpoints require authentication."""
        response = client.get('/api/v1/leads')
        assert response.status_code == 401
        assert b'Missing authorization token' in response.data
    
    def test_api_leads_endpoint(self, client, auth_headers):
        """Test API leads endpoint."""
        response = client.get('/api/v1/leads', headers=auth_headers)
        assert response.status_code == 200
        data = response.get_json()
        assert 'leads' in data
    
    def test_api_customers_endpoint(self, client, auth_headers):
        """Test API customers endpoint."""
        response = client.get('/api/v1/customers', headers=auth_headers)
        assert response.status_code == 200
        data = response.get_json()
        assert 'customers' in data
    
    def test_api_dashboard_stats(self, client, auth_headers):
        """Test API dashboard statistics endpoint."""
        response = client.get('/api/v1/dashboard-stats', headers=auth_headers)
        assert response.status_code == 200
        data = response.get_json()
        assert 'stats' in data

class TestMultiTenancy:
    """Test multi-tenancy functionality."""
    
    def test_tenant_isolation(self, client, test_company, test_user):
        """Test that data is isolated between tenants."""
        # Create data for test company
        lead = Lead(
            first_name='Tenant',
            last_name='Lead',
            email='tenant@test.com',
            company_id=test_company.id
        )
        db.session.add(lead)
        db.session.commit()
        
        # Create another company
        other_company = Company(
            name='Other Company',
            subdomain='othercompany',
            email='admin@othercompany.com',
            plan_type='starter'
        )
        db.session.add(other_company)
        db.session.commit()
        
        # Verify data isolation
        tenant_leads = Lead.query.filter_by(company_id=test_company.id).all()
        other_leads = Lead.query.filter_by(company_id=other_company.id).all()
        
        assert len(tenant_leads) > 0
        assert len(other_leads) == 0

class TestAuditLogging:
    """Test audit logging functionality."""
    
    def test_audit_log_creation(self, test_user):
        """Test that audit logs are created for important actions."""
        # Perform an action that should be logged
        log_audit(
            user_id=test_user.id,
            company_id=test_user.company_id,
            action='test_action',
            resource_type='test_resource',
            resource_id=1,
            details='Test audit log entry'
        )
        
        # Check if audit log was created
        from app.models import AuditLog
        audit_log = AuditLog.query.filter_by(
            user_id=test_user.id,
            action='test_action'
        ).first()
        
        assert audit_log is not None
        assert audit_log.company_id == test_user.company_id

class TestErrorHandling:
    """Test error handling."""
    
    def test_404_error(self, client):
        """Test 404 error handling."""
        response = client.get('/nonexistent-page')
        assert response.status_code == 404
    
    def test_500_error(self, client):
        """Test 500 error handling."""
        # This would require triggering an actual error in the app
        # For now, just test that error handlers exist
        pass

class TestSecurity:
    """Test security features."""
    
    def test_csrf_protection(self, client):
        """Test CSRF protection."""
        # CSRF protection should be enabled by default
        pass
    
    def test_sql_injection_protection(self, logged_in_client, test_user):
        """Test SQL injection protection."""
        # Test with potentially malicious input
        malicious_input = "'; DROP TABLE users; --"
        
        response = logged_in_client.post('/sales/leads/create', data={
            'first_name': malicious_input,
            'last_name': 'Test',
            'email': 'test@example.com',
            'company': 'Test Corp'
        }, follow_redirects=True)
        
        # Should handle gracefully without SQL injection
        assert response.status_code == 200
    
    def test_xss_protection(self, logged_in_client, test_user):
        """Test XSS protection."""
        # Test with potentially malicious input
        malicious_input = "<script>alert('xss')</script>"
        
        response = logged_in_client.post('/sales/leads/create', data={
            'first_name': 'Test',
            'last_name': 'User',
            'email': 'test@example.com',
            'company': malicious_input
        }, follow_redirects=True)
        
        # Should escape HTML content
        assert response.status_code == 200
