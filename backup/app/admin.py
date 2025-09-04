from flask import Blueprint, render_template, request, redirect, url_for, flash, g, jsonify, current_app
from flask_login import login_required, current_user
from app.extensions import db
from app.models import User, Company, UserRole, Lead, Customer, Product, Quotation, Invoice, Task, Activity, AuditLog
from app.forms import UserInviteForm, CompanyForm
from app.utils import log_audit, send_email
from sqlalchemy import func, desc
from datetime import datetime, timedelta
import os

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/')
@login_required
def admin_dashboard():
    """Admin dashboard"""
    if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER]:
        flash('You do not have permission to access admin area.', 'error')
        return redirect(url_for('main.dashboard'))
    
    company = current_user.company
    
    # Get company statistics
    stats = {
        'total_users': User.query.filter_by(company_id=company.id).count(),
        'total_leads': Lead.query.filter_by(company_id=company.id).count(),
        'total_customers': Customer.query.filter_by(company_id=company.id).count(),
        'total_products': Product.query.filter_by(company_id=company.id).count(),
        'total_quotations': Quotation.query.filter_by(company_id=company.id).count(),
        'total_invoices': Invoice.query.filter_by(company_id=company.id).count(),
        'total_tasks': Task.query.filter_by(company_id=company.id).count()
    }
    
    # Calculate monthly revenue
    current_month = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    monthly_revenue = db.session.query(func.sum(Invoice.total_amount)).filter(
        Invoice.company_id == company.id,
        Invoice.created_at >= current_month,
        Invoice.status == 'paid'
    ).scalar() or 0
    
    stats['monthly_revenue'] = float(monthly_revenue)
    
    # Get recent activities
    recent_activities = AuditLog.query.filter_by(
        company_id=company.id
    ).order_by(desc(AuditLog.created_at)).limit(20).all()
    
    # Get user activity summary
    user_activity = db.session.query(
        User.id, User.first_name, User.last_name,
        func.count(Activity.id).label('activity_count')
    ).outerjoin(Activity, User.id == Activity.user_id).filter(
        User.company_id == company.id
    ).group_by(User.id, User.first_name, User.last_name).order_by(
        desc(func.count(Activity.id))
    ).limit(10).all()
    
    # System metrics (mock data for demo purposes)
    import psutil
    try:
        metrics = {
            'cpu_usage': round(psutil.cpu_percent(interval=1), 1),
            'memory_usage': round(psutil.virtual_memory().percent, 1),
            'disk_usage': round(psutil.disk_usage('/').percent, 1),
            'network_io': round(psutil.net_io_counters().bytes_sent / 1024 / 1024, 1)  # MB/s
        }
    except (ImportError, AttributeError):
        # Fallback mock data if psutil is not available
        metrics = {
            'cpu_usage': 45.2,
            'memory_usage': 67.8,
            'disk_usage': 23.4,
            'network_io': 12.5
        }
    
    # Company subscription statistics
    from app.models import SubscriptionPlan
    company_stats = {
        'starter_plan': Company.query.filter_by(subscription_plan=SubscriptionPlan.STARTER).count(),
        'pro_plan': Company.query.filter_by(subscription_plan=SubscriptionPlan.PRO).count(),
        'enterprise_plan': Company.query.filter_by(subscription_plan=SubscriptionPlan.ENTERPRISE).count(),
        'trial_companies': Company.query.filter_by(subscription_plan=None).count()  # Companies without subscription
    }
    
    return render_template('admin/dashboard.html',
                         stats=stats,
                         recent_activities=recent_activities,
                         user_activity=user_activity,
                         metrics=metrics,
                         company_stats=company_stats,
                         company=company,
                         title='Admin Dashboard')

