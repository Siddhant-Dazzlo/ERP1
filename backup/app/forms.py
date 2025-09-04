from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, SelectField, TextAreaField, DecimalField, IntegerField, DateField, FileField
from wtforms.validators import DataRequired, Email, Length, EqualTo, ValidationError, Optional
from app.models import User, Company

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=80)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    first_name = StringField('First Name', validators=[DataRequired(), Length(max=50)])
    last_name = StringField('Last Name', validators=[DataRequired(), Length(max=50)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=8)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')
    
    def validate_email(self, field):
        if User.query.filter_by(email=field.data).first():
            raise ValidationError('Email already registered.')
    
    def validate_username(self, field):
        if User.query.filter_by(username=field.data).first():
            raise ValidationError('Username already taken.')

class UserInviteForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=80)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    first_name = StringField('First Name', validators=[DataRequired(), Length(max=50)])
    last_name = StringField('Last Name', validators=[DataRequired(), Length(max=50)])
    role = SelectField('Role', validators=[DataRequired()], choices=[
        ('sales_executive', 'Sales Executive'),
        ('manager', 'Manager'),
        ('admin', 'Admin')
    ])
    submit = SubmitField('Send Invitation')
    
    def validate_email(self, field):
        if User.query.filter_by(email=field.data).first():
            raise ValidationError('User with this email already exists.')
    
    def validate_username(self, field):
        if User.query.filter_by(username=field.data).first():
            raise ValidationError('Username already taken.')

