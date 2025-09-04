from flask import Blueprint, render_template, request, redirect, url_for, flash, g, jsonify
from flask_login import login_required, current_user
from app.extensions import db
from app.models import Lead, Customer, Quotation, Invoice, Task, Activity, User, Company
from app.utils import log_audit, format_currency, format_date, cache_data, get_cached_data
from sqlalchemy import func, desc
from datetime import datetime, timedelta
import json

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    """Landing page for the SaaS platform"""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    # Show pricing plans
    plans = [
        {
            'name': 'Starter',
            'price': 29,
            'currency': 'USD',
            'period': 'month',
            'features': [
                'Up to 5 users',
                '100 leads',
                'Basic reporting',
                'Email support',
                '10GB storage'
            ],
            'popular': False
        },
        {
            'name': 'Pro',
            'price': 79,
            'currency': 'USD',
            'period': 'month',
            'features': [
                'Up to 20 users',
                'Unlimited leads',
                'Advanced reporting',
                'Priority support',
                '100GB storage',
                'WhatsApp integration',
                'Custom branding'
            ],
            'popular': True
        },
        {
            'name': 'Enterprise',
            'price': 199,
            'currency': 'USD',
            'period': 'month',
            'features': [
                'Unlimited users',
                'Unlimited everything',
                'Custom integrations',
                'Dedicated support',
                'Unlimited storage',
                'API access',
                'White-label solution'
            ],
            'popular': False
        }
    ]
    
    return render_template('main/landing.html', plans=plans, title='Sales ERP - Multi-Enterprise SaaS')

@main_bp.route('/register', methods=['GET', 'POST'])
def company_register():
    """Company registration page"""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    if request.method == 'POST':
        try:
            # Get form data
            company_name = request.form.get('company_name')
            company_website = request.form.get('company_website')
            company_phone = request.form.get('company_phone')
            company_size = request.form.get('company_size')
            company_address = request.form.get('company_address')
            company_city = request.form.get('company_city')
            company_state = request.form.get('company_state')
            company_zip = request.form.get('company_zip')
            company_country = request.form.get('company_country')
            company_industry = request.form.get('company_industry')
            
            # User data
            first_name = request.form.get('first_name')
            last_name = request.form.get('last_name')
            email = request.form.get('email')
            phone = request.form.get('phone')
            password = request.form.get('password')
            confirm_password = request.form.get('confirm_password')
            
            # Validation
            if not all([company_name, first_name, last_name, email, password, confirm_password]):
                return jsonify({
                    'success': False,
                    'message': 'Please fill in all required fields.'
                }), 400
            
            if password != confirm_password:
                return jsonify({
                    'success': False,
                    'message': 'Passwords do not match.'
                }), 400
            
            if len(password) < 8:
                return jsonify({
                    'success': False,
                    'message': 'Password must be at least 8 characters long.'
                }), 400
            
            # Check if email already exists
            if User.query.filter_by(email=email).first():
                return jsonify({
                    'success': False,
                    'message': 'Email already registered.'
                }), 400
            
            # Generate subdomain from company name
            import re
            subdomain = re.sub(r'[^a-zA-Z0-9]', '', company_name.lower())
            if len(subdomain) > 20:
                subdomain = subdomain[:20]
            
            # Check if subdomain is available
            counter = 1
            original_subdomain = subdomain
            while Company.query.filter_by(subdomain=subdomain).first():
                subdomain = f"{original_subdomain}{counter}"
                counter += 1
            
            # Create company
            company = Company(
                name=company_name,
                subdomain=subdomain,
                website=company_website,
                phone=company_phone,
                address=company_address,
                city=company_city,
                state=company_state,
                zip_code=company_zip,
                country=company_country,
                industry=company_industry,
                size=company_size,
                is_active=True
            )
            db.session.add(company)
            db.session.flush()  # Get company ID
            
            # Create admin user
            from app.models import UserRole
            user = User(
                company_id=company.id,
                email=email,
                username=email.split('@')[0],  # Use email prefix as username
                first_name=first_name,
                last_name=last_name,
                phone=phone,
                role=UserRole.ADMIN,
                is_active=True
            )
            user.set_password(password)
            
            db.session.add(user)
            db.session.commit()
            
            # Log audit
            from app.utils import log_audit
            log_audit(company.id, user.id, 'company_registration', f'New company registered: {company_name}')
            
            # Return JSON response for AJAX requests
            return jsonify({
                'success': True,
                'message': f'Company "{company_name}" registered successfully!',
                'redirect_url': url_for('auth.login')
            })
            
        except Exception as e:
            db.session.rollback()
            # Return JSON error response for AJAX requests
            return jsonify({
                'success': False,
                'message': f'Registration failed: {str(e)}'
            }), 400
    
    return render_template('auth/register.html', title='Company Registration')

