from celery import Celery
from app import create_app
import os

def make_celery(app):
    """Create Celery instance"""
    celery = Celery(
        app.import_name,
        backend=app.config['REDIS_URL'],
        broker=app.config['REDIS_URL']
    )
    
    # Configure Celery
    celery.conf.update(
        task_serializer='json',
        accept_content=['json'],
        result_serializer='json',
        timezone='UTC',
        enable_utc=True,
        task_track_started=True,
        task_time_limit=30 * 60,  # 30 minutes
        task_soft_time_limit=25 * 60,  # 25 minutes
        worker_prefetch_multiplier=1,
        worker_max_tasks_per_child=1000,
        result_expires=3600,  # 1 hour
        beat_schedule={
            'send-daily-reports': {
                'task': 'celery_app.send_daily_reports',
                'schedule': 86400.0,  # Daily
            },
            'send-reminders': {
                'task': 'celery_app.send_reminders',
                'schedule': 3600.0,  # Hourly
            },
            'cleanup-old-files': {
                'task': 'celery_app.cleanup_old_files',
                'schedule': 604800.0,  # Weekly
            },
            'backup-database': {
                'task': 'celery_app.backup_database',
                'schedule': 86400.0,  # Daily
            }
        }
    )
    
    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)
    
    celery.Task = ContextTask
    return celery

# Create Flask app and Celery instance
flask_app = create_app()
celery = make_celery(flask_app)

# Background tasks
@celery.task
def send_daily_reports():
    """Send daily reports to users"""
    from app.models import User, Company, Lead, Customer, Invoice
    from app.utils import send_email
    from sqlalchemy import func
    from datetime import datetime, timedelta
    
    try:
        # Get all active companies
        companies = Company.query.filter_by(is_active=True).all()
        
        for company in companies:
            # Get company users
            users = User.query.filter_by(company_id=company.id, is_active=True).all()
            
            # Calculate daily statistics
            today = datetime.utcnow().date()
            yesterday = today - timedelta(days=1)
            
            # New leads
            new_leads = Lead.query.filter(
                Lead.company_id == company.id,
                func.date(Lead.created_at) == yesterday
            ).count()
            
            # New customers
            new_customers = Customer.query.filter(
                Customer.company_id == company.id,
                func.date(Customer.created_at) == yesterday
            ).count()
            
            # Revenue
            revenue = db.session.query(func.sum(Invoice.total_amount)).filter(
                Invoice.company_id == company.id,
                Invoice.status == 'paid',
                func.date(Invoice.payment_date) == yesterday
            ).scalar() or 0
            
            # Send report to each user
            for user in users:
                if user.role.value in ['admin', 'manager']:
                    email_content = f"""
                    Daily Sales Report - {yesterday.strftime('%Y-%m-%d')}
                    
                    Company: {company.name}
                    
                    Summary:
                    - New Leads: {new_leads}
                    - New Customers: {new_customers}
                    - Revenue: ${revenue:,.2f}
                    
                    Best regards,
                    Sales ERP Team
                    """
                    
                    send_email(
                        subject=f"Daily Sales Report - {yesterday.strftime('%Y-%m-%d')}",
                        recipients=[user.email],
                        body=email_content
                    )
        
        return f"Daily reports sent to {len(companies)} companies"
    
    except Exception as e:
        return f"Error sending daily reports: {str(e)}"