@admin_bp.route('/users')
@login_required
def users():
    """User management"""
    if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER]:
        flash('You do not have permission to access user management.', 'error')
        return redirect(url_for('main.dashboard'))
    
    company = current_user.company
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    search_query = request.args.get('search', '')
    role_filter = request.args.get('role', '')
    status_filter = request.args.get('status', '')
    
    query = User.query.filter_by(company_id=company.id)
    
    if search_query:
        query = query.filter(
            (User.first_name.ilike(f'%{search_query}%') |
             User.last_name.ilike(f'%{search_query}%') |
             User.email.ilike(f'%{search_query}%') |
             User.username.ilike(f'%{search_query}%'))
        )
    
    if role_filter:
        query = query.filter(User.role == role_filter)
    
    if status_filter:
        if status_filter == 'active':
            query = query.filter(User.is_active == True)
        elif status_filter == 'inactive':
            query = query.filter(User.is_active == False)
    
    users = query.order_by(User.created_at).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return render_template('admin/users.html',
                         users=users,
                         title='User Management')

@admin_bp.route('/users/new', methods=['GET', 'POST'])
@login_required
def new_user():
    """Create new user"""
    if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER]:
        flash('You do not have permission to create users.', 'error')
        return redirect(url_for('admin.users'))
    
    form = UserInviteForm()
    
    if form.validate_on_submit():
        # Check if user already exists
        if User.query.filter_by(email=form.email.data).first():
            flash('User with this email already exists.', 'error')
            return redirect(url_for('admin.new_user'))
        
        if User.query.filter_by(username=form.username.data).first():
            flash('Username already taken.', 'error')
            return redirect(url_for('admin.new_user'))
        
        # Generate temporary password
        import secrets
        import string
        temp_password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(12))
        
        # Create user
        user = User(
            company_id=current_user.company.id,
            email=form.email.data,
            username=form.username.data,
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            role=form.role.data
        )
        user.set_password(temp_password)
        
        db.session.add(user)
        db.session.commit()
        
        # Send invitation email
        invite_url = f"https://{current_user.company.subdomain}.{os.environ.get('DOMAIN', 'example.com')}/auth/login"
        
        email_content = f"""
        Hello {user.first_name},
        
        You have been invited to join {current_user.company.name} on our Sales ERP platform.
        
        Your login credentials:
        Username: {user.username}
        Password: {temp_password}
        
        Please login at: {invite_url}
        
        Please change your password after first login.
        
        Best regards,
        {current_user.company.name} Team
        """
        
        try:
            send_email(
                subject=f"Invitation to join {current_user.company.name}",
                recipients=[user.email],
                body=email_content
            )
            flash(f'User {user.email} has been invited successfully.', 'success')
        except Exception as e:
            flash(f'User created but invitation email failed: {str(e)}', 'warning')
        
        # Log audit
        log_audit(current_user.company.id, current_user.id, 'user_created',
                 f'Created user: {user.email}', 'user', user.id)
        
        return redirect(url_for('admin.users'))
    
    return render_template('admin/user_form.html',
                         form=form,
                         title='New User')

@admin_bp.route('/users/<int:user_id>')
@login_required
def view_user(user_id):
    """View user details"""
    if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER]:
        flash('You do not have permission to view user details.', 'error')
        return redirect(url_for('admin.users'))
    
    user = User.query.filter_by(
        id=user_id, company_id=current_user.company.id
    ).first_or_404()
    
    # Get user statistics
    user_stats = {
        'leads_assigned': Lead.query.filter_by(assigned_to_id=user.id).count(),
        'customers_converted': Customer.query.filter_by(company_id=user.company_id).count(),
        'activities_logged': Activity.query.filter_by(user_id=user.id).count(),
        'tasks_assigned': Task.query.filter_by(assigned_to_id=user.id).count()
    }
    
    # Get recent activities
    recent_activities = Activity.query.filter_by(
        company_id=user.company_id, user_id=user.id
    ).order_by(desc(Activity.created_at)).limit(10).all()
    
    return render_template('admin/user_detail.html',
                         user=user,
                         user_stats=user_stats,
                         recent_activities=recent_activities,
                         title=f'User: {user.get_full_name()}')

