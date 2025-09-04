-- Initialize SaaS ERP Database
-- This script sets up the initial database structure and sample data

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Create initial company (platform owner)
INSERT INTO companies (name, subdomain, domain, subscription_plan, max_users, max_storage_gb, is_active, created_at, updated_at)
VALUES (
    'Sales ERP Platform',
    'admin',
    'saas-erp.com',
    'enterprise',
    1000,
    1000,
    true,
    NOW(),
    NOW()
) ON CONFLICT (subdomain) DO NOTHING;

-- Create platform admin user
INSERT INTO users (company_id, email, username, first_name, last_name, password_hash, role, is_active, created_at, updated_at)
VALUES (
    1,
    'admin@saas-erp.com',
    'platform_admin',
    'Platform',
    'Administrator',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj4J/8QqHqGm', -- password: admin123
    'admin',
    true,
    NOW(),
    NOW()
) ON CONFLICT (email) DO NOTHING;

-- Create sample company for demonstration
INSERT INTO companies (name, subdomain, domain, subscription_plan, max_users, max_storage_gb, is_active, created_at, updated_at)
VALUES (
    'Demo Company',
    'demo',
    'saas-erp.com',
    'pro',
    20,
    100,
    true,
    NOW(),
    NOW()
) ON CONFLICT (subdomain) DO NOTHING;