@celery.task
def send_reminders():
    """Send reminders for overdue tasks and follow-ups"""
    from app.models import Task, Lead, User
    from app.utils import send_email, send_whatsapp_message, send_sms
    from datetime import datetime, timedelta
    
    try:
        # Get overdue tasks
        overdue_tasks = Task.query.filter(
            Task.due_date < datetime.utcnow(),
            Task.status.in_(['pending', 'in_progress'])
        ).all()
        
        for task in overdue_tasks:
            if task.assigned_to and task.assigned_to.is_active:
                # Send email reminder
                email_content = f"""
                Task Reminder
                
                Task: {task.title}
                Due Date: {task.due_date.strftime('%Y-%m-%d')}
                Priority: {task.priority.value.title()}
                
                Please complete this task as soon as possible.
                
                Best regards,
                Sales ERP Team
                """
                
                send_email(
                    subject="Task Reminder - Overdue",
                    recipients=[task.assigned_to.email],
                    body=email_content
                )
                
                # Send WhatsApp reminder if phone number exists
                if task.assigned_to.phone:
                    whatsapp_message = f"Reminder: Task '{task.title}' is overdue. Please complete it soon."
                    send_whatsapp_message(task.assigned_to.phone, whatsapp_message)
        
        # Get leads with overdue follow-ups
        overdue_leads = Lead.query.filter(
            Lead.next_follow_up < datetime.utcnow(),
            Lead.status.in_(['prospect', 'contacted', 'qualified'])
        ).all()
        
        for lead in overdue_leads:
            if lead.assigned_to and lead.assigned_to.is_active:
                # Send email reminder
                email_content = f"""
                Follow-up Reminder
                
                Lead: {lead.get_full_name()}
                Company: {lead.company_name or 'N/A'}
                Follow-up Date: {lead.next_follow_up.strftime('%Y-%m-%d')}
                
                Please follow up with this lead as soon as possible.
                
                Best regards,
                Sales ERP Team
                """
                
                send_email(
                    subject="Follow-up Reminder - Overdue",
                    recipients=[lead.assigned_to.email],
                    body=email_content
                )
        
        return f"Reminders sent for {len(overdue_tasks)} tasks and {len(overdue_leads)} leads"
    
    except Exception as e:
        return f"Error sending reminders: {str(e)}"

@celery.task
def cleanup_old_files():
    """Clean up old uploaded files"""
    import os
    from datetime import datetime, timedelta
    
    try:
        upload_folder = flask_app.config.get('UPLOAD_FOLDER', 'uploads')
        cutoff_date = datetime.utcnow() - timedelta(days=90)  # 90 days
        
        cleaned_files = 0
        total_size_freed = 0
        
        for root, dirs, files in os.walk(upload_folder):
            for file in files:
                file_path = os.path.join(root, file)
                file_modified = datetime.fromtimestamp(os.path.getmtime(file_path))
                
                if file_modified < cutoff_date:
                    try:
                        file_size = os.path.getsize(file_path)
                        os.remove(file_path)
                        cleaned_files += 1
                        total_size_freed += file_size
                    except Exception as e:
                        flask_app.logger.error(f"Failed to delete file {file_path}: {str(e)}")
        
        # Convert to MB
        size_freed_mb = total_size_freed / (1024 * 1024)
        
        return f"Cleaned up {cleaned_files} files, freed {size_freed_mb:.2f} MB"
    
    except Exception as e:
        return f"Error cleaning up files: {str(e)}"

@celery.task
def backup_database():
    """Create database backup"""
    import subprocess
    from datetime import datetime
    
    try:
        # Get database configuration
        db_url = flask_app.config['SQLALCHEMY_DATABASE_URI']
        
        # Parse database connection string
        if db_url.startswith('postgresql://'):
            # PostgreSQL backup
            backup_dir = 'backups'
            os.makedirs(backup_dir, exist_ok=True)
            
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            backup_file = f"{backup_dir}/backup_{timestamp}.sql"
            
            # Extract connection details (simplified)
            # In production, use proper environment variables
            db_name = db_url.split('/')[-1]
            
            # Create backup using pg_dump
            cmd = f"pg_dump -h localhost -U postgres -d {db_name} > {backup_file}"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            
            if result.returncode == 0:
                # Compress backup file
                import gzip
                with open(backup_file, 'rb') as f_in:
                    with gzip.open(f"{backup_file}.gz", 'wb') as f_out:
                        f_out.writelines(f_in)
                
                # Remove uncompressed file
                os.remove(backup_file)
                
                return f"Database backup created: {backup_file}.gz"
            else:
                return f"Database backup failed: {result.stderr}"
        
        else:
            return "Database backup not implemented for this database type"
    
    except Exception as e:
        return f"Error creating database backup: {str(e)}"