@admin_bp.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_user(user_id):
    """Edit user"""
    if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER]:
        flash('You do not have permission to edit users.', 'error')
        return redirect(url_for('admin.users'))
    
    user = User.query.filter_by(
        id=user_id, company_id=current_user.company.id
    ).first_or_404()
    
    if request.method == 'POST':
        # Update user details
        user.first_name = request.form.get('first_name')
        user.last_name = request.form.get('last_name')
        user.email = request.form.get('email')
        user.phone = request.form.get('phone')
        user.role = UserRole(request.form.get('role'))
        user.is_active = request.form.get('is_active') == 'on'
        
        db.session.commit()
        
        # Log audit
        log_audit(current_user.company.id, current_user.id, 'user_updated',
                 f'Updated user: {user.email}', 'user', user.id)
        
        flash('User updated successfully!', 'success')
        return redirect(url_for('admin.view_user', user_id=user.id))
    
    return render_template('admin/user_edit.html',
                         user=user,
                         title=f'Edit User: {user.get_full_name()}')

@admin_bp.route('/users/<int:user_id>/deactivate', methods=['POST'])
@login_required
def deactivate_user(user_id):
    """Deactivate user"""
    if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER]:
        return jsonify({'success': False, 'error': 'Permission denied'})
    
    if current_user.id == user_id:
        return jsonify({'success': False, 'error': 'Cannot deactivate yourself'})
    
    user = User.query.filter_by(
        id=user_id, company_id=current_user.company.id
    ).first_or_404()
    
    user.is_active = False
    db.session.commit()
    
    # Log audit
    log_audit(current_user.company.id, current_user.id, 'user_deactivated',
             f'Deactivated user: {user.email}', 'user', user.id)
    
    return jsonify({'success': True})

@admin_bp.route('/users/<int:user_id>/activate', methods=['POST'])
@login_required
def activate_user(user_id):
    """Activate user"""
    if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER]:
        return jsonify({'success': False, 'error': 'Permission denied'})
    
    user = User.query.filter_by(
        id=user_id, company_id=current_user.company.id
    ).first_or_404()
    
    user.is_active = True
    db.session.commit()
    
    # Log audit
    log_audit(current_user.company.id, current_user.id, 'user_activated',
             f'Activated user: {user.email}', 'user', user.id)
    
    return jsonify({'success': True})

@admin_bp.route('/users/<int:user_id>/reset-password', methods=['POST'])
@login_required
def reset_user_password(user_id):
    """Reset user password"""
    if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER]:
        return jsonify({'success': False, 'error': 'Permission denied'})
    
    user = User.query.filter_by(
        id=user_id, company_id=current_user.company.id
    ).first_or_404()
    
    # Generate new temporary password
    import secrets
    import string
    new_password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(12))
    
    user.set_password(new_password)
    db.session.commit()
    
    # Send password reset email
    email_content = f"""
    Hello {user.first_name},
    
    Your password has been reset by an administrator.
    
        Your new login credentials:
        Username: {user.username}
        Password: {new_password}
        
        Please login and change your password immediately.
        
        Best regards,
        {current_user.company.name} Team
        """
    
    try:
        send_email(
            subject="Password Reset - Sales ERP",
            recipients=[user.email],
            body=email_content
        )
        
        # Log audit
        log_audit(current_user.company.id, current_user.id, 'user_password_reset',
                 f'Reset password for user: {user.email}', 'user', user.id)
        
        return jsonify({'success': True, 'message': 'Password reset and email sent successfully'})
    except Exception as e:
        return jsonify({'success': False, 'error': f'Password reset failed: {str(e)}'})

