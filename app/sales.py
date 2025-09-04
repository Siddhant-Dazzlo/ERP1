from flask import Blueprint, render_template, request, redirect, url_for, flash, g, jsonify, send_file
from flask_login import login_required, current_user
from app.extensions import db
from app.models import Lead, Customer, Product, Quotation, QuotationItem, Invoice, InvoiceItem, Activity, User, UserRole
from app.forms import LeadForm, CustomerForm, ProductForm, QuotationForm, InvoiceForm, ActivityForm
from app.utils import log_audit, format_currency, format_date, generate_pdf_quotation, generate_pdf_invoice
from sqlalchemy import func, desc
from datetime import datetime, timedelta
import uuid

sales_bp = Blueprint('sales', __name__)

# Lead Management
@sales_bp.route('/leads')
@login_required
def leads():
    """List all leads"""
    company = current_user.company
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    # Get filter parameters
    status_filter = request.args.get('status', '')
    source_filter = request.args.get('source', '')
    assigned_filter = request.args.get('assigned_to', '')
    search_query = request.args.get('search', '')
    
    # Build query
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
    
    # Order by creation date
    leads = query.order_by(desc(Lead.created_at)).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    # Get users for filter
    users = User.query.filter_by(company_id=company.id).all()
    
    return render_template('sales/leads.html', 
                         leads=leads,
                         users=users,
                         title='Leads')

@sales_bp.route('/leads/new', methods=['GET', 'POST'])
@login_required
def new_lead():
    """Create new lead"""
    form = LeadForm()
    
    if form.validate_on_submit():
        lead = Lead(
            company_id=current_user.company.id,
            assigned_to_id=current_user.id,
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            email=form.email.data,
            phone=form.phone.data,
            company_name=form.company_name.data,
            job_title=form.job_title.data,
            industry=form.industry.data,
            source=form.source.data,
            estimated_value=form.estimated_value.data,
            notes=form.notes.data,
            next_follow_up=form.next_follow_up.data
        )
        
        db.session.add(lead)
        db.session.commit()
        
        # Log audit
        log_audit(current_user.company.id, current_user.id, 'lead_created', 
                 f'Created lead: {lead.get_full_name()}', 'lead', lead.id)
        
        flash('Lead created successfully!', 'success')
        return redirect(url_for('sales.leads'))
    
    return render_template('sales/lead_form.html', form=form, title='New Lead')

@sales_bp.route('/leads/<int:lead_id>')
@login_required
def view_lead(lead_id):
    """View lead details"""
    lead = Lead.query.filter_by(
        id=lead_id, company_id=current_user.company.id
    ).first_or_404()
    
    # Get lead activities
    activities = Activity.query.filter_by(
        company_id=current_user.company.id, lead_id=lead_id
    ).order_by(desc(Activity.created_at)).all()
    
    return render_template('sales/lead_detail.html', 
                         lead=lead,
                         activities=activities,
                         title=f'Lead: {lead.get_full_name()}')