class LeadForm(FlaskForm):
    first_name = StringField('First Name', validators=[DataRequired(), Length(max=50)])
    last_name = StringField('Last Name', validators=[DataRequired(), Length(max=50)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    phone = StringField('Phone', validators=[Optional(), Length(max=20)])
    company_name = StringField('Company Name', validators=[Optional(), Length(max=100)])
    job_title = StringField('Job Title', validators=[Optional(), Length(max=100)])
    industry = StringField('Industry', validators=[Optional(), Length(max=100)])
    source = SelectField('Source', validators=[DataRequired()], choices=[
        ('website', 'Website'),
        ('referral', 'Referral'),
        ('cold_call', 'Cold Call'),
        ('social_media', 'Social Media'),
        ('email_campaign', 'Email Campaign'),
        ('other', 'Other')
    ])
    estimated_value = DecimalField('Estimated Value', validators=[Optional()])
    notes = TextAreaField('Notes')
    next_follow_up = DateField('Next Follow Up', validators=[Optional()])
    submit = SubmitField('Save Lead')

class CustomerForm(FlaskForm):
    first_name = StringField('First Name', validators=[DataRequired(), Length(max=50)])
    last_name = StringField('Last Name', validators=[DataRequired(), Length(max=50)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    phone = StringField('Phone', validators=[Optional(), Length(max=20)])
    company_name = StringField('Company Name', validators=[Optional(), Length(max=100)])
    address = TextAreaField('Address')
    tax_id = StringField('Tax ID', validators=[Optional(), Length(max=50)])
    credit_limit = DecimalField('Credit Limit', validators=[Optional()])
    payment_terms = StringField('Payment Terms', validators=[Optional(), Length(max=100)])
    submit = SubmitField('Save Customer')

class ProductForm(FlaskForm):
    name = StringField('Product Name', validators=[DataRequired(), Length(max=200)])
    description = TextAreaField('Description')
    sku = StringField('SKU', validators=[Optional(), Length(max=100)])
    category = StringField('Category', validators=[Optional(), Length(max=100)])
    unit_price = DecimalField('Unit Price', validators=[DataRequired()])
    cost_price = DecimalField('Cost Price', validators=[Optional()])
    tax_rate = DecimalField('Tax Rate (%)', validators=[Optional()])
    submit = SubmitField('Save Product')

class QuotationForm(FlaskForm):
    quotation_number = StringField('Quotation Number', validators=[Optional(), Length(max=50)])
    quotation_date = DateField('Quotation Date', validators=[Optional()])
    customer = SelectField('Customer', validators=[DataRequired()], coerce=int)
    subject = StringField('Subject', validators=[DataRequired(), Length(max=200)])
    valid_until = DateField('Valid Until', validators=[Optional()])
    status = SelectField('Status', validators=[Optional()], choices=[
        ('draft', 'Draft'),
        ('sent', 'Sent'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
        ('converted', 'Converted')
    ])
    sales_person = SelectField('Sales Person', validators=[Optional()], coerce=int)
    currency = SelectField('Currency', validators=[Optional()], choices=[
        ('USD', 'USD'),
        ('INR', 'INR'),
        ('EUR', 'EUR'),
        ('GBP', 'GBP')
    ])
    tax_rate = DecimalField('Tax Rate (%)', validators=[Optional()])
    terms_conditions = TextAreaField('Terms & Conditions')
    notes = TextAreaField('Notes')
    submit = SubmitField('Save Quotation')

class InvoiceForm(FlaskForm):
    invoice_number = StringField('Invoice Number', validators=[Optional(), Length(max=50)])
    invoice_date = DateField('Invoice Date', validators=[Optional()])
    customer = SelectField('Customer', validators=[DataRequired()], coerce=int)
    subject = StringField('Subject', validators=[DataRequired(), Length(max=200)])
    due_date = DateField('Due Date', validators=[Optional()])
    status = SelectField('Status', validators=[Optional()], choices=[
        ('draft', 'Draft'),
        ('sent', 'Sent'),
        ('paid', 'Paid'),
        ('overdue', 'Overdue')
    ])
    sales_person = SelectField('Sales Person', validators=[Optional()], coerce=int)
    currency = SelectField('Currency', validators=[Optional()], choices=[
        ('USD', 'USD'),
        ('INR', 'INR'),
        ('EUR', 'EUR'),
        ('GBP', 'GBP')
    ])
    tax_rate = DecimalField('Tax Rate (%)', validators=[Optional()])
    payment_terms = SelectField('Payment Terms', validators=[Optional()], choices=[
        ('net_15', 'Net 15'),
        ('net_30', 'Net 30'),
        ('net_45', 'Net 45'),
        ('net_60', 'Net 60'),
        ('due_on_receipt', 'Due on Receipt')
    ])
    payment_method = SelectField('Payment Method', validators=[Optional()], choices=[
        ('bank_transfer', 'Bank Transfer'),
        ('credit_card', 'Credit Card'),
        ('check', 'Check'),
        ('cash', 'Cash'),
        ('paypal', 'PayPal')
    ])
    billing_address = TextAreaField('Billing Address')
    shipping_address = TextAreaField('Shipping Address')
    same_as_billing = BooleanField('Same as Billing Address')
    terms_conditions = TextAreaField('Terms & Conditions')
    notes = TextAreaField('Notes')
    submit = SubmitField('Save Invoice')

class TaskForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired(), Length(max=200)])
    description = TextAreaField('Description')
    priority = SelectField('Priority', validators=[DataRequired()], choices=[
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent')
    ])
    due_date = DateField('Due Date', validators=[Optional()])
    submit = SubmitField('Save Task')

class ActivityForm(FlaskForm):
    activity_type = SelectField('Activity Type', validators=[DataRequired()], choices=[
        ('call', 'Call'),
        ('email', 'Email'),
        ('meeting', 'Meeting'),
        ('note', 'Note'),
        ('demo', 'Demo'),
        ('proposal', 'Proposal')
    ])
    subject = StringField('Subject', validators=[DataRequired(), Length(max=200)])
    description = TextAreaField('Description')
    scheduled_at = DateField('Scheduled At', validators=[Optional()])
    submit = SubmitField('Save Activity')

class CompanyForm(FlaskForm):
    name = StringField('Company Name', validators=[DataRequired(), Length(max=100)])
    subdomain = StringField('Subdomain', validators=[DataRequired(), Length(max=50)])
    domain = StringField('Domain', validators=[DataRequired(), Length(max=100)])
    address = TextAreaField('Address')
    phone = StringField('Phone', validators=[Optional(), Length(max=20)])
    email = StringField('Email', validators=[Optional(), Email()])
    website = StringField('Website', validators=[Optional(), Length(max=200)])
    logo = FileField('Company Logo')
    submit = SubmitField('Save Company')

class SearchForm(FlaskForm):
    search = StringField('Search', validators=[Optional()])
    submit = SubmitField('Search')

class FilterForm(FlaskForm):
    status = SelectField('Status', validators=[Optional()], choices=[
        ('', 'All Statuses'),
        ('prospect', 'Prospect'),
        ('contacted', 'Contacted'),
        ('qualified', 'Qualified'),
        ('proposal', 'Proposal'),
        ('negotiation', 'Negotiation'),
        ('closed_won', 'Closed Won'),
        ('closed_lost', 'Closed Lost')
    ])
    source = SelectField('Source', validators=[Optional()], choices=[
        ('', 'All Sources'),
        ('website', 'Website'),
        ('referral', 'Referral'),
        ('cold_call', 'Cold Call'),
        ('social_media', 'Social Media'),
        ('email_campaign', 'Email Campaign'),
        ('other', 'Other')
    ])
    assigned_to = SelectField('Assigned To', validators=[Optional()], choices=[
        ('', 'All Users')
    ])
    submit = SubmitField('Apply Filters')
