from flask import Blueprint, render_template, request, redirect, url_for, flash, g, session
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db, login_manager
from app.models import User, Company, UserRole, AuditLog
from app.forms import LoginForm, RegistrationForm, UserInviteForm
from app.utils import send_email, log_audit
import os
from datetime import datetime, timedelta

auth_bp = Blueprint('auth', __name__)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.check_password(form.password.data):
            if not user.is_active:
                flash('Your account has been deactivated. Please contact administrator.', 'error')
                return redirect(url_for('auth.login'))
            
            # Check if user belongs to current tenant
            if g.tenant and user.company.subdomain != g.tenant:
                flash('Access denied. You do not have access to this company.', 'error')
                return redirect(url_for('auth.login'))
            
            login_user(user, remember=form.remember_me.data)
            user.last_login = datetime.utcnow()
            db.session.commit()
            
            # Log audit
            log_audit(user.company_id, user.id, 'user_login', 'User logged in successfully')
            
            next_page = request.args.get('next')
            if not next_page or not next_page.startswith('/'):
                next_page = url_for('main.dashboard')
            return redirect(next_page)
        else:
            flash('Invalid email or password', 'error')
    
    return render_template('auth/login.html', form=form, title='Login')

@auth_bp.route('/logout')
@login_required
def logout():
    if current_user.is_authenticated:
        log_audit(current_user.company_id, current_user.id, 'user_logout', 'User logged out')
    
    logout_user()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('auth.login'))

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        # Check if company exists
        company = Company.query.filter_by(subdomain=g.tenant).first()
        if not company:
            flash('Invalid company subdomain.', 'error')
            return redirect(url_for('auth.register'))
        
        # Check if user already exists
        if User.query.filter_by(email=form.email.data).first():
            flash('Email already registered.', 'error')
            return redirect(url_for('auth.register'))
        
        # Check if username already exists
        if User.query.filter_by(username=form.username.data).first():
            flash('Username already taken.', 'error')
            return redirect(url_for('auth.register'))
        
        # Create user
        user = User(
            company_id=company.id,
            email=form.email.data,
            username=form.username.data,
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            role=UserRole.SALES_EXECUTIVE
        )
        user.set_password(form.password.data)
        
        db.session.add(user)
        db.session.commit()
        
        # Log audit
        log_audit(company.id, user.id, 'user_registration', 'New user registered')
        
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/register.html', form=form, title='Register')

@auth_bp.route('/invite', methods=['GET', 'POST'])
@login_required
def invite_user():
    if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER]:
        flash('You do not have permission to invite users.', 'error')
        return redirect(url_for('main.dashboard'))
    
    form = UserInviteForm()
    if form.validate_on_submit():
        # Check if user already exists
        if User.query.filter_by(email=form.email.data).first():
            flash('User with this email already exists.', 'error')
            return redirect(url_for('auth.invite_user'))
        
        # Generate temporary password
        import secrets
        import string
        temp_password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(12))
        
        # Create user
        user = User(
            company_id=current_user.company_id,
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
        log_audit(current_user.company_id, current_user.id, 'user_invite', f'Invited user: {user.email}')
        
        return redirect(url_for('admin.users'))
    
    return render_template('auth/invite.html', form=form, title='Invite User')

@auth_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        # Update profile
        current_user.first_name = request.form.get('first_name')
        current_user.last_name = request.form.get('last_name')
        current_user.phone = request.form.get('phone')
        
        # Handle password change
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        
        if current_password and new_password:
            if current_user.check_password(current_password):
                current_user.set_password(new_password)
                flash('Password updated successfully.', 'success')
            else:
                flash('Current password is incorrect.', 'error')
                return redirect(url_for('auth.profile'))
        
        db.session.commit()
        flash('Profile updated successfully.', 'success')
        return redirect(url_for('auth.profile'))
    
    return render_template('auth/profile.html', title='Profile')

@auth_bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        if not current_user.check_password(current_password):
            flash('Current password is incorrect.', 'error')
        elif new_password != confirm_password:
            flash('New passwords do not match.', 'error')
        elif len(new_password) < 8:
            flash('Password must be at least 8 characters long.', 'error')
        else:
            current_user.set_password(new_password)
            db.session.commit()
            flash('Password changed successfully.', 'success')
            return redirect(url_for('auth.profile'))
    
    return render_template('auth/change_password.html', title='Change Password')

# Password reset functionality
@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        user = User.query.filter_by(email=email).first()
        
        if user:
            # Generate reset token
            import secrets
            reset_token = secrets.token_urlsafe(32)
            user.reset_token = reset_token
            user.reset_token_expiry = datetime.utcnow() + timedelta(hours=1)
            db.session.commit()
            
            # Send reset email
            reset_url = url_for('auth.reset_password', token=reset_token, _external=True)
            email_content = f"""
            Hello {user.first_name},
            
            You requested a password reset. Click the link below to reset your password:
            
            {reset_url}
            
            This link will expire in 1 hour.
            
            If you didn't request this, please ignore this email.
            
            Best regards,
            Sales ERP Team
            """
            
            try:
                send_email(
                    subject="Password Reset Request",
                    recipients=[user.email],
                    body=email_content
                )
                flash('Password reset instructions have been sent to your email.', 'success')
            except Exception as e:
                flash('Failed to send reset email. Please try again.', 'error')
        else:
            flash('If an account with that email exists, a reset link has been sent.', 'info')
    
    return render_template('auth/forgot_password.html', title='Forgot Password')

@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    user = User.query.filter_by(reset_token=token).first()
    
    if not user or user.reset_token_expiry < datetime.utcnow():
        flash('Invalid or expired reset token.', 'error')
        return redirect(url_for('auth.forgot_password'))
    
    if request.method == 'POST':
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        if new_password != confirm_password:
            flash('Passwords do not match.', 'error')
        elif len(new_password) < 8:
            flash('Password must be at least 8 characters long.', 'error')
        else:
            user.set_password(new_password)
            user.reset_token = None
            user.reset_token_expiry = None
            db.session.commit()
            
            flash('Password has been reset successfully. You can now login.', 'success')
            return redirect(url_for('auth.login'))
    
    return render_template('auth/reset_password.html', title='Reset Password')
