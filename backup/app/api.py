from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from app.extensions import db
from app.models import User, Company, Lead, Customer, Product, Quotation, Invoice, Task, Activity
from app.utils import log_audit, format_currency, format_date
from sqlalchemy import func, desc
from datetime import datetime, timedelta
import jwt
from functools import wraps

api_bp = Blueprint('api', __name__)

# API Authentication decorator
def api_auth_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'error': 'Missing authorization token'}), 401
        
        try:
            # Remove 'Bearer ' prefix if present
            if token.startswith('Bearer '):
                token = token[7:]
            
            # Decode JWT token
            payload = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])
            user_id = payload.get('user_id')
            company_id = payload.get('company_id')
            
            if not user_id or not company_id:
                return jsonify({'error': 'Invalid token'}), 401
            
            # Get user and verify company access
            user = User.query.filter_by(id=user_id, company_id=company_id).first()
            if not user or not user.is_active:
                return jsonify({'error': 'Invalid or inactive user'}), 401
            
            # Add user and company to request context
            request.current_user = user
            request.current_company = user.company
            
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid token'}), 401
        
        return f(*args, **kwargs)
    return decorated_function

# Authentication endpoints
@api_bp.route('/auth/login', methods=['POST'])
def api_login():
    """API login endpoint"""
    data = request.get_json()
    
    if not data or not data.get('email') or not data.get('password'):
        return jsonify({'error': 'Email and password required'}), 400
    
    user = User.query.filter_by(email=data['email']).first()
    
    if not user or not user.check_password(data['password']):
        return jsonify({'error': 'Invalid credentials'}), 401
    
    if not user.is_active:
        return jsonify({'error': 'Account deactivated'}), 401
    
    # Generate JWT token
    token = jwt.encode({
        'user_id': user.id,
        'company_id': user.company_id,
        'email': user.email,
        'role': user.role.value,
        'exp': datetime.utcnow() + timedelta(days=1)
    }, current_app.config['SECRET_KEY'], algorithm='HS256')
    
    # Log audit
    log_audit(user.company_id, user.id, 'api_login', 'API login successful')
    
    return jsonify({
        'token': token,
        'user': {
            'id': user.id,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'role': user.role.value,
            'company': {
                'id': user.company.id,
                'name': user.company.name,
                'subdomain': user.company.subdomain
            }
        }
    })

@api_bp.route('/auth/refresh', methods=['POST'])
@api_auth_required
def api_refresh_token():
    """Refresh API token"""
    user = request.current_user
    
    # Generate new JWT token
    token = jwt.encode({
        'user_id': user.id,
        'company_id': user.company_id,
        'email': user.email,
        'role': user.role.value,
        'exp': datetime.utcnow() + timedelta(days=1)
    }, current_app.config['SECRET_KEY'], algorithm='HS256')
    
    return jsonify({'token': token})

# Lead endpoints
@api_bp.route('/leads', methods=['GET'])
@api_auth_required
def api_get_leads():
    """Get leads list"""
    company = request.current_company
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)
    
    # Get filter parameters
    status_filter = request.args.get('status', '')
    source_filter = request.args.get('source', '')
    assigned_filter = request.args.get('assigned_to', '')
    search_query = request.args.get('search', '')
    
    query = Lead.query.filter_by(company_id=company.id)
    
    if status_filter:
        query = query.filter(Lead.status == status_filter)
    if source_filter:
        query = query.filter(Lead.source == source_filter)
    if assigned_filter:
        query = query.filter(Lead.assigned_to_id == assigned_filter)
    if search_query:
        query = query.filter(
            (Lead.first_name.ilike(f'%{search_query}%') |
             Lead.last_name.ilike(f'%{search_query}%') |
             Lead.email.ilike(f'%{search_query}%') |
             Lead.company_name.ilike(f'%{search_query}%'))
        )
    
    leads = query.order_by(desc(Lead.created_at)).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return jsonify({
        'leads': [{
            'id': lead.id,
            'first_name': lead.first_name,
            'last_name': lead.last_name,
            'email': lead.email,
            'phone': lead.phone,
            'company_name': lead.company_name,
            'job_title': lead.job_title,
            'industry': lead.industry,
            'source': lead.source,
            'status': lead.status.value,
            'estimated_value': float(lead.estimated_value) if lead.estimated_value else None,
            'notes': lead.notes,
            'next_follow_up': lead.next_follow_up.isoformat() if lead.next_follow_up else None,
            'assigned_to': {
                'id': lead.assigned_to.id,
                'name': lead.assigned_to.get_full_name()
            } if lead.assigned_to else None,
            'created_at': lead.created_at.isoformat(),
            'updated_at': lead.updated_at.isoformat()
        } for lead in leads.items],
        'pagination': {
            'page': leads.page,
            'pages': leads.pages,
            'per_page': leads.per_page,
            'total': leads.total,
            'has_next': leads.has_next,
            'has_prev': leads.has_prev
        }
    })

