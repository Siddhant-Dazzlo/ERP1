# Flask SaaS ERP Application Package

from flask import Flask
from app.extensions import db, migrate, login_manager, mail, limiter, compress
import os
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()

def create_app(config_name='development'):
    # Get the absolute path to the app directory
    app_dir = os.path.dirname(os.path.abspath(__file__))
    # Go up one level to the project root
    project_root = os.path.dirname(app_dir)
    # Set template folder to the templates directory in project root
    template_dir = os.path.join(project_root, 'templates')
    
    app = Flask(__name__, template_folder=template_dir)
    
    # Configuration
    if config_name == 'development':
        app.config.from_object('config.DevelopmentConfig')
    elif config_name == 'production':
        app.config.from_object('config.ProductionConfig')
    elif config_name == 'testing':
        app.config.from_object('config.TestingConfig')
    else:
        app.config.from_object('config.DevelopmentConfig')
    
    # Initialize extensions with app
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    mail.init_app(app)
    limiter.init_app(app)
    compress.init_app(app)
    
    # Configure login manager
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'
    
    # User loader for Flask-Login
    @login_manager.user_loader
    def load_user(user_id):
        # Import here to avoid circular imports
        from app.models import User
        try:
            # Try to convert to integer first
            user_id_int = int(user_id)
            return User.query.get(user_id_int)
        except (ValueError, TypeError):
            # If conversion fails, try to find by username or email
            # This handles cases where user_id might be a string like 'admin-001'
            user = User.query.filter_by(username=user_id).first()
            if not user:
                user = User.query.filter_by(email=user_id).first()
            return user
    
    # Multi-tenancy middleware
    @app.before_request
    def before_request():
        from flask import request, g
        host = request.host
        
        # Skip tenant detection for local development
        if host in ['localhost', '127.0.0.1'] or ':' in host:
            g.tenant = None
        elif '.' in host:
            subdomain = host.split('.')[0]
            if subdomain not in ['www', 'api', 'admin']:
                g.tenant = subdomain
            else:
                g.tenant = None
        else:
            g.tenant = None
    
    # Register blueprints
    from app.auth import auth_bp
    from app.main import main_bp
    from app.sales import sales_bp
    from app.billing import billing_bp
    from app.admin import admin_bp
    from app.api import api_bp
    
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(main_bp)
    app.register_blueprint(sales_bp, url_prefix='/sales')
    app.register_blueprint(billing_bp, url_prefix='/billing')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(api_bp, url_prefix='/api/v1')
    
    # Register Jinja2 filters
    from app.utils import format_currency, format_date
    app.jinja_env.filters['currency'] = format_currency
    app.jinja_env.filters['date'] = format_date
    
    # Add timesince filter for relative time
    def timesince(dt):
        """Return relative time string (e.g., '2 hours ago')"""
        if not dt:
            return ''
        
        now = datetime.utcnow()
        diff = now - dt
        
        if diff.days > 0:
            return f"{diff.days} days ago"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours} hours ago"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"{minutes} minutes ago"
        else:
            return "Just now"
    
    app.jinja_env.filters['timesince'] = timesince
    
    # Error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        return 'Page not found', 404
    
    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return 'Internal server error', 500
    
    # Health check endpoint
    @app.route('/health')
    def health_check():
        return 'healthy', 200
    
    return app