@main_bp.route('/dashboard')
@login_required
def dashboard():
    """Main dashboard for authenticated users"""
    company = current_user.company
    
    # Get cached dashboard data or calculate fresh
    cache_key = f"dashboard_{company.id}_{current_user.id}"
    dashboard_data = get_cached_data(cache_key)
    
    # If cached data is not a dict, clear cache and recalculate
    if dashboard_data is not None and not isinstance(dashboard_data, dict):
        from app.utils import clear_cache
        clear_cache(cache_key)
        dashboard_data = None
    
    if not dashboard_data:
        # Calculate dashboard metrics
        total_leads = Lead.query.filter_by(company_id=company.id).count()
        total_customers = Customer.query.filter_by(company_id=company.id).count()
        total_quotations = Quotation.query.filter_by(company_id=company.id).count()
        total_invoices = Invoice.query.filter_by(company_id=company.id).count()
        
        # Calculate total revenue
        total_revenue = db.session.query(func.sum(Invoice.total_amount)).filter(
            Invoice.company_id == company.id,
            Invoice.status == 'paid'
        ).scalar() or 0
        
        # Ensure total_revenue is a valid number
        try:
            total_revenue = float(total_revenue) if total_revenue is not None else 0.0
        except (ValueError, TypeError):
            total_revenue = 0.0
        
        # Calculate conversion rate (leads to customers)
        conversion_rate = 0
        if total_leads > 0:
            conversion_rate = round((total_customers / total_leads) * 100, 1)
        
        # Lead status distribution
        lead_statuses = db.session.query(
            Lead.status, func.count(Lead.id)
        ).filter_by(company_id=company.id).group_by(Lead.status).all()
        
        # Monthly revenue trend (last 6 months)
        monthly_revenue = []
        for i in range(6):
            date = datetime.utcnow() - timedelta(days=30*i)
            month_start = date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            month_end = month_start.replace(day=28) + timedelta(days=4)
            month_end = month_end.replace(day=1) - timedelta(seconds=1)
            
            revenue = db.session.query(func.sum(Invoice.total_amount)).filter(
                Invoice.company_id == company.id,
                Invoice.created_at >= month_start,
                Invoice.created_at <= month_end,
                Invoice.status == 'paid'
            ).scalar() or 0
            
            monthly_revenue.append({
                'month': month_start.strftime('%b %Y'),
                'revenue': float(revenue)
            })
        
        # Recent activities
        recent_activities = Activity.query.filter_by(
            company_id=company.id
        ).order_by(desc(Activity.created_at)).limit(10).all()
        
        # Recent leads
        recent_leads = Lead.query.filter_by(
            company_id=company.id
        ).order_by(desc(Lead.created_at)).limit(5).all()
        
        # Pipeline stats from lead statuses
        pipeline_stats = {}
        for status, count in lead_statuses:
            if status.value == 'prospect':
                pipeline_stats['prospect'] = count
            elif status.value == 'qualified':
                pipeline_stats['qualified'] = count
            elif status.value == 'proposal':
                pipeline_stats['proposal'] = count
            elif status.value == 'closed_won':
                pipeline_stats['closed_won'] = count
        
        # Set default values for missing statuses
        pipeline_stats.setdefault('prospect', 0)
        pipeline_stats.setdefault('qualified', 0)
        pipeline_stats.setdefault('proposal', 0)
        pipeline_stats.setdefault('closed_won', 0)
        
        # Upcoming tasks
        upcoming_tasks = Task.query.filter(
            Task.company_id == company.id,
            Task.status.in_(['pending', 'in_progress']),
            Task.due_date >= datetime.utcnow()
        ).order_by(Task.due_date).limit(5).all()
        
        # Top performing users
        top_users = db.session.query(
            User.id, User.first_name, User.last_name,
            func.count(Lead.id).label('leads_assigned'),
            func.count(Customer.id).label('customers_converted')
        ).outerjoin(Lead, User.id == Lead.assigned_to_id).outerjoin(
            Customer, User.id == Customer.id
        ).filter(User.company_id == company.id).group_by(
            User.id, User.first_name, User.last_name
        ).order_by(desc(func.count(Lead.id))).limit(5).all()
        
        dashboard_data = {
            'total_leads': total_leads,
            'total_customers': total_customers,
            'total_quotations': total_quotations,
            'total_invoices': total_invoices,
            'total_revenue': total_revenue,
            'conversion_rate': conversion_rate,
            'lead_statuses': lead_statuses,
            'monthly_revenue': monthly_revenue,
            'recent_activities': recent_activities,
            'recent_leads': recent_leads,
            'pipeline_stats': pipeline_stats,
            'upcoming_tasks': upcoming_tasks,
            'top_users': top_users
        }
        
        # Cache for 5 minutes
        cache_data(cache_key, dashboard_data, 300)
    
    return render_template('main/dashboard.html', 
                         dashboard_data=dashboard_data,
                         company=company,
                         title='Dashboard')

