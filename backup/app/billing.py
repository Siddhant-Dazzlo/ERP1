from flask import Blueprint, render_template, request, redirect, url_for, flash, g, jsonify, current_app
from flask_login import login_required, current_user
from app.extensions import db
from app.models import Company, Subscription, SubscriptionPlan, User, AuditLog
from app.utils import log_audit, create_stripe_payment_intent, create_razorpay_order
import stripe
import razorpay
from datetime import datetime, timedelta
import os

billing_bp = Blueprint('billing', __name__)

@billing_bp.route('/subscription')
@login_required
def subscription():
    """Subscription management page"""
    if current_user.role not in ['admin', 'manager']:
        flash('You do not have permission to access billing.', 'error')
        return redirect(url_for('main.dashboard'))
    
    company = current_user.company
    subscription = Subscription.query.filter_by(company_id=company.id).first()
    
    # Get current plan details
    current_plan = {
        'name': company.subscription_plan.value.title(),
        'max_users': company.max_users,
        'max_storage_gb': company.max_storage_gb,
        'features': get_plan_features(company.subscription_plan)
    }
    
    # Get available plans
    available_plans = get_available_plans()
    
    return render_template('billing/subscription.html',
                         company=company,
                         subscription=subscription,
                         current_plan=current_plan,
                         available_plans=available_plans,
                         title='Subscription Management')

@billing_bp.route('/subscription/upgrade', methods=['POST'])
@login_required
def upgrade_subscription():
    """Upgrade subscription plan"""
    if current_user.role not in ['admin', 'manager']:
        return jsonify({'success': False, 'error': 'Permission denied'})
    
    plan_name = request.form.get('plan')
    if plan_name not in [plan.value for plan in SubscriptionPlan]:
        return jsonify({'success': False, 'error': 'Invalid plan'})
    
    company = current_user.company
    new_plan = SubscriptionPlan(plan_name)
    
    # Check if upgrade is allowed
    if not can_upgrade_plan(company.subscription_plan, new_plan):
        return jsonify({'success': False, 'error': 'Invalid upgrade path'})
    
    # Update company subscription
    company.subscription_plan = new_plan
    company.max_users = get_plan_limits(new_plan)['max_users']
    company.max_storage_gb = get_plan_limits(new_plan)['max_storage_gb']
    
    # Update or create subscription record
    subscription = Subscription.query.filter_by(company_id=company.id).first()
    if not subscription:
        subscription = Subscription(company_id=company.id, plan=new_plan)
        db.session.add(subscription)
    
    subscription.plan = new_plan
    subscription.status = 'active'
    subscription.current_period_start = datetime.utcnow()
    subscription.current_period_end = datetime.utcnow() + timedelta(days=30)
    
    db.session.commit()
    
    # Log audit
    log_audit(company.id, current_user.id, 'subscription_upgraded',
             f'Upgraded to {new_plan.value} plan', 'subscription', subscription.id)
    
    return jsonify({'success': True, 'plan': new_plan.value})

@billing_bp.route('/subscription/cancel', methods=['POST'])
@login_required
def cancel_subscription():
    """Cancel subscription"""
    if current_user.role not in ['admin', 'manager']:
        return jsonify({'success': False, 'error': 'Permission denied'})
    
    company = current_user.company
    subscription = Subscription.query.filter_by(company_id=company.id).first()
    
    if subscription:
        subscription.status = 'canceled'
        subscription.cancel_at_period_end = True
        db.session.commit()
        
        # Log audit
        log_audit(company.id, current_user.id, 'subscription_canceled',
                 'Subscription canceled', 'subscription', subscription.id)
        
        return jsonify({'success': True})
    
    return jsonify({'success': False, 'error': 'No active subscription found'})

@billing_bp.route('/payment/stripe')
@login_required
def stripe_payment():
    """Stripe payment page"""
    if current_user.role not in ['admin', 'manager']:
        flash('You do not have permission to access billing.', 'error')
        return redirect(url_for('main.dashboard'))
    
    company = current_user.company
    plan = request.args.get('plan', 'pro')
    
    if plan not in [plan.value for plan in SubscriptionPlan]:
        flash('Invalid plan selected.', 'error')
        return redirect(url_for('billing.subscription'))
    
    # Get plan details
    plan_details = get_plan_details(plan)
    
    # Create Stripe payment intent
    payment_intent = create_stripe_payment_intent(
        amount=plan_details['price'],
        currency='usd',
        metadata={
            'company_id': company.id,
            'plan': plan,
            'user_id': current_user.id
        }
    )
    
    if not payment_intent:
        flash('Failed to create payment intent.', 'error')
        return redirect(url_for('billing.subscription'))
    
    return render_template('billing/stripe_payment.html',
                         payment_intent=payment_intent,
                         plan_details=plan_details,
                         stripe_key=current_app.config['STRIPE_PUBLISHABLE_KEY'],
                         title='Payment - Stripe')