@admin_bp.route('/company/settings', methods=['GET', 'POST'])
@login_required
def company_settings():
    """Company settings management"""
    if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER]:
        flash('You do not have permission to access company settings.', 'error')
        return redirect(url_for('main.dashboard'))
    
    company = current_user.company
    form = CompanyForm(obj=company)
    
    if form.validate_on_submit():
        # Update company details
        form.populate_obj(company)
        
        # Handle logo upload
        if form.logo.data:
            logo_file = form.logo.data
            if logo_file and allowed_file(logo_file.filename, {'png', 'jpg', 'jpeg', 'gif'}):
                filename = f"logo_{company.id}_{int(datetime.utcnow().timestamp())}.{get_file_extension(logo_file.filename)}"
                logo_path = save_file(logo_file, 'logos', filename)
                if logo_path:
                    company.logo_url = logo_path
        
        db.session.commit()
        
        # Log audit
        log_audit(current_user.company.id, current_user.id, 'company_updated',
                 'Updated company settings', 'company', company.id)
        
        flash('Company settings updated successfully!', 'success')
        return redirect(url_for('admin.company_settings'))
    
    return render_template('admin/company_settings.html',
                         form=form,
                         company=company,
                         title='Company Settings')

@admin_bp.route('/reports')
@login_required
def reports():
    """Reports and analytics"""
    if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER]:
        flash('You do not have permission to access reports.', 'error')
        return redirect(url_for('main.dashboard'))
    
    company = current_user.company
    
    # Get date range for reports
    start_date = request.args.get('start_date', (datetime.utcnow() - timedelta(days=30)).strftime('%Y-%m-%d'))
    end_date = request.args.get('end_date', datetime.utcnow().strftime('%Y-%m-%d'))
    
    # Convert to datetime objects
    start_dt = datetime.strptime(start_date, '%Y-%m-%d')
    end_dt = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
    
    # Lead conversion report
    lead_conversion = db.session.query(
        Lead.status, func.count(Lead.id)
    ).filter(
        Lead.company_id == company.id,
        Lead.created_at >= start_dt,
        Lead.created_at < end_dt
    ).group_by(Lead.status).all()
    
    # Revenue report
    revenue_data = db.session.query(
        func.date(Invoice.created_at).label('date'),
        func.sum(Invoice.total_amount).label('revenue')
    ).filter(
        Invoice.company_id == company.id,
        Invoice.status == 'paid',
        Invoice.created_at >= start_dt,
        Invoice.created_at < end_dt
    ).group_by(func.date(Invoice.created_at)).order_by(
        func.date(Invoice.created_at)
    ).all()
    
    # User performance report
    user_performance = db.session.query(
        User.first_name, User.last_name,
        func.count(Lead.id).label('leads_assigned'),
        func.count(Customer.id).label('customers_converted'),
        func.count(Activity.id).label('activities_logged')
    ).outerjoin(Lead, User.id == Lead.assigned_to_id).outerjoin(
        Customer, User.id == Customer.id
    ).outerjoin(Activity, User.id == Activity.user_id).filter(
        User.company_id == company.id
    ).group_by(User.id, User.first_name, User.last_name).order_by(
        desc(func.count(Lead.id))
    ).all()
    
    return render_template('admin/reports.html',
                         lead_conversion=lead_conversion,
                         revenue_data=revenue_data,
                         user_performance=user_performance,
                         start_date=start_date,
                         end_date=end_date,
                         company=company,
                         title='Reports & Analytics')

@admin_bp.route('/audit-log')
@login_required
def audit_log():
    """Audit log viewer"""
    if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER]:
        flash('You do not have permission to access audit logs.', 'error')
        return redirect(url_for('main.dashboard'))
    
    company = current_user.company
    page = request.args.get('page', 1, type=int)
    per_page = 50
    
    # Get filter parameters
    user_filter = request.args.get('user_id', '')
    action_filter = request.args.get('action', '')
    resource_filter = request.args.get('resource_type', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    
    query = AuditLog.query.filter_by(company_id=company.id)
    
    if user_filter:
        query = query.filter(AuditLog.user_id == user_filter)
    if action_filter:
        query = query.filter(AuditLog.action.ilike(f'%{action_filter}%'))
    if resource_filter:
        query = query.filter(AuditLog.resource_type == resource_filter)
    if date_from:
        query = query.filter(AuditLog.created_at >= datetime.strptime(date_from, '%Y-%m-%d'))
    if date_to:
        query = query.filter(AuditLog.created_at < datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1))
    
    audit_logs = query.order_by(desc(AuditLog.created_at)).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    # Get users for filter
    users = User.query.filter_by(company_id=company.id).all()
    
    return render_template('admin/audit_log.html',
                         audit_logs=audit_logs,
                         users=users,
                         title='Audit Log')