@main_bp.route('/profile')
@login_required
def profile():
    """User profile page"""
    return redirect(url_for('auth.profile'))

@main_bp.route('/settings')
@login_required
def settings():
    """Company settings page"""
    if current_user.role not in ['admin', 'manager']:
        flash('You do not have permission to access settings.', 'error')
        return redirect(url_for('main.dashboard'))
    
    company = current_user.company
    return render_template('main/settings.html', company=company, title='Settings')

@main_bp.route('/help')
def help():
    """Help and documentation page"""
    return render_template('main/help.html', title='Help & Documentation')

@main_bp.route('/contact')
def contact():
    """Contact support page"""
    return render_template('main/contact.html', title='Contact Support')

@main_bp.route('/api/dashboard-stats')
@login_required
def dashboard_stats():
    """API endpoint for dashboard statistics (for AJAX updates)"""
    company = current_user.company
    
    # Real-time stats
    total_leads = Lead.query.filter_by(company_id=company.id).count()
    total_customers = Customer.query.filter_by(company_id=company.id).count()
    
    # Today's activities
    today = datetime.utcnow().date()
    today_leads = Lead.query.filter(
        Lead.company_id == company.id,
        func.date(Lead.created_at) == today
    ).count()
    
    today_activities = Activity.query.filter(
        Activity.company_id == company.id,
        func.date(Activity.created_at) == today
    ).count()
    
    # Pending tasks
    pending_tasks = Task.query.filter(
        Task.company_id == company.id,
        Task.status.in_(['pending', 'in_progress'])
    ).count()
    
    stats = {
        'total_leads': total_leads,
        'total_customers': total_customers,
        'today_leads': today_leads,
        'today_activities': today_activities,
        'pending_tasks': pending_tasks,
        'last_updated': datetime.utcnow().isoformat()
    }
    
    return jsonify(stats)

@main_bp.route('/api/lead-chart-data')
@login_required
def lead_chart_data():
    """API endpoint for lead chart data"""
    company = current_user.company
    
    # Get lead status distribution for chart
    lead_statuses = db.session.query(
        Lead.status, func.count(Lead.id)
    ).filter_by(company_id=company.id).group_by(Lead.status).all()
    
    chart_data = {
        'labels': [status.value.replace('_', ' ').title() for status, _ in lead_statuses],
        'data': [count for _, count in lead_statuses],
        'colors': [
            '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0',
            '#9966FF', '#FF9F40', '#FF6384'
        ]
    }
    
    return jsonify(chart_data)