@api_bp.route('/leads', methods=['POST'])
@api_auth_required
def api_create_lead():
    """Create new lead"""
    company = request.current_company
    user = request.current_user
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    # Validate required fields
    required_fields = ['first_name', 'last_name', 'email', 'source']
    for field in required_fields:
        if not data.get(field):
            return jsonify({'error': f'{field} is required'}), 400
    
    # Create lead
    lead = Lead(
        company_id=company.id,
        assigned_to_id=user.id,
        first_name=data['first_name'],
        last_name=data['last_name'],
        email=data['email'],
        phone=data.get('phone'),
        company_name=data.get('company_name'),
        job_title=data.get('job_title'),
        industry=data.get('industry'),
        source=data['source'],
        estimated_value=data.get('estimated_value'),
        notes=data.get('notes'),
        next_follow_up=datetime.fromisoformat(data['next_follow_up']) if data.get('next_follow_up') else None
    )
    
    db.session.add(lead)
    db.session.commit()
    
    # Log audit
    log_audit(company.id, user.id, 'api_lead_created', 
             f'Created lead via API: {lead.get_full_name()}', 'lead', lead.id)
    
    return jsonify({
        'message': 'Lead created successfully',
        'lead_id': lead.id
    }), 201

@api_bp.route('/leads/<int:lead_id>', methods=['GET'])
@api_auth_required
def api_get_lead(lead_id):
    """Get lead details"""
    company = request.current_company
    
    lead = Lead.query.filter_by(
        id=lead_id, company_id=company.id
    ).first()
    
    if not lead:
        return jsonify({'error': 'Lead not found'}), 404
    
    return jsonify({
        'id': lead.id,
        'first_name': lead.first_name,
        'last_name': lead.last_name,
        'email': lead.email,
        'phone': lead.phone,
        'company_name': lead.company_name,
        'job_title': lead.job_title,
        'industry': lead.industry,
        'source': lead.source,
        'status': lead.status.value,
        'estimated_value': float(lead.estimated_value) if lead.estimated_value else None,
        'notes': lead.notes,
        'next_follow_up': lead.next_follow_up.isoformat() if lead.next_follow_up else None,
        'assigned_to': {
            'id': lead.assigned_to.id,
            'name': lead.assigned_to.get_full_name()
        } if lead.assigned_to else None,
        'created_at': lead.created_at.isoformat(),
        'updated_at': lead.updated_at.isoformat()
    })

@api_bp.route('/leads/<int:lead_id>', methods=['PUT'])
@api_auth_required
def api_update_lead(lead_id):
    """Update lead"""
    company = request.current_company
    user = request.current_user
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    lead = Lead.query.filter_by(
        id=lead_id, company_id=company.id
    ).first()
    
    if not lead:
        return jsonify({'error': 'Lead not found'}), 404
    
    # Update fields
    if 'first_name' in data:
        lead.first_name = data['first_name']
    if 'last_name' in data:
        lead.last_name = data['last_name']
    if 'email' in data:
        lead.email = data['email']
    if 'phone' in data:
        lead.phone = data['phone']
    if 'company_name' in data:
        lead.company_name = data['company_name']
    if 'job_title' in data:
        lead.job_title = data['job_title']
    if 'industry' in data:
        lead.industry = data['industry']
    if 'source' in data:
        lead.source = data['source']
    if 'status' in data:
        lead.status = data['status']
    if 'estimated_value' in data:
        lead.estimated_value = data['estimated_value']
    if 'notes' in data:
        lead.notes = data['notes']
    if 'next_follow_up' in data:
        lead.next_follow_up = datetime.fromisoformat(data['next_follow_up']) if data['next_follow_up'] else None
    
    db.session.commit()
    
    # Log audit
    log_audit(company.id, user.id, 'api_lead_updated', 
             f'Updated lead via API: {lead.get_full_name()}', 'lead', lead.id)
    
    return jsonify({'message': 'Lead updated successfully'})

@api_bp.route('/leads/<int:lead_id>/status', methods=['PATCH'])
@api_auth_required
def api_update_lead_status(lead_id):
    """Update lead status"""
    company = request.current_company
    user = request.current_user
    data = request.get_json()
    
    if not data or 'status' not in data:
        return jsonify({'error': 'Status is required'}), 400
    
    lead = Lead.query.filter_by(
        id=lead_id, company_id=company.id
    ).first()
    
    if not lead:
        return jsonify({'error': 'Lead not found'}), 404
    
    # Update status
    lead.status = data['status']
    db.session.commit()
    
    # Log audit
    log_audit(company.id, user.id, 'api_lead_status_updated', 
             f'Updated lead status via API: {data["status"]}', 'lead', lead.id)
    
    return jsonify({'message': 'Lead status updated successfully'})

