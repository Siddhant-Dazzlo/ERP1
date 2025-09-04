from flask import current_app, request
from flask_mail import Message
from app.extensions import mail, db
from app.models import AuditLog
from datetime import datetime
import os
import json
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
import stripe
import razorpay
from twilio.rest import Client
import redis
from celery import Celery

def send_email(subject, recipients, body, html=None):
    """Send email using Flask-Mail"""
    try:
        msg = Message(
            subject=subject,
            recipients=recipients,
            body=body,
            html=html
        )
        mail.send(msg)
        return True
    except Exception as e:
        current_app.logger.error(f"Failed to send email: {str(e)}")
        return False

def log_audit(company_id, user_id, action, details, resource_type=None, resource_id=None):
    """Log audit trail for compliance"""
    try:
        audit_log = AuditLog(
            company_id=company_id,
            user_id=user_id,
            action=action,
            details={'message': details},
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=request.remote_addr if request else None,
            user_agent=request.headers.get('User-Agent') if request else None
        )
        db.session.add(audit_log)
        db.session.commit()
        return True
    except Exception as e:
        current_app.logger.error(f"Failed to log audit: {str(e)}")
        return False

def generate_pdf_quotation(quotation):
    """Generate PDF quotation"""
    try:
        filename = f"quotation_{quotation.quotation_number}.pdf"
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], 'pdfs', filename)
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        doc = SimpleDocTemplate(filepath, pagesize=A4)
        styles = getSampleStyleSheet()
        story = []
        
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            spaceAfter=30,
            alignment=1  # Center
        )
        story.append(Paragraph(f"QUOTATION - {quotation.quotation_number}", title_style))
        story.append(Spacer(1, 20))
        
        # Company and Customer Info
        company_info = [
            ['Company:', quotation.company.name],
            ['Address:', quotation.company.address or ''],
            ['Phone:', quotation.company.phone or ''],
            ['Email:', quotation.company.email or '']
        ]
        
        customer_info = [
            ['Customer:', f"{quotation.customer.first_name} {quotation.customer.last_name}"],
            ['Company:', quotation.customer.company_name or ''],
            ['Address:', quotation.customer.address or ''],
            ['Phone:', quotation.customer.phone or '']
        ]
        
        info_table = Table([company_info, customer_info], colWidths=[2*inch, 4*inch])
        info_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        
        story.append(info_table)
        story.append(Spacer(1, 20))
        
        # Items Table
        items_data = [['Item', 'Description', 'Qty', 'Unit Price', 'Total']]
        for item in quotation.items:
            items_data.append([
                item.product.name,
                item.description or '',
                str(item.quantity),
                f"${item.unit_price:.2f}",
                f"${item.total_amount:.2f}"
            ])
        
        items_table = Table(items_data, colWidths=[1.5*inch, 2*inch, 0.8*inch, 1.2*inch, 1*inch])
        items_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(items_table)
        story.append(Spacer(1, 20))
        
        # Totals
        totals_data = [
            ['Subtotal:', f"${quotation.subtotal:.2f}"],
            ['Tax:', f"${quotation.tax_amount:.2f}"],
            ['Total:', f"${quotation.total_amount:.2f}"]
        ]
        
        totals_table = Table(totals_data, colWidths=[4*inch, 2*inch])
        totals_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 12),
        ]))
        
        story.append(totals_table)
        
        # Notes
        if quotation.notes:
            story.append(Spacer(1, 20))
            story.append(Paragraph("Notes:", styles['Heading3']))
            story.append(Paragraph(quotation.notes, styles['Normal']))
        
        # Build PDF
        doc.build(story)
        return filepath
    except Exception as e:
        current_app.logger.error(f"Failed to generate PDF quotation: {str(e)}")
        return None