-- Create sample users for demo company
INSERT INTO users (company_id, email, username, first_name, last_name, password_hash, role, is_active, created_at, updated_at)
VALUES 
    (2, 'manager@demo.com', 'demo_manager', 'John', 'Manager', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj4J/8QqHqGm', 'manager', true, NOW(), NOW()),
    (2, 'sales1@demo.com', 'demo_sales1', 'Sarah', 'Sales', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj4J/8QqHqGm', 'sales_executive', true, NOW(), NOW()),
    (2, 'sales2@demo.com', 'demo_sales2', 'Mike', 'Sales', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj4J/8QqHqGm', 'sales_executive', true, NOW(), NOW())
ON CONFLICT (email) DO NOTHING;

-- Create sample products for demo company
INSERT INTO products (company_id, name, description, sku, category, unit_price, cost_price, tax_rate, is_active, created_at, updated_at)
VALUES 
    (2, 'Premium Software License', 'Enterprise software license with full features', 'SW-LIC-001', 'Software', 999.99, 200.00, 18.00, true, NOW(), NOW()),
    (2, 'Technical Support Package', '24/7 technical support for 1 year', 'SUP-001', 'Support', 299.99, 50.00, 18.00, true, NOW(), NOW()),
    (2, 'Training Session', 'On-site training session for team', 'TRAIN-001', 'Training', 499.99, 100.00, 18.00, true, NOW(), NOW()),
    (2, 'Custom Development', 'Custom feature development', 'DEV-001', 'Development', 1999.99, 800.00, 18.00, true, NOW(), NOW())
ON CONFLICT (sku) DO NOTHING;

-- Create sample leads for demo company
INSERT INTO leads (company_id, assigned_to_id, first_name, last_name, email, phone, company_name, job_title, industry, source, status, estimated_value, notes, created_at, updated_at)
VALUES 
    (2, 3, 'Alice', 'Johnson', 'alice@techcorp.com', '+1234567890', 'TechCorp Inc', 'CTO', 'Technology', 'website', 'qualified', 5000.00, 'Interested in enterprise solution', NOW(), NOW()),
    (2, 3, 'Bob', 'Smith', 'bob@innovate.com', '+1234567891', 'Innovate Solutions', 'CEO', 'Technology', 'referral', 'proposal', 8000.00, 'Looking for custom development', NOW(), NOW()),
    (2, 4, 'Carol', 'Davis', 'carol@startup.com', '+1234567892', 'StartupXYZ', 'Founder', 'Technology', 'cold_call', 'contacted', 3000.00, 'Startup with limited budget', NOW(), NOW()),
    (2, 4, 'David', 'Wilson', 'david@enterprise.com', '+1234567893', 'Enterprise Corp', 'IT Director', 'Manufacturing', 'social_media', 'prospect', 15000.00, 'Large enterprise client', NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Create sample customers for demo company
INSERT INTO customers (company_id, lead_id, first_name, last_name, email, phone, company_name, address, tax_id, credit_limit, payment_terms, created_at, updated_at)
VALUES 
    (2, 1, 'Alice', 'Johnson', 'alice@techcorp.com', '+1234567890', 'TechCorp Inc', '123 Tech Street, Silicon Valley, CA 94025', 'TAX123456', 10000.00, 'Net 30', NOW(), NOW()),
    (2, 2, 'Bob', 'Smith', 'bob@innovate.com', '+1234567891', 'Innovate Solutions', '456 Innovation Ave, Austin, TX 73301', 'TAX789012', 15000.00, 'Net 30', NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Create sample quotations
INSERT INTO quotations (company_id, customer_id, quotation_number, subject, valid_until, subtotal, tax_amount, total_amount, status, notes, created_at, updated_at)
VALUES 
    (2, 1, 'QT-20241201-ABC12345', 'Enterprise Software Package', NOW() + INTERVAL '30 days', 1999.98, 359.99, 2359.97, 'sent', 'Includes software license and support package', NOW(), NOW()),
    (2, 2, 'QT-20241201-DEF67890', 'Custom Development Project', NOW() + INTERVAL '30 days', 3999.98, 719.99, 4719.97, 'accepted', 'Custom feature development for existing system', NOW(), NOW())
ON CONFLICT (quotation_number) DO NOTHING;

-- Create quotation items
INSERT INTO quotation_items (quotation_id, product_id, description, quantity, unit_price, discount_percent, tax_rate, total_amount)
VALUES 
    (1, 1, 'Premium Software License', 1, 999.99, 0.00, 18.00, 999.99),
    (1, 2, 'Technical Support Package', 1, 299.99, 0.00, 18.00, 299.99),
    (2, 4, 'Custom Development', 1, 1999.99, 0.00, 18.00, 1999.99),
    (2, 3, 'Training Session', 1, 499.99, 0.00, 18.00, 499.99)
ON CONFLICT DO NOTHING;

-- Create sample invoices
INSERT INTO invoices (company_id, customer_id, quotation_id, invoice_number, subject, due_date, subtotal, tax_amount, total_amount, status, created_at, updated_at)
VALUES 
    (2, 1, 1, 'INV-20241201-ABC12345', 'Enterprise Software Package', NOW() + INTERVAL '30 days', 1999.98, 359.99, 2359.97, 'sent', NOW(), NOW()),
    (2, 2, 2, 'INV-20241201-DEF67890', 'Custom Development Project', NOW() + INTERVAL '30 days', 3999.98, 719.99, 4719.97, 'sent', NOW(), NOW())
ON CONFLICT (invoice_number) DO NOTHING;

-- Create invoice items
INSERT INTO invoice_items (invoice_id, product_id, description, quantity, unit_price, discount_percent, tax_rate, total_amount)
VALUES 
    (1, 1, 'Premium Software License', 1, 999.99, 0.00, 18.00, 999.99),
    (1, 2, 'Technical Support Package', 1, 299.99, 0.00, 18.00, 299.99),
    (2, 4, 'Custom Development', 1, 1999.99, 0.00, 18.00, 1999.99),
    (2, 3, 'Training Session', 1, 499.99, 0.00, 18.00, 499.99)
ON CONFLICT DO NOTHING;

-- Create sample tasks
INSERT INTO tasks (company_id, assigned_to_id, title, description, priority, status, due_date, created_at, updated_at)
VALUES 
    (2, 3, 'Follow up with TechCorp', 'Call Alice to discuss enterprise requirements', 'high', 'pending', NOW() + INTERVAL '2 days', NOW(), NOW()),
    (2, 4, 'Prepare proposal for StartupXYZ', 'Create detailed proposal for startup package', 'medium', 'in_progress', NOW() + INTERVAL '5 days', NOW(), NOW()),
    (2, 3, 'Demo for Enterprise Corp', 'Schedule product demo for David Wilson', 'high', 'pending', NOW() + INTERVAL '3 days', NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Create sample activities
INSERT INTO activities (company_id, user_id, lead_id, customer_id, activity_type, subject, description, scheduled_at, created_at)
VALUES 
    (2, 3, 1, NULL, 'call', 'Initial Contact', 'Called Alice to understand requirements', NOW() - INTERVAL '2 days', NOW()),
    (2, 3, 1, NULL, 'meeting', 'Requirements Discussion', 'Met with Alice to discuss technical requirements', NOW() - INTERVAL '1 day', NOW()),
    (2, 4, 3, NULL, 'call', 'Cold Call Follow-up', 'Called Carol to discuss startup package', NOW() - INTERVAL '1 day', NOW()),
    (2, 3, 4, NULL, 'email', 'Initial Outreach', 'Sent introductory email to David', NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Create subscription records
INSERT INTO subscriptions (company_id, plan, status, current_period_start, current_period_end, created_at, updated_at)
VALUES 
    (1, 'enterprise', 'active', NOW(), NOW() + INTERVAL '1 year', NOW(), NOW()),
    (2, 'pro', 'active', NOW(), NOW() + INTERVAL '1 month', NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Create audit log entries
INSERT INTO audit_logs (company_id, user_id, action, resource_type, resource_id, details, ip_address, user_agent, created_at)
VALUES 
    (1, 1, 'system_initialization', 'system', NULL, '{"message": "System initialized"}', '127.0.0.1', 'System', NOW()),
    (2, 2, 'company_created', 'company', 2, '{"message": "Demo company created"}', '127.0.0.1', 'System', NOW()),
    (2, 2, 'user_created', 'user', 3, '{"message": "Demo manager created"}', '127.0.0.1', 'System', NOW())
ON CONFLICT DO NOTHING;

-- Update sequences
SELECT setval('companies_id_seq', (SELECT MAX(id) FROM companies));
SELECT setval('users_id_seq', (SELECT MAX(id) FROM users));
SELECT setval('leads_id_seq', (SELECT MAX(id) FROM leads));
SELECT setval('customers_id_seq', (SELECT MAX(id) FROM customers));
SELECT setval('products_id_seq', (SELECT MAX(id) FROM products));
SELECT setval('quotations_id_seq', (SELECT MAX(id) FROM quotations));
SELECT setval('invoices_id_seq', (SELECT MAX(id) FROM invoices));
SELECT setval('tasks_id_seq', (SELECT MAX(id) FROM tasks));
SELECT setval('activities_id_seq', (SELECT MAX(id) FROM activities));
SELECT setval('subscriptions_id_seq', (SELECT MAX(id) FROM subscriptions));
SELECT setval('audit_logs_id_seq', (SELECT MAX(id) FROM audit_logs));

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_leads_company_status ON leads(company_id, status);
CREATE INDEX IF NOT EXISTS idx_leads_assigned_to ON leads(assigned_to_id);
CREATE INDEX IF NOT EXISTS idx_customers_company ON customers(company_id);
CREATE INDEX IF NOT EXISTS idx_products_company ON products(company_id);
CREATE INDEX IF NOT EXISTS idx_quotations_company ON quotations(company_id);
CREATE INDEX IF NOT EXISTS idx_invoices_company ON invoices(company_id);
CREATE INDEX IF NOT EXISTS idx_tasks_company ON tasks(company_id);
CREATE INDEX IF NOT EXISTS idx_activities_company ON activities(company_id);
CREATE INDEX IF NOT EXISTS idx_users_company ON users(company_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_company ON audit_logs(company_id);

-- Create full-text search indexes
CREATE INDEX IF NOT EXISTS idx_leads_search ON leads USING gin(to_tsvector('english', first_name || ' ' || last_name || ' ' || COALESCE(company_name, '') || ' ' || COALESCE(email, '')));
CREATE INDEX IF NOT EXISTS idx_customers_search ON customers USING gin(to_tsvector('english', first_name || ' ' || last_name || ' ' || COALESCE(company_name, '') || ' ' || COALESCE(email, '')));
CREATE INDEX IF NOT EXISTS idx_products_search ON products USING gin(to_tsvector('english', name || ' ' || COALESCE(description, '') || ' ' || COALESCE(sku, '')));

-- Grant permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO postgres;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO postgres;

-- Print completion message
DO $$
BEGIN
    RAISE NOTICE 'SaaS ERP Database initialized successfully!';
    RAISE NOTICE 'Default admin credentials: admin@saas-erp.com / admin123';
    RAISE NOTICE 'Demo company: demo.saas-erp.com';
    RAISE NOTICE 'Demo user: manager@demo.com / admin123';
END $$;
