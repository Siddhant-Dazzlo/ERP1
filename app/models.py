from app.extensions import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import uuid
import enum

class UserRole(enum.Enum):
    ADMIN = "admin"
    MANAGER = "manager"
    SALES_EXECUTIVE = "sales_executive"

class SubscriptionPlan(enum.Enum):
    STARTER = "starter"
    PRO = "pro"
    ENTERPRISE = "enterprise"

class LeadStatus(enum.Enum):
    PROSPECT = "prospect"
    CONTACTED = "contacted"
    QUALIFIED = "qualified"
    PROPOSAL = "proposal"
    NEGOTIATION = "negotiation"
    CLOSED_WON = "closed_won"
    CLOSED_LOST = "closed_lost"

class TaskPriority(enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"

class TaskStatus(enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class Company(db.Model):
    """Multi-tenant company model"""
    __tablename__ = 'companies'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    subdomain = db.Column(db.String(50), unique=True, nullable=False)
    domain = db.Column(db.String(100), nullable=True)
    address = db.Column(db.Text)
    city = db.Column(db.String(100))
    state = db.Column(db.String(100))
    zip_code = db.Column(db.String(20))
    country = db.Column(db.String(100))
    industry = db.Column(db.String(100))
    size = db.Column(db.String(50))
    phone = db.Column(db.String(20))
    email = db.Column(db.String(120))
    website = db.Column(db.String(200))
    logo_url = db.Column(db.String(500))
    subscription_plan = db.Column(db.Enum(SubscriptionPlan), default=SubscriptionPlan.STARTER)
    subscription_start_date = db.Column(db.DateTime, default=datetime.utcnow)
    subscription_end_date = db.Column(db.DateTime)
    max_users = db.Column(db.Integer, default=5)
    max_storage_gb = db.Column(db.Integer, default=10)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    users = db.relationship('User', backref='company', lazy='dynamic')
    leads = db.relationship('Lead', backref='company', lazy='dynamic')
    customers = db.relationship('Customer', backref='company', lazy='dynamic')
    products = db.relationship('Product', backref='company', lazy='dynamic')
    quotations = db.relationship('Quotation', backref='company', lazy='dynamic')
    invoices = db.relationship('Invoice', backref='company', lazy='dynamic')
    tasks = db.relationship('Task', backref='company', lazy='dynamic')
    
    def __repr__(self):
        return f'<Company {self.name}>'

class User(UserMixin, db.Model):
    """User model with role-based access control"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.Enum(UserRole), default=UserRole.SALES_EXECUTIVE)
    phone = db.Column(db.String(20))
    avatar_url = db.Column(db.String(500))
    is_active = db.Column(db.Boolean, default=True)
    last_login = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    leads_assigned = db.relationship('Lead', backref='assigned_to', lazy='dynamic')
    tasks_assigned = db.relationship('Task', backref='assigned_to', lazy='dynamic')
    activities = db.relationship('Activity', backref='user', lazy='dynamic')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    @property
    def name(self):
        """Alias for get_full_name() for template compatibility"""
        return self.get_full_name()
    
    def __repr__(self):
        return f'<User {self.username}>'

class Lead(db.Model):
    """Lead management model"""
    __tablename__ = 'leads'
    
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    assigned_to_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20))
    company_name = db.Column(db.String(100))
    job_title = db.Column(db.String(100))
    industry = db.Column(db.String(100))
    source = db.Column(db.String(100))  # website, referral, cold_call, etc.
    status = db.Column(db.Enum(LeadStatus), default=LeadStatus.PROSPECT)
    estimated_value = db.Column(db.Numeric(10, 2))
    notes = db.Column(db.Text)
    next_follow_up = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    activities = db.relationship('Activity', backref='lead', lazy='dynamic')
    
    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    def __repr__(self):
        return f'<Lead {self.get_full_name()}>'

class Customer(db.Model):
    """Customer model for converted leads"""
    __tablename__ = 'customers'
    
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    lead_id = db.Column(db.Integer, db.ForeignKey('leads.id'))
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20))
    company_name = db.Column(db.String(100))
    address = db.Column(db.Text)
    tax_id = db.Column(db.String(50))
    credit_limit = db.Column(db.Numeric(10, 2))
    payment_terms = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    quotations = db.relationship('Quotation', backref='customer', lazy='dynamic')
    invoices = db.relationship('Invoice', backref='customer', lazy='dynamic')
    
    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    @property
    def name(self):
        """Alias for get_full_name() for template compatibility"""
        return self.get_full_name()
    
    def __repr__(self):
        return f'<Customer {self.get_full_name()}>'

class Product(db.Model):
    """Product catalog model"""
    __tablename__ = 'products'
    
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    sku = db.Column(db.String(100), unique=True)
    category = db.Column(db.String(100))
    unit_price = db.Column(db.Numeric(10, 2), nullable=False)
    cost_price = db.Column(db.Numeric(10, 2))
    tax_rate = db.Column(db.Numeric(5, 2), default=0.0)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    quotation_items = db.relationship('QuotationItem', backref='product', lazy='dynamic')
    invoice_items = db.relationship('InvoiceItem', backref='product', lazy='dynamic')
    
    def __repr__(self):
        return f'<Product {self.name}>'

class Quotation(db.Model):
    """Quotation model"""
    __tablename__ = 'quotations'
    
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False)
    quotation_number = db.Column(db.String(50), unique=True, nullable=False)
    subject = db.Column(db.String(200))
    valid_until = db.Column(db.DateTime)
    subtotal = db.Column(db.Numeric(10, 2), default=0.0)
    tax_amount = db.Column(db.Numeric(10, 2), default=0.0)
    total_amount = db.Column(db.Numeric(10, 2), default=0.0)
    status = db.Column(db.String(20), default='draft')  # draft, sent, accepted, rejected
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    items = db.relationship('QuotationItem', backref='quotation', lazy='dynamic')
    
    def __repr__(self):
        return f'<Quotation {self.quotation_number}>'

class QuotationItem(db.Model):
    """Quotation line items"""
    __tablename__ = 'quotation_items'
    
    id = db.Column(db.Integer, primary_key=True)
    quotation_id = db.Column(db.Integer, db.ForeignKey('quotations.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    description = db.Column(db.String(200))
    quantity = db.Column(db.Integer, nullable=False, default=1)
    unit_price = db.Column(db.Numeric(10, 2), nullable=False)
    discount_percent = db.Column(db.Numeric(5, 2), default=0.0)
    tax_rate = db.Column(db.Numeric(5, 2), default=0.0)
    total_amount = db.Column(db.Numeric(10, 2), nullable=False)
    
    def __repr__(self):
        return f'<QuotationItem {self.id}>'

class Invoice(db.Model):
    """Invoice model"""
    __tablename__ = 'invoices'
    
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False)
    quotation_id = db.Column(db.Integer, db.ForeignKey('quotations.id'))
    invoice_number = db.Column(db.String(50), unique=True, nullable=False)
    subject = db.Column(db.String(200))
    due_date = db.Column(db.DateTime)
    subtotal = db.Column(db.Numeric(10, 2), default=0.0)
    tax_amount = db.Column(db.Numeric(10, 2), default=0.0)
    total_amount = db.Column(db.Numeric(10, 2), default=0.0)
    status = db.Column(db.String(20), default='draft')  # draft, sent, paid, overdue
    payment_date = db.Column(db.DateTime)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    items = db.relationship('InvoiceItem', backref='invoice', lazy='dynamic')
    
    def __repr__(self):
        return f'<Invoice {self.invoice_number}>'

class InvoiceItem(db.Model):
    """Invoice line items"""
    __tablename__ = 'invoice_items'
    
    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoices.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    description = db.Column(db.String(200))
    quantity = db.Column(db.Integer, nullable=False, default=1)
    unit_price = db.Column(db.Numeric(10, 2), nullable=False)
    discount_percent = db.Column(db.Numeric(5, 2), default=0.0)
    tax_rate = db.Column(db.Numeric(5, 2), default=0.0)
    total_amount = db.Column(db.Numeric(10, 2), nullable=False)
    
    def __repr__(self):
        return f'<InvoiceItem {self.id}>'

class Task(db.Model):
    """Task and activity management model"""
    __tablename__ = 'tasks'
    
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    assigned_to_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    priority = db.Column(db.Enum(TaskPriority), default=TaskPriority.MEDIUM)
    status = db.Column(db.Enum(TaskStatus), default=TaskStatus.PENDING)
    due_date = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<Task {self.title}>'

class Activity(db.Model):
    """Activity log for leads and customers"""
    __tablename__ = 'activities'
    
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    lead_id = db.Column(db.Integer, db.ForeignKey('leads.id'))
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'))
    activity_type = db.Column(db.String(50), nullable=False)  # call, email, meeting, note
    subject = db.Column(db.String(200))
    description = db.Column(db.Text)
    scheduled_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Activity {self.activity_type}>'

class Subscription(db.Model):
    """Subscription and billing model"""
    __tablename__ = 'subscriptions'
    
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    plan = db.Column(db.Enum(SubscriptionPlan), nullable=False)
    stripe_subscription_id = db.Column(db.String(100))
    razorpay_subscription_id = db.Column(db.String(100))
    status = db.Column(db.String(20), default='active')  # active, canceled, past_due
    current_period_start = db.Column(db.DateTime)
    current_period_end = db.Column(db.DateTime)
    cancel_at_period_end = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<Subscription {self.plan.value}>'

class AuditLog(db.Model):
    """Audit logging for compliance"""
    __tablename__ = 'audit_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    action = db.Column(db.String(100), nullable=False)
    resource_type = db.Column(db.String(50))
    resource_id = db.Column(db.Integer)
    details = db.Column(db.JSON)
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<AuditLog {self.action}>'