def generate_pdf_invoice(invoice):
    """Generate PDF invoice"""
    try:
        filename = f"invoice_{invoice.invoice_number}.pdf"
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], 'pdfs', filename)
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        doc = SimpleDocTemplate(filepath, pagesize=A4)
        styles = getSampleStyleSheet()
        story = []
        
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            spaceAfter=30,
            alignment=1  # Center
        )
        story.append(Paragraph(f"INVOICE - {invoice.invoice_number}", title_style))
        story.append(Spacer(1, 20))
        
        # Company and Customer Info
        company_info = [
            ['Company:', invoice.company.name],
            ['Address:', invoice.company.address or ''],
            ['Phone:', invoice.company.phone or ''],
            ['Email:', invoice.company.email or '']
        ]
        
        customer_info = [
            ['Customer:', f"{invoice.customer.first_name} {invoice.customer.last_name}"],
            ['Company:', invoice.customer.company_name or ''],
            ['Address:', invoice.customer.address or ''],
            ['Phone:', invoice.customer.phone or '']
        ]
        
        info_table = Table([company_info, customer_info], colWidths=[2*inch, 4*inch])
        info_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        
        story.append(info_table)
        story.append(Spacer(1, 20))
        
        # Invoice Details
        invoice_details = [
            ['Invoice Date:', invoice.created_at.strftime('%Y-%m-%d')],
            ['Due Date:', invoice.due_date.strftime('%Y-%m-%d') if invoice.due_date else 'N/A'],
            ['Status:', invoice.status.title()]
        ]
        
        details_table = Table(invoice_details, colWidths=[2*inch, 4*inch])
        details_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
        ]))
        
        story.append(details_table)
        story.append(Spacer(1, 20))
        
        # Items Table
        items_data = [['Item', 'Description', 'Qty', 'Unit Price', 'Total']]
        for item in invoice.items:
            items_data.append([
                item.product.name,
                item.description or '',
                str(item.quantity),
                f"${item.unit_price:.2f}",
                f"${item.total_amount:.2f}"
            ])
        
        items_table = Table(items_data, colWidths=[1.5*inch, 2*inch, 0.8*inch, 1.2*inch, 1*inch])
        items_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(items_table)
        story.append(Spacer(1, 20))
        
        # Totals
        totals_data = [
            ['Subtotal:', f"${invoice.subtotal:.2f}"],
            ['Tax:', f"${invoice.tax_amount:.2f}"],
            ['Total:', f"${invoice.total_amount:.2f}"]
        ]
        
        totals_table = Table(totals_data, colWidths=[4*inch, 2*inch])
        totals_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 12),
        ]))
        
        story.append(totals_table)
        
        # Notes
        if invoice.notes:
            story.append(Spacer(1, 20))
            story.append(Paragraph("Notes:", styles['Heading3']))
            story.append(Paragraph(invoice.notes, styles['Normal']))
        
        # Build PDF
        doc.build(story)
        return filepath
    except Exception as e:
        current_app.logger.error(f"Failed to generate PDF invoice: {str(e)}")
        return None

def send_whatsapp_message(to_number, message):
    """Send WhatsApp message using Twilio"""
    try:
        client = Client(
            current_app.config['TWILIO_ACCOUNT_SID'],
            current_app.config['TWILIO_AUTH_TOKEN']
        )
        
        # Format phone number for WhatsApp
        if not to_number.startswith('whatsapp:'):
            to_number = f"whatsapp:+{to_number}"
        
        message = client.messages.create(
            from_=f"whatsapp:{current_app.config['TWILIO_PHONE_NUMBER']}",
            body=message,
            to=to_number
        )
        return message.sid
    except Exception as e:
        current_app.logger.error(f"Failed to send WhatsApp message: {str(e)}")
        return None

def send_sms(to_number, message):
    """Send SMS using Twilio"""
    try:
        client = Client(
            current_app.config['TWILIO_ACCOUNT_SID'],
            current_app.config['TWILIO_AUTH_TOKEN']
        )
        
        message = client.messages.create(
            from_=current_app.config['TWILIO_PHONE_NUMBER'],
            body=message,
            to=f"+{to_number}"
        )
        return message.sid
    except Exception as e:
        current_app.logger.error(f"Failed to send SMS: {str(e)}")
        return None