# Customer endpoints
@api_bp.route('/customers', methods=['GET'])
@api_auth_required
def api_get_customers():
    """Get customers list"""
    company = request.current_company
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)
    
    search_query = request.args.get('search', '')
    
    query = Customer.query.filter_by(company_id=company.id)
    
    if search_query:
        query = query.filter(
            (Customer.first_name.ilike(f'%{search_query}%') |
             Customer.last_name.ilike(f'%{search_query}%') |
             Customer.email.ilike(f'%{search_query}%') |
             Customer.company_name.ilike(f'%{search_query}%'))
        )
    
    customers = query.order_by(desc(Customer.created_at)).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return jsonify({
        'customers': [{
            'id': customer.id,
            'first_name': customer.first_name,
            'last_name': customer.last_name,
            'email': customer.email,
            'phone': customer.phone,
            'company_name': customer.company_name,
            'address': customer.address,
            'tax_id': customer.tax_id,
            'credit_limit': float(customer.credit_limit) if customer.credit_limit else None,
            'payment_terms': customer.payment_terms,
            'created_at': customer.created_at.isoformat(),
            'updated_at': customer.updated_at.isoformat()
        } for customer in customers.items],
        'pagination': {
            'page': customers.page,
            'pages': customers.pages,
            'per_page': customers.per_page,
            'total': customers.total,
            'has_next': customers.has_next,
            'has_prev': customers.has_prev
        }
    })

@api_bp.route('/customers', methods=['POST'])
@api_auth_required
def api_create_customer():
    """Create new customer"""
    company = request.current_company
    user = request.current_user
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    # Validate required fields
    required_fields = ['first_name', 'last_name', 'email']
    for field in required_fields:
        if not data.get(field):
            return jsonify({'error': f'{field} is required'}), 400
    
    # Create customer
    customer = Customer(
        company_id=company.id,
        first_name=data['first_name'],
        last_name=data['last_name'],
        email=data['email'],
        phone=data.get('phone'),
        company_name=data.get('company_name'),
        address=data.get('address'),
        tax_id=data.get('tax_id'),
        credit_limit=data.get('credit_limit'),
        payment_terms=data.get('payment_terms')
    )
    
    db.session.add(customer)
    db.session.commit()
    
    # Log audit
    log_audit(company.id, user.id, 'api_customer_created', 
             f'Created customer via API: {customer.get_full_name()}', 'customer', customer.id)
    
    return jsonify({
        'message': 'Customer created successfully',
        'customer_id': customer.id
    }), 201

# Product endpoints
@api_bp.route('/products', methods=['GET'])
@api_auth_required
def api_get_products():
    """Get products list"""
    company = request.current_company
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)
    
    search_query = request.args.get('search', '')
    category_filter = request.args.get('category', '')
    
    query = Product.query.filter_by(company_id=company.id)
    
    if search_query:
        query = query.filter(
            (Product.name.ilike(f'%{search_query}%') |
             Product.description.ilike(f'%{search_query}%') |
             Product.sku.ilike(f'%{search_query}%'))
        )
    
    if category_filter:
        query = query.filter(Product.category == category_filter)
    
    products = query.order_by(Product.name).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return jsonify({
        'products': [{
            'id': product.id,
            'name': product.name,
            'description': product.description,
            'sku': product.sku,
            'category': product.category,
            'unit_price': float(product.unit_price),
            'cost_price': float(product.cost_price) if product.cost_price else None,
            'tax_rate': float(product.tax_rate) if product.tax_rate else None,
            'is_active': product.is_active,
            'created_at': product.created_at.isoformat(),
            'updated_at': product.updated_at.isoformat()
        } for product in products.items],
        'pagination': {
            'page': products.page,
            'pages': products.pages,
            'per_page': products.per_page,
            'total': products.total,
            'has_next': products.has_next,
            'has_prev': products.has_prev
        }
    })

# Dashboard statistics
@api_bp.route('/dashboard/stats', methods=['GET'])
@api_auth_required
def api_dashboard_stats():
    """Get dashboard statistics"""
    company = request.current_company
    
    # Get basic stats
    stats = {
        'total_leads': Lead.query.filter_by(company_id=company.id).count(),
        'total_customers': Customer.query.filter_by(company_id=company.id).count(),
        'total_products': Product.query.filter_by(company_id=company.id).count(),
        'total_quotations': Quotation.query.filter_by(company_id=company.id).count(),
        'total_invoices': Invoice.query.filter_by(company_id=company.id).count()
    }
    
    # Get lead status distribution
    lead_statuses = db.session.query(
        Lead.status, func.count(Lead.id)
    ).filter_by(company_id=company.id).group_by(Lead.status).all()
    
    stats['lead_statuses'] = {
        status.value: count for status, count in lead_statuses
    }
    
    # Get recent activities
    recent_activities = Activity.query.filter_by(
        company_id=company.id
    ).order_by(desc(Activity.created_at)).limit(10).all()
    
    stats['recent_activities'] = [{
        'id': activity.id,
        'type': activity.activity_type,
        'subject': activity.subject,
        'description': activity.description,
        'user': {
            'id': activity.user.id,
            'name': activity.user.get_full_name()
        },
        'created_at': activity.created_at.isoformat()
    } for activity in recent_activities]
    
    return jsonify(stats)

# Error handlers
@api_bp.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Resource not found'}), 404

@api_bp.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

@api_bp.errorhandler(400)
def bad_request(error):
    return jsonify({'error': 'Bad request'}), 400

@api_bp.errorhandler(401)
def unauthorized(error):
    return jsonify({'error': 'Unauthorized'}), 401

@api_bp.errorhandler(403)
def forbidden(error):
    return jsonify({'error': 'Forbidden'}), 403