@billing_bp.route('/payment/razorpay')
@login_required
def razorpay_payment():
    """Razorpay payment page"""
    if current_user.role not in ['admin', 'manager']:
        flash('You do not have permission to access billing.', 'error')
        return redirect(url_for('main.dashboard'))
    
    company = current_user.company
    plan = request.args.get('plan', 'pro')
    
    if plan not in [plan.value for plan in SubscriptionPlan]:
        flash('Invalid plan selected.', 'error')
        return redirect(url_for('billing.subscription'))
    
    # Get plan details
    plan_details = get_plan_details(plan)
    
    # Create Razorpay order
    order = create_razorpay_order(
        amount=plan_details['price'],
        currency='INR',
        receipt=f"sub_{company.id}_{plan}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
    )
    
    if not order:
        flash('Failed to create payment order.', 'error')
        return redirect(url_for('billing.subscription'))
    
    return render_template('billing/razorpay_payment.html',
                         order=order,
                         plan_details=plan_details,
                         razorpay_key=current_app.config['RAZORPAY_KEY_ID'],
                         title='Payment - Razorpay')

@billing_bp.route('/payment/stripe/webhook', methods=['POST'])
def stripe_webhook():
    """Stripe webhook handler"""
    payload = request.get_data()
    sig_header = request.headers.get('Stripe-Signature')
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, current_app.config.get('STRIPE_WEBHOOK_SECRET', '')
        )
    except ValueError as e:
        return jsonify({'error': 'Invalid payload'}), 400
    except stripe.error.SignatureVerificationError as e:
        return jsonify({'error': 'Invalid signature'}), 400
    
    # Handle the event
    if event['type'] == 'payment_intent.succeeded':
        payment_intent = event['data']['object']
        handle_stripe_payment_success(payment_intent)
    elif event['type'] == 'payment_intent.payment_failed':
        payment_intent = event['data']['object']
        handle_stripe_payment_failure(payment_intent)
    
    return jsonify({'success': True})

@billing_bp.route('/payment/razorpay/webhook', methods=['POST'])
def razorpay_webhook():
    """Razorpay webhook handler"""
    # Verify webhook signature
    webhook_signature = request.headers.get('X-Razorpay-Signature')
    webhook_secret = current_app.config.get('RAZORPAY_WEBHOOK_SECRET', '')
    
    if not verify_razorpay_signature(request.get_data(), webhook_signature, webhook_secret):
        return jsonify({'error': 'Invalid signature'}), 400
    
    # Parse webhook data
    webhook_data = request.get_json()
    
    if webhook_data.get('event') == 'payment.captured':
        payment_data = webhook_data.get('payload', {}).get('payment', {})
        handle_razorpay_payment_success(payment_data)
    
    return jsonify({'success': True})

@billing_bp.route('/invoices')
@login_required
def billing_invoices():
    """Billing invoices page"""
    if current_user.role not in ['admin', 'manager']:
        flash('You do not have permission to access billing.', 'error')
        return redirect(url_for('main.dashboard'))
    
    company = current_user.company
    
    # Get billing invoices (implement billing invoice system)
    invoices = []  # Placeholder for billing invoices
    
    return render_template('billing/invoices.html',
                         invoices=invoices,
                         company=company,
                         title='Billing Invoices')

@billing_bp.route('/usage')
@login_required
def usage():
    """Usage analytics page"""
    if current_user.role not in ['admin', 'manager']:
        flash('You do not have permission to access billing.', 'error')
        return redirect(url_for('main.dashboard'))
    
    company = current_user.company
    
    # Calculate current usage
    current_users = User.query.filter_by(company_id=company.id).count()
    current_storage = calculate_storage_usage(company.id)
    
    usage_data = {
        'users': {
            'current': current_users,
            'limit': company.max_users,
            'percentage': (current_users / company.max_users) * 100 if company.max_users > 0 else 0
        },
        'storage': {
            'current_gb': current_storage,
            'limit_gb': company.max_storage_gb,
            'percentage': (current_storage / company.max_storage_gb) * 100 if company.max_storage_gb > 0 else 0
        }
    }
    
    return render_template('billing/usage.html',
                         usage_data=usage_data,
                         company=company,
                         title='Usage Analytics')

# Helper functions
def get_plan_features(plan):
    """Get features for a specific plan"""
    features = {
        SubscriptionPlan.STARTER: [
            'Up to 5 users',
            '100 leads',
            'Basic reporting',
            'Email support',
            '10GB storage'
        ],
        SubscriptionPlan.PRO: [
            'Up to 20 users',
            'Unlimited leads',
            'Advanced reporting',
            'Priority support',
            '100GB storage',
            'WhatsApp integration',
            'Custom branding'
        ],
        SubscriptionPlan.ENTERPRISE: [
            'Unlimited users',
            'Unlimited everything',
            'Custom integrations',
            'Dedicated support',
            'Unlimited storage',
            'API access',
            'White-label solution'
        ]
    }
    return features.get(plan, [])