@main_bp.route('/api/revenue-chart-data')
@login_required
def revenue_chart_data():
    """API endpoint for revenue chart data"""
    company = current_user.company
    
    # Get monthly revenue for last 12 months
    monthly_revenue = []
    for i in range(12):
        date = datetime.utcnow() - timedelta(days=30*i)
        month_start = date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        month_end = month_start.replace(day=28) + timedelta(days=4)
        month_end = month_end.replace(day=1) - timedelta(seconds=1)
        
        revenue = db.session.query(func.sum(Invoice.total_amount)).filter(
            Invoice.company_id == company.id,
            Invoice.created_at >= month_start,
            Invoice.created_at <= month_end,
            Invoice.status == 'paid'
        ).scalar() or 0
        
        monthly_revenue.append({
            'month': month_start.strftime('%b %Y'),
            'revenue': float(revenue)
        })
    
    # Reverse to show oldest to newest
    monthly_revenue.reverse()
    
    chart_data = {
        'labels': [item['month'] for item in monthly_revenue],
        'data': [item['revenue'] for item in monthly_revenue]
    }
    
    return jsonify(chart_data)

@main_bp.route('/search')
@login_required
def search():
    """Global search functionality"""
    query = request.args.get('q', '').strip()
    if not query:
        return redirect(url_for('main.dashboard'))
    
    company = current_user.company
    
    # Search in leads
    leads = Lead.query.filter(
        Lead.company_id == company.id,
        (Lead.first_name.ilike(f'%{query}%') |
         Lead.last_name.ilike(f'%{query}%') |
         Lead.email.ilike(f'%{query}%') |
         Lead.company_name.ilike(f'%{query}%'))
    ).limit(10).all()
    
    # Search in customers
    customers = Customer.query.filter(
        Customer.company_id == company.id,
        (Customer.first_name.ilike(f'%{query}%') |
         Customer.last_name.ilike(f'%{query}%') |
         Customer.email.ilike(f'%{query}%') |
         Customer.company_name.ilike(f'%{query}%'))
    ).limit(10).all()
    
    # Search in products
    products = Product.query.filter(
        Product.company_id == company.id,
        (Product.name.ilike(f'%{query}%') |
         Product.description.ilike(f'%{query}%') |
         Product.sku.ilike(f'%{query}%'))
    ).limit(10).all()
    
    # Search in quotations
    quotations = Quotation.query.filter(
        Quotation.company_id == company.id,
        (Quotation.subject.ilike(f'%{query}%') |
         Quotation.quotation_number.ilike(f'%{query}%'))
    ).limit(10).all()
    
    # Search in invoices
    invoices = Invoice.query.filter(
        Invoice.company_id == company.id,
        (Invoice.subject.ilike(f'%{query}%') |
         Invoice.invoice_number.ilike(f'%{query}%'))
    ).limit(10).all()
    
    results = {
        'leads': leads,
        'customers': customers,
        'products': products,
        'quotations': quotations,
        'invoices': invoices,
        'query': query
    }
    
    return render_template('main/search_results.html', results=results, title=f'Search: {query}')

@main_bp.route('/notifications')
@login_required
def notifications():
    """User notifications page"""
    # Get user's notifications (implement notification system)
    notifications = []  # Placeholder for notification system
    
    return render_template('main/notifications.html', 
                         notifications=notifications,
                         title='Notifications')

@main_bp.route('/api/mark-notification-read/<int:notification_id>')
@login_required
def mark_notification_read(notification_id):
    """Mark notification as read"""
    # Implement notification marking logic
    return jsonify({'success': True})

@main_bp.route('/api/clear-all-notifications')
@login_required
def clear_all_notifications():
    """Clear all notifications"""
    # Implement clear all notifications logic
    return jsonify({'success': True})
