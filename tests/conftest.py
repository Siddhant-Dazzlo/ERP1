import pytest
import os
import tempfile
from app import create_app, db
from app.models import User, Company, UserRole
from flask_login import login_user
import jwt
from datetime import datetime, timedelta

@pytest.fixture
def app():
    """Create and configure a new app instance for each test."""
    # Create a temporary file to isolate the database for each test
    db_fd, db_path = tempfile.mkstemp()
    
    app = create_app('testing')
    
    # Configure the app for testing
    app.config.update({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': f'sqlite:///{db_path}',
        'WTF_CSRF_ENABLED': False,
        'SECRET_KEY': 'test-secret-key',
        'MAIL_SUPPRESS_SEND': True,
        'CELERY_ALWAYS_EAGER': True,
        'REDIS_URL': 'redis://localhost:6379/1'
    })
    
    # Create the database and load test data
    with app.app_context():
        db.create_all()
        create_test_data()
        yield app
        db.session.remove()
        db.drop_all()
    
    # Clean up the temporary database
    os.close(db_fd)
    os.unlink(db_path)

@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()

@pytest.fixture
def runner(app):
    """A test runner for the app's Click commands."""
    return app.test_cli_runner()

@pytest.fixture
def test_company():
    """Create a test company."""
    company = Company(
        name='Test Company',
        subdomain='testcompany',
        email='admin@testcompany.com',
        phone='+1234567890',
        address='123 Test St, Test City, TC 12345',
        plan_type='pro',
        max_users=10,
        max_storage_gb=100,
        is_active=True
    )
    db.session.add(company)
    db.session.commit()
    return company

@pytest.fixture
def test_user(test_company):
    """Create a test user."""
    user = User(
        email='test@testcompany.com',
        first_name='Test',
        last_name='User',
        password='testpassword123',
        role=UserRole.ADMIN,
        company_id=test_company.id,
        is_active=True,
        email_verified=True
    )
    db.session.add(user)
    db.session.commit()
    return user

@pytest.fixture
def test_manager(test_company):
    """Create a test manager user."""
    user = User(
        email='manager@testcompany.com',
        first_name='Test',
        last_name='Manager',
        password='testpassword123',
        role=UserRole.MANAGER,
        company_id=test_company.id,
        is_active=True,
        email_verified=True
    )
    db.session.add(user)
    db.session.commit()
    return user

@pytest.fixture
def test_sales_executive(test_company):
    """Create a test sales executive user."""
    user = User(
        email='sales@testcompany.com',
        first_name='Test',
        last_name='Sales',
        password='testpassword123',
        role=UserRole.SALES_EXECUTIVE,
        company_id=test_company.id,
        is_active=True,
        email_verified=True
    )
    db.session.add(user)
    db.session.commit()
    return user

@pytest.fixture
def auth_headers(test_user):
    """Generate authentication headers for API requests."""
    token = jwt.encode(
        {
            'user_id': test_user.id,
            'company_id': test_user.company_id,
            'exp': datetime.utcnow() + timedelta(hours=1)
        },
        'test-secret-key',
        algorithm='HS256'
    )
    return {'Authorization': f'Bearer {token}'}

@pytest.fixture
def logged_in_client(client, test_user):
    """Create a client with a logged-in user."""
    with client.session_transaction() as sess:
        sess['user_id'] = test_user.id
        sess['company_id'] = test_user.company_id
    return client

def create_test_data():
    """Create test data for the database."""
    # Create a test company
    company = Company(
        name='Test Company',
        subdomain='testcompany',
        email='admin@testcompany.com',
        phone='+1234567890',
        address='123 Test St, Test City, TC 12345',
        plan_type='pro',
        max_users=10,
        max_storage_gb=100,
        is_active=True
    )
    db.session.add(company)
    db.session.commit()
    
    # Create test users
    admin_user = User(
        email='admin@testcompany.com',
        first_name='Admin',
        last_name='User',
        password='adminpass123',
        role=UserRole.ADMIN,
        company_id=company.id,
        is_active=True,
        email_verified=True
    )
    
    manager_user = User(
        email='manager@testcompany.com',
        first_name='Manager',
        last_name='User',
        password='managerpass123',
        role=UserRole.MANAGER,
        company_id=company.id,
        is_active=True,
        email_verified=True
    )
    
    sales_user = User(
        email='sales@testcompany.com',
        first_name='Sales',
        last_name='User',
        password='salespass123',
        role=UserRole.SALES_EXECUTIVE,
        company_id=company.id,
        is_active=True,
        email_verified=True
    )
    
    db.session.add_all([admin_user, manager_user, sales_user])
    db.session.commit()

class AuthActions:
    """Helper class for authentication actions in tests."""
    
    def __init__(self, client):
        self._client = client
    
    def login(self, email='admin@testcompany.com', password='adminpass123'):
        return self._client.post('/auth/login', data={
            'email': email,
            'password': password
        }, follow_redirects=True)
    
    def logout(self):
        return self._client.get('/auth/logout', follow_redirects=True)

@pytest.fixture
def auth(client):
    """Authentication helper fixture."""
    return AuthActions(client)

# Mock external services
@pytest.fixture(autouse=True)
def mock_external_services(monkeypatch):
    """Mock external services to avoid actual API calls during testing."""
    
    def mock_send_email(*args, **kwargs):
        return True
    
    def mock_send_sms(*args, **kwargs):
        return True
    
    def mock_send_whatsapp(*args, **kwargs):
        return True
    
    def mock_stripe_payment(*args, **kwargs):
        return {'id': 'pi_test123', 'status': 'succeeded'}
    
    def mock_razorpay_payment(*args, **kwargs):
        return {'id': 'order_test123', 'status': 'created'}
    
    # Apply mocks
    monkeypatch.setattr('app.utils.send_email', mock_send_email)
    monkeypatch.setattr('app.utils.send_sms', mock_send_sms)
    monkeypatch.setattr('app.utils.send_whatsapp_message', mock_whatsapp)
    monkeypatch.setattr('app.utils.create_stripe_payment_intent', mock_stripe_payment)
    monkeypatch.setattr('app.utils.create_razorpay_order', mock_razorpay_payment)

# Test database session
@pytest.fixture(autouse=True)
def session(app):
    """Provide a database session for tests."""
    with app.app_context():
        yield db.session

# Clean up after each test
@pytest.fixture(autouse=True)
def cleanup():
    """Clean up after each test."""
    yield
    # Any cleanup code can go here