@sales_bp.route('/leads/<int:lead_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_lead(lead_id):
    """Edit lead"""
    lead = Lead.query.filter_by(
        id=lead_id, company_id=current_user.company.id
    ).first_or_404()
    
    form = LeadForm(obj=lead)
    
    if form.validate_on_submit():
        form.populate_obj(lead)
        db.session.commit()
        
        # Log audit
        log_audit(current_user.company.id, current_user.id, 'lead_updated', 
                 f'Updated lead: {lead.get_full_name()}', 'lead', lead.id)
        
        flash('Lead updated successfully!', 'success')
        return redirect(url_for('sales.view_lead', lead_id=lead.id))
    
    return render_template('sales/lead_form.html', form=form, lead=lead, title='Edit Lead')

@sales_bp.route('/leads/<int:lead_id>/convert', methods=['POST'])
@login_required
def convert_lead(lead_id):
    """Convert lead to customer"""
    lead = Lead.query.filter_by(
        id=lead_id, company_id=current_user.company.id
    ).first_or_404()
    
    # Create customer from lead
    customer = Customer(
        company_id=current_user.company.id,
        lead_id=lead.id,
        first_name=lead.first_name,
        last_name=lead.last_name,
        email=lead.email,
        phone=lead.phone,
        company_name=lead.company_name
    )
    
    db.session.add(customer)
    
    # Update lead status
    lead.status = 'closed_won'
    
    db.session.commit()
    
    # Log audit
    log_audit(current_user.company.id, current_user.id, 'lead_converted', 
             f'Converted lead to customer: {customer.get_full_name()}', 'lead', lead.id)
    
    flash('Lead converted to customer successfully!', 'success')
    return redirect(url_for('sales.view_customer', customer_id=customer.id))

@sales_bp.route('/leads/<int:lead_id>/status', methods=['POST'])
@login_required
def update_lead_status(lead_id):
    """Update lead status"""
    lead = Lead.query.filter_by(
        id=lead_id, company_id=current_user.company.id
    ).first_or_404()
    
    new_status = request.form.get('status')
    if new_status in [status.value for status in Lead.status.__class__]:
        lead.status = new_status
        db.session.commit()
        
        # Log audit
        log_audit(current_user.company.id, current_user.id, 'lead_status_updated', 
                 f'Updated lead status to: {new_status}', 'lead', lead.id)
        
        return jsonify({'success': True, 'status': new_status})
    
    return jsonify({'success': False, 'error': 'Invalid status'})

# Customer Management
@sales_bp.route('/customers')
@login_required
def customers():
    """List all customers"""
    company = current_user.company
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
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
    
    return render_template('sales/customers.html', 
                         customers=customers,
                         title='Customers')

@sales_bp.route('/customers/new', methods=['GET', 'POST'])
@login_required
def new_customer():
    """Create new customer"""
    form = CustomerForm()
    
    if form.validate_on_submit():
        customer = Customer(
            company_id=current_user.company.id,
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            email=form.email.data,
            phone=form.phone.data,
            company_name=form.company_name.data,
            address=form.address.data,
            tax_id=form.tax_id.data,
            credit_limit=form.credit_limit.data,
            payment_terms=form.payment_terms.data
        )
        
        db.session.add(customer)
        db.session.commit()
        
        # Log audit
        log_audit(current_user.company.id, current_user.id, 'customer_created', 
                 f'Created customer: {customer.get_full_name()}', 'customer', customer.id)
        
        flash('Customer created successfully!', 'success')
        return redirect(url_for('sales.customers'))
    
    return render_template('sales/customer_form.html', form=form, title='New Customer')

@sales_bp.route('/customers/<int:customer_id>')
@login_required
def view_customer(customer_id):
    """View customer details"""
    customer = Customer.query.filter_by(
        id=customer_id, company_id=current_user.company.id
    ).first_or_404()
    
    # Get customer quotations and invoices
    quotations = Quotation.query.filter_by(
        company_id=current_user.company.id, customer_id=customer_id
    ).order_by(desc(Quotation.created_at)).all()
    
    invoices = Invoice.query.filter_by(
        company_id=current_user.company.id, customer_id=customer_id
    ).order_by(desc(Invoice.created_at)).all()
    
    return render_template('sales/customer_detail.html', 
                         customer=customer,
                         quotations=quotations,
                         invoices=invoices,
                         title=f'Customer: {customer.get_full_name()}')

@sales_bp.route('/customers/<int:customer_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_customer(customer_id):
    """Edit customer"""
    customer = Customer.query.filter_by(
        id=customer_id, company_id=current_user.company.id
    ).first_or_404()
    
    form = CustomerForm(obj=customer)
    
    if form.validate_on_submit():
        form.populate_obj(customer)
        db.session.commit()
        
        # Log audit
        log_audit(current_user.company.id, current_user.id, 'customer_updated', 
                 f'Updated customer: {customer.get_full_name()}', 'customer', customer.id)
        
        flash('Customer updated successfully!', 'success')
        return redirect(url_for('sales.view_customer', customer_id=customer.id))
    
    return render_template('sales/customer_form.html', form=form, customer=customer, title='Edit Customer')

# Product Management
@sales_bp.route('/products')
@login_required
def products():
    """List all products"""
    company = current_user.company
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    search_query = request.args.get('search', '')
    
    query = Product.query.filter_by(company_id=company.id)
    
    if search_query:
        query = query.filter(
            (Product.name.ilike(f'%{search_query}%') |
             Product.description.ilike(f'%{search_query}%') |
             Product.sku.ilike(f'%{search_query}%'))
        )
    
    products = query.order_by(Product.name).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return render_template('sales/products.html', 
                         products=products,
                         title='Products')

@sales_bp.route('/products/new', methods=['GET', 'POST'])
@login_required
def new_product():
    """Create new product"""
    form = ProductForm()
    
    if form.validate_on_submit():
        product = Product(
            company_id=current_user.company.id,
            name=form.name.data,
            description=form.description.data,
            sku=form.sku.data,
            category=form.category.data,
            unit_price=form.unit_price.data,
            cost_price=form.cost_price.data,
            tax_rate=form.tax_rate.data
        )
        
        db.session.add(product)
        db.session.commit()
        
        # Log audit
        log_audit(current_user.company.id, current_user.id, 'product_created', 
                 f'Created product: {product.name}', 'product', product.id)
        
        flash('Product created successfully!', 'success')
        return redirect(url_for('sales.products'))
    
    return render_template('sales/product_form.html', form=form, title='New Product')

@sales_bp.route('/products/<int:product_id>')
@login_required
def view_product(product_id):
    """View product details"""
    product = Product.query.filter_by(
        id=product_id, company_id=current_user.company.id
    ).first_or_404()
    
    return render_template('sales/product_detail.html', 
                         product=product,
                         title=f'Product: {product.name}')

@sales_bp.route('/products/<int:product_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_product(product_id):
    """Edit product"""
    product = Product.query.filter_by(
        id=product_id, company_id=current_user.company.id
    ).first_or_404()
    
    form = ProductForm(obj=product)
    
    if form.validate_on_submit():
        form.populate_obj(product)
        db.session.commit()
        
        # Log audit
        log_audit(current_user.company.id, current_user.id, 'product_updated', 
                 f'Updated product: {product.name}', 'product', product.id)
        
        flash('Product updated successfully!', 'success')
        return redirect(url_for('sales.view_product', product_id=product.id))
    
    return render_template('sales/product_form.html', form=form, product=product, title='Edit Product')

# Quotation Management
@sales_bp.route('/quotations')
@login_required
def quotations():
    """List all quotations"""
    company = current_user.company
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    status_filter = request.args.get('status', '')
    
    query = Quotation.query.filter_by(company_id=company.id)
    
    if status_filter:
        query = query.filter(Quotation.status == status_filter)
    
    quotations = query.order_by(desc(Quotation.created_at)).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    # Get customers for filter dropdown
    customers = Customer.query.filter_by(company_id=company.id).all()
    
    return render_template('sales/quotations.html', 
                         quotations=quotations,
                         pagination=quotations,  # Add pagination object
                         customers=customers,
                         title='Quotations')

@sales_bp.route('/quotations/new', methods=['GET', 'POST'])
@login_required
def new_quotation():
    """Create new quotation"""
    form = QuotationForm()
    
    # Populate form choices
    customers = Customer.query.filter_by(company_id=current_user.company.id).all()
    form.customer.choices = [(c.id, f"{c.first_name} {c.last_name} - {c.company_name or c.email}") for c in customers]
    
    users = User.query.filter_by(company_id=current_user.company.id).all()
    form.sales_person.choices = [(u.id, f"{u.first_name} {u.last_name}") for u in users]
    
    if form.validate_on_submit():
        # Generate quotation number
        quotation_number = f"QT-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"
        
        quotation = Quotation(
            company_id=current_user.company.id,
            customer_id=form.customer.data,
            quotation_number=quotation_number,
            subject=form.subject.data,
            valid_until=form.valid_until.data,
            notes=form.notes.data
        )
        
        db.session.add(quotation)
        db.session.commit()
        
        # Log audit
        log_audit(current_user.company.id, current_user.id, 'quotation_created', 
                 f'Created quotation: {quotation.quotation_number}', 'quotation', quotation.id)
        
        flash('Quotation created successfully!', 'success')
        return redirect(url_for('sales.view_quotation', quotation_id=quotation.id))
    
    # Get products for selection
    products = Product.query.filter_by(company_id=current_user.company.id).all()
    
    return render_template('sales/quotation_form.html', 
                         form=form,
                         customers=customers,
                         products=products,
                         title='New Quotation')

@sales_bp.route('/quotations/<int:quotation_id>')
@login_required
def view_quotation(quotation_id):
    """View quotation details"""
    quotation = Quotation.query.filter_by(
        id=quotation_id, company_id=current_user.company.id
    ).first_or_404()
    
    return render_template('sales/quotation_detail.html', 
                         quotation=quotation,
                         title=f'Quotation: {quotation.quotation_number}')

@sales_bp.route('/quotations/<int:quotation_id>/pdf')
@login_required
def download_quotation_pdf(quotation_id):
    """Download quotation as PDF"""
    quotation = Quotation.query.filter_by(
        id=quotation_id, company_id=current_user.company.id
    ).first_or_404()
    
    pdf_path = generate_pdf_quotation(quotation)
    if pdf_path:
        return send_file(pdf_path, as_attachment=True, 
                        download_name=f"quotation_{quotation.quotation_number}.pdf")
    else:
        flash('Failed to generate PDF', 'error')
        return redirect(url_for('sales.view_quotation', quotation_id=quotation.id))

@sales_bp.route('/quotations/<int:quotation_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_quotation(quotation_id):
    """Edit quotation"""
    quotation = Quotation.query.filter_by(
        id=quotation_id, company_id=current_user.company.id
    ).first_or_404()
    
    form = QuotationForm(obj=quotation)
    
    # Populate form choices
    customers = Customer.query.filter_by(company_id=current_user.company.id).all()
    form.customer.choices = [(c.id, f"{c.first_name} {c.last_name} - {c.company_name or c.email}") for c in customers]
    
    users = User.query.filter_by(company_id=current_user.company.id).all()
    form.sales_person.choices = [(u.id, f"{u.first_name} {u.last_name}") for u in users]
    
    if form.validate_on_submit():
        form.populate_obj(quotation)
        db.session.commit()
        
        # Log audit
        log_audit(current_user.company.id, current_user.id, 'quotation_updated', 
                 f'Updated quotation: {quotation.quotation_number}', 'quotation', quotation.id)
        
        flash('Quotation updated successfully!', 'success')
        return redirect(url_for('sales.view_quotation', quotation_id=quotation.id))
    
    # Get products for selection
    products = Product.query.filter_by(company_id=current_user.company.id).all()
    
    return render_template('sales/quotation_form.html', 
                         form=form,
                         quotation=quotation,
                         customers=customers,
                         products=products,
                         title='Edit Quotation')

@sales_bp.route('/send-quotation', methods=['POST'])
@login_required
def send_quotation_email():
    """Send quotation via email"""
    quotation_id = request.form.get('quotation_id')
    quotation = Quotation.query.filter_by(
        id=quotation_id, company_id=current_user.company.id
    ).first_or_404()
    
    recipient_email = request.form.get('recipient_email')
    subject = request.form.get('subject')
    message = request.form.get('message')
    
    if not recipient_email:
        return jsonify({'success': False, 'message': 'Recipient email is required'})
    
    # Here you would implement email sending logic
    # For now, just update the status
    quotation.status = 'sent'
    db.session.commit()
    
    # Log audit
    log_audit(current_user.company.id, current_user.id, 'quotation_sent', 
             f'Sent quotation to {recipient_email}', 'quotation', quotation.id)
    
    return jsonify({'success': True, 'message': 'Quotation sent successfully'})

@sales_bp.route('/convert-quotation/<int:quotation_id>', methods=['POST'])
@login_required
def convert_quotation_to_invoice_ajax(quotation_id):
    """Convert quotation to invoice via AJAX"""
    quotation = Quotation.query.filter_by(
        id=quotation_id, company_id=current_user.company.id
    ).first_or_404()
    
    # Generate invoice number
    invoice_number = f"INV-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"
    
    # Create invoice from quotation
    invoice = Invoice(
        company_id=current_user.company.id,
        customer_id=quotation.customer_id,
        invoice_number=invoice_number,
        subject=quotation.subject,
        due_date=quotation.valid_until,
        notes=quotation.notes,
        subtotal=quotation.subtotal,
        tax_amount=quotation.tax_amount,
        total_amount=quotation.total_amount
    )
    
    db.session.add(invoice)
    
    # Update quotation status
    quotation.status = 'converted'
    
    db.session.commit()
    
    # Log audit
    log_audit(current_user.company.id, current_user.id, 'quotation_converted', 
             f'Converted quotation to invoice: {invoice.invoice_number}', 'quotation', quotation.id)
    
    return jsonify({'success': True, 'invoice_id': invoice.id, 'message': 'Quotation converted to invoice successfully'})

@sales_bp.route('/delete-quotation/<int:quotation_id>', methods=['DELETE'])
@login_required
def delete_quotation_ajax(quotation_id):
    """Delete quotation via AJAX"""
    quotation = Quotation.query.filter_by(
        id=quotation_id, company_id=current_user.company.id
    ).first_or_404()
    
    quotation_number = quotation.quotation_number
    db.session.delete(quotation)
    db.session.commit()
    
    # Log audit
    log_audit(current_user.company.id, current_user.id, 'quotation_deleted', 
             f'Deleted quotation: {quotation_number}', 'quotation', quotation_id)
    
    return jsonify({'success': True, 'message': 'Quotation deleted successfully'})

@sales_bp.route('/quotations/<int:quotation_id>/convert', methods=['POST'])
@login_required
def convert_quotation_to_invoice(quotation_id):
    """Convert quotation to invoice"""
    quotation = Quotation.query.filter_by(
        id=quotation_id, company_id=current_user.company.id
    ).first_or_404()
    
    # Generate invoice number
    invoice_number = f"INV-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"
    
    # Create invoice from quotation
    invoice = Invoice(
        company_id=current_user.company.id,
        invoice_number=invoice_number,
        customer_id=quotation.customer_id,
        subject=quotation.subject,
        due_date=quotation.valid_until,
        notes=quotation.notes,
        subtotal=quotation.subtotal,
        tax_amount=quotation.tax_amount,
        total_amount=quotation.total_amount
    )
    
    db.session.add(invoice)
    
    # Update quotation status
    quotation.status = 'converted'
    
    db.session.commit()
    
    # Log audit
    log_audit(current_user.company.id, current_user.id, 'quotation_converted', 
             f'Converted quotation to invoice: {invoice.invoice_number}', 'quotation', quotation.id)
    
    return jsonify({'success': True, 'invoice_id': invoice.id, 'message': 'Quotation converted to invoice successfully'})

@sales_bp.route('/quotations/<int:quotation_id>/delete', methods=['DELETE'])
@login_required
def delete_quotation(quotation_id):
    """Delete quotation"""
    quotation = Quotation.query.filter_by(
        id=quotation_id, company_id=current_user.company.id
    ).first_or_404()
    
    quotation_number = quotation.quotation_number
    db.session.delete(quotation)
    db.session.commit()
    
    # Log audit
    log_audit(current_user.company.id, current_user.id, 'quotation_deleted', 
             f'Deleted quotation: {quotation_number}', 'quotation', quotation_id)
    
    return jsonify({'success': True, 'message': 'Quotation deleted successfully'})

@sales_bp.route('/quotations/<int:quotation_id>/duplicate', methods=['GET', 'POST'])
@login_required
def duplicate_quotation(quotation_id):
    """Duplicate quotation"""
    original_quotation = Quotation.query.filter_by(
        id=quotation_id, company_id=current_user.company.id
    ).first_or_404()
    
    # Generate new quotation number
    quotation_number = f"QT-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"
    
    # Create duplicate quotation
    duplicate_quotation = Quotation(
        company_id=current_user.company.id,
        customer_id=original_quotation.customer_id,
        quotation_number=quotation_number,
        subject=f"Copy of {original_quotation.subject}",
        valid_until=original_quotation.valid_until,
        notes=original_quotation.notes,
        subtotal=original_quotation.subtotal,
        tax_amount=original_quotation.tax_amount,
        total_amount=original_quotation.total_amount
    )
    
    db.session.add(duplicate_quotation)
    db.session.commit()
    
    # Log audit
    log_audit(current_user.company.id, current_user.id, 'quotation_duplicated', 
             f'Duplicated quotation: {duplicate_quotation.quotation_number}', 'quotation', duplicate_quotation.id)
    
    flash('Quotation duplicated successfully!', 'success')
    return redirect(url_for('sales.view_quotation', quotation_id=duplicate_quotation.id))

@sales_bp.route('/quotations/save', methods=['POST'])
@sales_bp.route('/quotations/<int:quotation_id>/save', methods=['POST'])
@login_required
def save_quotation(quotation_id=None):
    """Save quotation (create or update)"""
    form = QuotationForm()
    
    # Populate form choices
    customers = Customer.query.filter_by(company_id=current_user.company.id).all()
    form.customer.choices = [(c.id, f"{c.first_name} {c.last_name} - {c.company_name or c.email}") for c in customers]
    
    users = User.query.filter_by(company_id=current_user.company.id).all()
    form.sales_person.choices = [(u.id, f"{u.first_name} {u.last_name}") for u in users]
    
    if form.validate_on_submit():
        if quotation_id:
            # Update existing quotation
            quotation = Quotation.query.filter_by(
                id=quotation_id, company_id=current_user.company.id
            ).first_or_404()
            
            quotation.customer_id = form.customer.data
            quotation.subject = form.subject.data
            quotation.valid_until = form.valid_until.data
            quotation.notes = form.notes.data
            
            # Log audit
            log_audit(current_user.company.id, current_user.id, 'quotation_updated', 
                     f'Updated quotation: {quotation.quotation_number}', 'quotation', quotation.id)
            
            flash('Quotation updated successfully!', 'success')
        else:
            # Create new quotation
            quotation_number = f"QT-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"
            
            quotation = Quotation(
                company_id=current_user.company.id,
                customer_id=form.customer.data,
                quotation_number=quotation_number,
                subject=form.subject.data,
                valid_until=form.valid_until.data,
                notes=form.notes.data
            )
            
            db.session.add(quotation)
            
            # Log audit
            log_audit(current_user.company.id, current_user.id, 'quotation_created', 
                     f'Created quotation: {quotation.quotation_number}', 'quotation', quotation.id)
            
            flash('Quotation created successfully!', 'success')
        
        db.session.commit()
        return redirect(url_for('sales.view_quotation', quotation_id=quotation.id))
    
    # If form validation fails, redirect back to form
    if quotation_id:
        return redirect(url_for('sales.edit_quotation', quotation_id=quotation_id))
    else:
        return redirect(url_for('sales.new_quotation'))

# Invoice Management
@sales_bp.route('/invoices')
@login_required
def invoices():
    """List all invoices"""
    company = current_user.company
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    status_filter = request.args.get('status', '')
    
    query = Invoice.query.filter_by(company_id=company.id)
    
    if status_filter:
        query = query.filter(Invoice.status == status_filter)
    
    invoices = query.order_by(desc(Invoice.created_at)).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    # Get customers for filter dropdown
    customers = Customer.query.filter_by(company_id=company.id).all()
    
    # Get today's date for form defaults
    today = datetime.utcnow().date()
    
    return render_template('sales/invoices.html', 
                         invoices=invoices,
                         pagination=invoices,  # invoices is already a paginated object
                         customers=customers,
                         today=today,
                         title='Invoices')

@sales_bp.route('/invoices/new', methods=['GET', 'POST'])
@login_required
def new_invoice():
    """Create new invoice"""
    form = InvoiceForm()
    
    # Populate form choices
    customers = Customer.query.filter_by(company_id=current_user.company.id).all()
    form.customer.choices = [(c.id, f"{c.first_name} {c.last_name} - {c.company_name or c.email}") for c in customers]
    
    users = User.query.filter_by(company_id=current_user.company.id).all()
    form.sales_person.choices = [(u.id, f"{u.first_name} {u.last_name}") for u in users]
    
    if form.validate_on_submit():
        # Generate invoice number
        invoice_number = f"INV-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"
        
        invoice = Invoice(
            company_id=current_user.company.id,
            customer_id=form.customer.data,
            invoice_number=invoice_number,
            subject=form.subject.data,
            due_date=form.due_date.data,
            notes=form.notes.data
        )
        
        db.session.add(invoice)
        db.session.commit()
        
        # Log audit
        log_audit(current_user.company.id, current_user.id, 'invoice_created', 
                 f'Created invoice: {invoice.invoice_number}', 'invoice', invoice.id)
        
        flash('Invoice created successfully!', 'success')
        return redirect(url_for('sales.view_invoice', invoice_id=invoice.id))
    
    # Get products for selection
    products = Product.query.filter_by(company_id=current_user.company.id).all()
    
    return render_template('sales/invoice_form.html', 
                         form=form,
                         customers=customers,
                         products=products,
                         title='New Invoice')

@sales_bp.route('/invoices/<int:invoice_id>')
@login_required
def view_invoice(invoice_id):
    """View invoice details"""
    invoice = Invoice.query.filter_by(
        id=invoice_id, company_id=current_user.company.id
    ).first_or_404()
    
    return render_template('sales/invoice_detail.html', 
                         invoice=invoice,
                         title=f'Invoice: {invoice.invoice_number}')

@sales_bp.route('/invoices/<int:invoice_id>/pdf')
@login_required
def download_invoice_pdf(invoice_id):
    """Download invoice as PDF"""
    invoice = Invoice.query.filter_by(
        id=invoice_id, company_id=current_user.company.id
    ).first_or_404()
    
    pdf_path = generate_pdf_invoice(invoice)
    if pdf_path:
        return send_file(pdf_path, as_attachment=True, 
                        download_name=f"invoice_{invoice.invoice_number}.pdf")
    else:
        flash('Failed to generate PDF', 'error')
        return redirect(url_for('sales.view_invoice', invoice_id=invoice.id))

@sales_bp.route('/invoices/save', methods=['POST'])
@sales_bp.route('/invoices/<int:invoice_id>/save', methods=['POST'])
@login_required
def save_invoice(invoice_id=None):
    """Save invoice (create or update)"""
    form = InvoiceForm()
    
    if form.validate_on_submit():
        if invoice_id:
            # Update existing invoice
            invoice = Invoice.query.filter_by(
                id=invoice_id, company_id=current_user.company.id
            ).first_or_404()
            
            invoice.subject = form.subject.data
            invoice.due_date = form.due_date.data
            invoice.notes = form.notes.data
            
            # Log audit
            log_audit(current_user.company.id, current_user.id, 'invoice_updated', 
                     f'Updated invoice: {invoice.invoice_number}', 'invoice', invoice.id)
            
            flash('Invoice updated successfully!', 'success')
        else:
            # Create new invoice
            invoice_number = f"INV-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"
            
            invoice = Invoice(
                company_id=current_user.company.id,
                invoice_number=invoice_number,
                subject=form.subject.data,
                due_date=form.due_date.data,
                notes=form.notes.data
            )
            
            db.session.add(invoice)
            
            # Log audit
            log_audit(current_user.company.id, current_user.id, 'invoice_created', 
                     f'Created invoice: {invoice.invoice_number}', 'invoice', invoice.id)
            
            flash('Invoice created successfully!', 'success')
        
        db.session.commit()
        return redirect(url_for('sales.view_invoice', invoice_id=invoice.id))
    
    # If form validation fails, redirect back to form
    if invoice_id:
        return redirect(url_for('sales.edit_invoice', invoice_id=invoice_id))
    else:
        return redirect(url_for('sales.new_invoice'))

@sales_bp.route('/invoices/<int:invoice_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_invoice(invoice_id):
    """Edit invoice"""
    invoice = Invoice.query.filter_by(
        id=invoice_id, company_id=current_user.company.id
    ).first_or_404()
    
    form = InvoiceForm(obj=invoice)
    
    # Populate form choices
    customers = Customer.query.filter_by(company_id=current_user.company.id).all()
    form.customer.choices = [(c.id, f"{c.first_name} {c.last_name} - {c.company_name or c.email}") for c in customers]
    
    users = User.query.filter_by(company_id=current_user.company.id).all()
    form.sales_person.choices = [(u.id, f"{u.first_name} {u.last_name}") for u in users]
    
    if form.validate_on_submit():
        form.populate_obj(invoice)
        db.session.commit()
        
        # Log audit
        log_audit(current_user.company.id, current_user.id, 'invoice_updated', 
                 f'Updated invoice: {invoice.invoice_number}', 'invoice', invoice.id)
        
        flash('Invoice updated successfully!', 'success')
        return redirect(url_for('sales.view_invoice', invoice_id=invoice.id))
    
    # Get products for selection
    products = Product.query.filter_by(company_id=current_user.company.id).all()
    
    return render_template('sales/invoice_form.html', 
                         form=form,
                         invoice=invoice,
                         customers=customers,
                         products=products,
                         title='Edit Invoice')

@sales_bp.route('/invoices/<int:invoice_id>/duplicate', methods=['GET', 'POST'])
@login_required
def duplicate_invoice(invoice_id):
    """Duplicate invoice"""
    original_invoice = Invoice.query.filter_by(
        id=invoice_id, company_id=current_user.company.id
    ).first_or_404()
    
    # Generate new invoice number
    invoice_number = f"INV-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"
    
    # Create duplicate invoice
    duplicate_invoice = Invoice(
        company_id=current_user.company.id,
        customer_id=original_invoice.customer_id,
        invoice_number=invoice_number,
        subject=f"Copy of {original_invoice.subject}",
        due_date=original_invoice.due_date,
        notes=original_invoice.notes,
        subtotal=original_invoice.subtotal,
        tax_amount=original_invoice.tax_amount,
        total_amount=original_invoice.total_amount
    )
    
    db.session.add(duplicate_invoice)
    db.session.commit()
    
    # Log audit
    log_audit(current_user.company.id, current_user.id, 'invoice_duplicated', 
             f'Duplicated invoice: {duplicate_invoice.invoice_number}', 'invoice', duplicate_invoice.id)
    
    flash('Invoice duplicated successfully!', 'success')
    return redirect(url_for('sales.view_invoice', invoice_id=duplicate_invoice.id))

# Sales Pipeline (Kanban View)
@sales_bp.route('/pipeline')
@login_required
def sales_pipeline():
    """Sales pipeline kanban view"""
    company = current_user.company
    
    # Get leads grouped by status
    pipeline_data = {}
    for status in ['prospect', 'contacted', 'qualified', 'proposal', 'negotiation', 'closed_won', 'closed_lost']:
        leads = Lead.query.filter_by(
            company_id=company.id, status=status
        ).order_by(Lead.created_at).all()
        pipeline_data[status] = leads
    
    # Calculate pipeline stats for the summary cards
    pipeline_stats = {}
    for status in ['prospect', 'qualified', 'proposal', 'closed_won']:
        count = Lead.query.filter_by(
            company_id=company.id, status=status
        ).count()
        pipeline_stats[status] = count
    
    return render_template('sales/pipeline.html', 
                         pipeline_data=pipeline_data,
                         pipeline_stats=pipeline_stats,
                         title='Sales Pipeline')

# API endpoints for AJAX operations
@sales_bp.route('/api/leads/<int:lead_id>/assign', methods=['POST'])
@login_required
def assign_lead(lead_id):
    """Assign lead to user"""
    lead = Lead.query.filter_by(
        id=lead_id, company_id=current_user.company.id
    ).first_or_404()
    
    user_id = request.json.get('user_id')
    user = User.query.filter_by(
        id=user_id, company_id=current_user.company.id
    ).first()
    
    if user:
        lead.assigned_to_id = user_id
        db.session.commit()
        
        # Log audit
        log_audit(current_user.company.id, current_user.id, 'lead_assigned', 
                 f'Assigned lead to {user.get_full_name()}', 'lead', lead.id)
        
        return jsonify({'success': True, 'assigned_to': user.get_full_name()})
    
    return jsonify({'success': False, 'error': 'Invalid user'})

@sales_bp.route('/api/leads/<int:lead_id>/add-activity', methods=['POST'])
@login_required
def add_lead_activity(lead_id):
    """Add activity to lead"""
    lead = Lead.query.filter_by(
        id=lead_id, company_id=current_user.company.id
    ).first_or_404()
    
    data = request.json
    
    activity = Activity(
        company_id=current_user.company.id,
        user_id=current_user.id,
        lead_id=lead_id,
        activity_type=data.get('type'),
        subject=data.get('subject'),
        description=data.get('description'),
        scheduled_at=data.get('scheduled_at')
    )
    
    db.session.add(activity)
    db.session.commit()
    
    # Log audit
    log_audit(current_user.company.id, current_user.id, 'activity_added', 
             f'Added activity to lead: {data.get("type")}', 'lead', lead.id)
    
    return jsonify({'success': True, 'activity_id': activity.id})