def create_stripe_payment_intent(amount, currency='usd', metadata=None):
    """Create Stripe payment intent"""
    try:
        stripe.api_key = current_app.config['STRIPE_SECRET_KEY']
        
        intent = stripe.PaymentIntent.create(
            amount=int(amount * 100),  # Convert to cents
            currency=currency,
            metadata=metadata or {}
        )
        return intent
    except Exception as e:
        current_app.logger.error(f"Failed to create Stripe payment intent: {str(e)}")
        return None

def create_razorpay_order(amount, currency='INR', receipt=None):
    """Create Razorpay order"""
    try:
        client = razorpay.Client(
            auth=(current_app.config['RAZORPAY_KEY_ID'], current_app.config['RAZORPAY_KEY_SECRET'])
        )
        
        order_data = {
            'amount': int(amount * 100),  # Convert to paise
            'currency': currency,
            'receipt': receipt or f"order_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        }
        
        order = client.order.create(data=order_data)
        return order
    except Exception as e:
        current_app.logger.error(f"Failed to create Razorpay order: {str(e)}")
        return None

def get_redis_client():
    """Get Redis client"""
    try:
        redis_client = redis.from_url(current_app.config['REDIS_URL'])
        return redis_client
    except Exception as e:
        current_app.logger.error(f"Failed to connect to Redis: {str(e)}")
        return None

def cache_data(key, data, expire_time=3600):
    """Cache data in Redis"""
    try:
        redis_client = get_redis_client()
        if redis_client:
            # Handle different data types for JSON serialization
            if isinstance(data, dict):
                # Regular dictionary - serialize as is
                pass
            elif hasattr(data, '__iter__') and not isinstance(data, (str, bytes, dict)):
                # Iterable that's not a string, bytes, or dict (likely a query result)
                try:
                    # Try to convert to list of dicts if it's a query result
                    data = [dict(row._mapping) if hasattr(row, '_mapping') else row for row in data]
                except:
                    # If conversion fails, convert to string representation
                    data = str(data)
            elif hasattr(data, '_mapping'):
                # Single Row object
                data = dict(data._mapping)
            
            redis_client.setex(key, expire_time, json.dumps(data, default=str))
            return True
        return False
    except Exception as e:
        current_app.logger.error(f"Failed to cache data: {str(e)}")
        return False

def get_cached_data(key):
    """Get cached data from Redis"""
    try:
        redis_client = get_redis_client()
        if redis_client:
            data = redis_client.get(key)
            if data:
                return json.loads(data)
        return None
    except Exception as e:
        current_app.logger.error(f"Failed to get cached data: {str(e)}")
        return None

def clear_cache(key):
    """Clear cached data from Redis"""
    try:
        redis_client = get_redis_client()
        if redis_client:
            redis_client.delete(key)
            return True
        return False
    except Exception as e:
        current_app.logger.error(f"Failed to clear cached data: {str(e)}")
        return False

def format_currency(amount, currency='USD'):
    """Format currency amount"""
    # Handle None, Undefined, or empty values
    if amount is None or amount == '' or str(amount).lower() in ['none', 'undefined']:
        amount = 0
    
    try:
        # Convert to float to ensure it's a number
        amount = float(amount)
    except (ValueError, TypeError):
        amount = 0
    
    if currency == 'USD':
        return f"${amount:,.2f}"
    elif currency == 'INR':
        return f"₹{amount:,.2f}"
    else:
        return f"{amount:,.2f} {currency}"

def format_date(date_obj):
    """Format date object"""
    if date_obj:
        return date_obj.strftime('%Y-%m-%d')
    return ''

def format_datetime(datetime_obj):
    """Format datetime object"""
    if datetime_obj:
        return datetime_obj.strftime('%Y-%m-%d %H:%M')
    return ''

def get_file_extension(filename):
    """Get file extension from filename"""
    return os.path.splitext(filename)[1].lower()

def is_allowed_file(filename, allowed_extensions):
    """Check if file extension is allowed"""
    return get_file_extension(filename) in allowed_extensions

def save_file(file, folder, filename=None):
    """Save uploaded file"""
    try:
        if not filename:
            filename = file.filename
        
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], folder, filename)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        file.save(filepath)
        return filepath
    except Exception as e:
        current_app.logger.error(f"Failed to save file: {str(e)}")
        return None