@admin_bp.route('/system-status')
@login_required
def system_status():
    """System status and health check"""
    if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER]:
        flash('You do not have permission to access system status.', 'error')
        return redirect(url_for('main.dashboard'))
    
    company = current_user.company
    
    # Get system statistics
    system_stats = {
        'database_size': get_database_size(),
        'storage_usage': calculate_storage_usage(company.id),
        'active_users': User.query.filter_by(company_id=company.id, is_active=True).count(),
        'total_leads': Lead.query.filter_by(company_id=company.id).count(),
        'total_customers': Customer.query.filter_by(company_id=company.id).count(),
        'pending_tasks': Task.query.filter_by(
            company_id=company.id, status='pending'
        ).count()
    }
    
    # Check system health
    health_checks = {
        'database': check_database_health(),
        'redis': check_redis_health(),
        'email': check_email_health(),
        'storage': check_storage_health()
    }
    
    return render_template('admin/system_status.html',
                         system_stats=system_stats,
                         health_checks=health_checks,
                         company=company,
                         title='System Status')

# Helper functions
def allowed_file(filename, allowed_extensions):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions

def get_file_extension(filename):
    """Get file extension from filename"""
    return filename.rsplit('.', 1)[1].lower() if '.' in filename else ''

def save_file(file, folder, filename):
    """Save uploaded file"""
    try:
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], folder, filename)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        file.save(filepath)
        return filepath
    except Exception as e:
        current_app.logger.error(f"Failed to save file: {str(e)}")
        return None

def get_database_size():
    """Get database size (placeholder)"""
    return "25.6 MB"  # Placeholder

def calculate_storage_usage(company_id):
    """Calculate storage usage for company"""
    return 2.5  # Placeholder: 2.5 GB

def check_database_health():
    """Check database health"""
    try:
        # Simple query to check database connectivity
        db.session.execute('SELECT 1')
        return {'status': 'healthy', 'message': 'Database connection OK'}
    except Exception as e:
        return {'status': 'unhealthy', 'message': f'Database error: {str(e)}'}

def check_redis_health():
    """Check Redis health"""
    try:
        from app.utils import get_redis_client
        redis_client = get_redis_client()
        if redis_client and redis_client.ping():
            return {'status': 'healthy', 'message': 'Redis connection OK'}
        else:
            return {'status': 'unhealthy', 'message': 'Redis connection failed'}
    except Exception as e:
        return {'status': 'unhealthy', 'message': f'Redis error: {str(e)}'}

def check_email_health():
    """Check email service health"""
    try:
        # Test email configuration
        if current_app.config.get('MAIL_USERNAME') and current_app.config.get('MAIL_PASSWORD'):
            return {'status': 'healthy', 'message': 'Email configuration OK'}
        else:
            return {'status': 'warning', 'message': 'Email not configured'}
    except Exception as e:
        return {'status': 'unhealthy', 'message': f'Email error: {str(e)}'}

def check_storage_health():
    """Check storage health"""
    try:
        upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
        if os.path.exists(upload_folder) and os.access(upload_folder, os.W_OK):
            return {'status': 'healthy', 'message': 'Storage access OK'}
        else:
            return {'status': 'unhealthy', 'message': 'Storage access denied'}
    except Exception as e:
        return {'status': 'unhealthy', 'message': f'Storage error: {str(e)}'}