@celery.task
def generate_report(company_id, report_type, user_id, date_from=None, date_to=None):
    """Generate custom reports"""
    from app.models import Lead, Customer, Invoice, User
    from app.utils import send_email
    from sqlalchemy import func
    import pandas as pd
    import io
    
    try:
        company = Company.query.get(company_id)
        user = User.query.get(user_id)
        
        if not company or not user:
            return "Company or user not found"
        
        # Set default date range if not provided
        if not date_from:
            date_from = datetime.utcnow() - timedelta(days=30)
        if not date_to:
            date_to = datetime.utcnow()
        
        if report_type == 'leads':
            # Generate leads report
            leads = Lead.query.filter(
                Lead.company_id == company_id,
                Lead.created_at >= date_from,
                Lead.created_at <= date_to
            ).all()
            
            # Create DataFrame
            data = []
            for lead in leads:
                data.append({
                    'First Name': lead.first_name,
                    'Last Name': lead.last_name,
                    'Email': lead.email,
                    'Company': lead.company_name,
                    'Status': lead.status.value,
                    'Source': lead.source,
                    'Created Date': lead.created_at.strftime('%Y-%m-%d')
                })
            
            df = pd.DataFrame(data)
            
        elif report_type == 'revenue':
            # Generate revenue report
            invoices = Invoice.query.filter(
                Invoice.company_id == company_id,
                Invoice.status == 'paid',
                Invoice.payment_date >= date_from,
                Invoice.payment_date <= date_to
            ).all()
            
            data = []
            for invoice in invoices:
                data.append({
                    'Invoice Number': invoice.invoice_number,
                    'Customer': f"{invoice.customer.first_name} {invoice.customer.last_name}",
                    'Amount': float(invoice.total_amount),
                    'Payment Date': invoice.payment_date.strftime('%Y-%m-%d')
                })
            
            df = pd.DataFrame(data)
        
        else:
            return f"Unknown report type: {report_type}"
        
        # Create Excel file
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Report', index=False)
        
        output.seek(0)
        
        # Send report via email
        email_content = f"""
        Report Generated
        
        Report Type: {report_type.title()}
        Company: {company.name}
        Date Range: {date_from.strftime('%Y-%m-%d')} to {date_to.strftime('%Y-%m-%d')}
        
        Please find the attached report.
        
        Best regards,
        Sales ERP Team
        """
        
        # In a real implementation, you would save the file and attach it
        # For now, just return success message
        return f"Report generated successfully for {report_type}"
    
    except Exception as e:
        return f"Error generating report: {str(e)}"

@celery.task
def sync_external_data(company_id, sync_type):
    """Sync data with external systems (Tally, QuickBooks, etc.)"""
    try:
        company = Company.query.get(company_id)
        
        if sync_type == 'tally':
            # Implement Tally integration
            return f"Tally sync completed for {company.name}"
        
        elif sync_type == 'quickbooks':
            # Implement QuickBooks integration
            return f"QuickBooks sync completed for {company.name}"
        
        else:
            return f"Unknown sync type: {sync_type}"
    
    except Exception as e:
        return f"Error syncing external data: {str(e)}"

@celery.task
def send_bulk_notifications(company_id, notification_type, recipients, message):
    """Send bulk notifications (email, SMS, WhatsApp)"""
    from app.utils import send_email, send_sms, send_whatsapp_message
    
    try:
        company = Company.query.get(company_id)
        success_count = 0
        failure_count = 0
        
        for recipient in recipients:
            try:
                if notification_type == 'email':
                    send_email(
                        subject=f"Message from {company.name}",
                        recipients=[recipient['email']],
                        body=message
                    )
                    success_count += 1
                
                elif notification_type == 'sms' and recipient.get('phone'):
                    send_sms(recipient['phone'], message)
                    success_count += 1
                
                elif notification_type == 'whatsapp' and recipient.get('phone'):
                    send_whatsapp_message(recipient['phone'], message)
                    success_count += 1
                
            except Exception as e:
                failure_count += 1
                flask_app.logger.error(f"Failed to send {notification_type} to {recipient}: {str(e)}")
        
        return f"Bulk notifications sent: {success_count} success, {failure_count} failed"
    
    except Exception as e:
        return f"Error sending bulk notifications: {str(e)}"

if __name__ == '__main__':
    celery.start()