def get_plan_limits(plan):
    """Get limits for a specific plan"""
    limits = {
        SubscriptionPlan.STARTER: {'max_users': 5, 'max_storage_gb': 10},
        SubscriptionPlan.PRO: {'max_users': 20, 'max_storage_gb': 100},
        SubscriptionPlan.ENTERPRISE: {'max_users': -1, 'max_storage_gb': -1}  # Unlimited
    }
    return limits.get(plan, {'max_users': 5, 'max_storage_gb': 10})

def get_available_plans():
    """Get available subscription plans"""
    return [
        {
            'name': 'Starter',
            'value': 'starter',
            'price': 29,
            'currency': 'USD',
            'period': 'month',
            'features': get_plan_features(SubscriptionPlan.STARTER),
            'popular': False
        },
        {
            'name': 'Pro',
            'value': 'pro',
            'price': 79,
            'currency': 'USD',
            'period': 'month',
            'features': get_plan_features(SubscriptionPlan.PRO),
            'popular': True
        },
        {
            'name': 'Enterprise',
            'value': 'enterprise',
            'price': 199,
            'currency': 'USD',
            'period': 'month',
            'features': get_plan_features(SubscriptionPlan.ENTERPRISE),
            'popular': False
        }
    ]

def get_plan_details(plan_name):
    """Get details for a specific plan"""
    plans = get_available_plans()
    for plan in plans:
        if plan['value'] == plan_name:
            return plan
    return None

def can_upgrade_plan(current_plan, new_plan):
    """Check if plan upgrade is allowed"""
    plan_order = [SubscriptionPlan.STARTER, SubscriptionPlan.PRO, SubscriptionPlan.ENTERPRISE]
    current_index = plan_order.index(current_plan)
    new_index = plan_order.index(new_plan)
    return new_index > current_index

def calculate_storage_usage(company_id):
    """Calculate current storage usage for a company"""
    # Implement storage calculation logic
    # This would typically involve scanning uploaded files, database size, etc.
    return 2.5  # Placeholder: 2.5 GB

def handle_stripe_payment_success(payment_intent):
    """Handle successful Stripe payment"""
    try:
        metadata = payment_intent.get('metadata', {})
        company_id = metadata.get('company_id')
        plan = metadata.get('plan')
        user_id = metadata.get('user_id')
        
        if company_id and plan:
            company = Company.query.get(company_id)
            if company:
                # Update company subscription
                company.subscription_plan = SubscriptionPlan(plan)
                company.max_users = get_plan_limits(company.subscription_plan)['max_users']
                company.max_storage_gb = get_plan_limits(company.subscription_plan)['max_storage_gb']
                
                # Update subscription record
                subscription = Subscription.query.filter_by(company_id=company.id).first()
                if not subscription:
                    subscription = Subscription(company_id=company.id, plan=company.subscription_plan)
                    db.session.add(subscription)
                
                subscription.stripe_subscription_id = payment_intent.get('id')
                subscription.status = 'active'
                subscription.current_period_start = datetime.utcnow()
                subscription.current_period_end = datetime.utcnow() + timedelta(days=30)
                
                db.session.commit()
                
                # Log audit
                log_audit(company.id, user_id, 'stripe_payment_success',
                         f'Payment successful for {plan} plan', 'subscription', subscription.id)
    except Exception as e:
        current_app.logger.error(f"Error handling Stripe payment success: {str(e)}")

def handle_stripe_payment_failure(payment_intent):
    """Handle failed Stripe payment"""
    try:
        metadata = payment_intent.get('metadata', {})
        company_id = metadata.get('company_id')
        user_id = metadata.get('user_id')
        
        if company_id:
            # Log audit
            log_audit(company_id, user_id, 'stripe_payment_failed',
                     'Payment failed', 'subscription', None)
    except Exception as e:
        current_app.logger.error(f"Error handling Stripe payment failure: {str(e)}")

def handle_razorpay_payment_success(payment_data):
    """Handle successful Razorpay payment"""
    try:
        # Extract payment details and update subscription
        # Implementation depends on Razorpay payment structure
        pass
    except Exception as e:
        current_app.logger.error(f"Error handling Razorpay payment success: {str(e)}")

def verify_razorpay_signature(payload, signature, secret):
    """Verify Razorpay webhook signature"""
    try:
        # Implement signature verification logic
        return True  # Placeholder
    except Exception as e:
        current_app.logger.error(f"Error verifying Razorpay signature: {str(e)}")
        return False
