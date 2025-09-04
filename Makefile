.PHONY: help install setup test run clean docker-build docker-run docker-stop docker-logs deploy monitor logs backup restore

# Default target
help:
	@echo "SaaS ERP - Available Commands:"
	@echo ""
	@echo "Development:"
	@echo "  install     - Install Python dependencies"
	@echo "  setup       - Setup database and initial data"
	@echo "  run         - Run development server"
	@echo "  test        - Run test suite"
	@echo "  test-cov    - Run tests with coverage report"
	@echo "  lint        - Run code linting"
	@echo "  format      - Format code with black"
	@echo ""
	@echo "Docker:"
	@echo "  docker-build - Build Docker images"
	@echo "  docker-run   - Start all services with Docker Compose"
	@echo "  docker-stop  - Stop all Docker services"
	@echo "  docker-logs  - View Docker logs"
	@echo "  docker-shell - Open shell in web container"
	@echo ""
	@echo "Database:"
	@echo "  db-init     - Initialize database"
	@echo "  db-migrate  - Run database migrations"
	@echo "  db-upgrade  - Upgrade database to latest version"
	@echo "  db-downgrade - Downgrade database by one version"
	@echo "  db-reset    - Reset database (WARNING: destroys all data)"
	@echo ""
	@echo "Monitoring:"
	@echo "  monitor     - Start monitoring services"
	@echo "  monitor-stop - Stop monitoring services"
	@echo ""
	@echo "Deployment:"
	@echo "  deploy      - Deploy to production"
	@echo "  backup      - Create database backup"
	@echo "  restore     - Restore database from backup"
	@echo ""
	@echo "Maintenance:"
	@echo "  clean       - Clean up temporary files"
	@echo "  logs        - View application logs"
	@echo "  shell       - Open Flask shell"

# Development Commands
install:
	@echo "Installing Python dependencies..."
	pip install -r requirements.txt
	pip install -r requirements-dev.txt

setup:
	@echo "Setting up the application..."
	@if [ ! -f .env ]; then \
		echo "Creating .env file from template..."; \
		cp env.example .env; \
		echo "Please edit .env file with your configuration"; \
	fi
	@echo "Setting up database..."
	python setup.py
	@echo "Setup complete!"

run:
	@echo "Starting development server..."
	flask run --host=0.0.0.0 --port=5000 --debug

test:
	@echo "Running test suite..."
	pytest tests/ -v

test-cov:
	@echo "Running tests with coverage..."
	pytest tests/ -v --cov=app --cov-report=html --cov-report=term-missing

lint:
	@echo "Running code linting..."
	flake8 app/ tests/
	black --check app/ tests/
	isort --check-only app/ tests/

format:
	@echo "Formatting code..."
	black app/ tests/
	isort app/ tests/

# Docker Commands
docker-build:
	@echo "Building Docker images..."
	docker-compose build

docker-run:
	@echo "Starting Docker services..."
	docker-compose up -d

docker-stop:
	@echo "Stopping Docker services..."
	docker-compose down

docker-logs:
	@echo "Viewing Docker logs..."
	docker-compose logs -f

docker-shell:
	@echo "Opening shell in web container..."
	docker-compose exec web bash

# Database Commands
db-init:
	@echo "Initializing database..."
	docker-compose exec web flask db init

db-migrate:
	@echo "Creating database migration..."
	docker-compose exec web flask db migrate -m "$(message)"

db-upgrade:
	@echo "Upgrading database..."
	docker-compose exec web flask db upgrade

db-downgrade:
	@echo "Downgrading database..."
	docker-compose exec web flask db downgrade

db-reset:
	@echo "WARNING: This will destroy all data!"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		echo "Resetting database..."; \
		docker-compose exec web flask db downgrade base; \
		docker-compose exec web flask db upgrade; \
		python setup.py; \
	fi

# Monitoring Commands
monitor:
	@echo "Starting monitoring services..."
	cd monitoring && docker-compose -f docker-compose.monitoring.yml up -d

monitor-stop:
	@echo "Stopping monitoring services..."
	cd monitoring && docker-compose -f docker-compose.monitoring.yml down

# Deployment Commands
deploy:
	@echo "Deploying to production..."
	@if [ -z "$(env)" ]; then \
		echo "Usage: make deploy env=<environment>"; \
		echo "Available environments: docker-compose, kubernetes, cloud-run, ecs"; \
		exit 1; \
	fi
	./deploy.sh $(env)

backup:
	@echo "Creating database backup..."
	@mkdir -p backups
	docker-compose exec postgres pg_dump -U postgres saas_erp > backups/backup_$(shell date +%Y%m%d_%H%M%S).sql
	@echo "Backup created in backups/ directory"

restore:
	@echo "Restoring database from backup..."
	@if [ -z "$(file)" ]; then \
		echo "Usage: make restore file=<backup_file>"; \
		exit 1; \
	fi
	docker-compose exec -T postgres psql -U postgres saas_erp < backups/$(file)
	@echo "Database restored from $(file)"

# Maintenance Commands
clean:
	@echo "Cleaning up temporary files..."
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type f -name ".coverage" -delete
	rm -rf htmlcov/
	rm -rf .pytest_cache/
	rm -rf .coverage
	@echo "Cleanup complete!"

logs:
	@echo "Viewing application logs..."
	@if [ -d "logs" ]; then \
		tail -f logs/app.log; \
	else \
		echo "No logs directory found. Run the application first."; \
	fi

shell:
	@echo "Opening Flask shell..."
	flask shell

# Celery Commands
celery-worker:
	@echo "Starting Celery worker..."
	celery -A celery_app.celery worker --loglevel=info

celery-beat:
	@echo "Starting Celery beat scheduler..."
	celery -A celery_app.celery beat --loglevel=info

# Security Commands
security-check:
	@echo "Running security checks..."
	bandit -r app/
	safety check

# Performance Commands
profile:
	@echo "Profiling application..."
	python -m cProfile -o profile.stats app.py

analyze-profile:
	@echo "Analyzing profile data..."
	python -c "import pstats; p = pstats.Stats('profile.stats'); p.sort_stats('cumulative').print_stats(20)"

# Documentation Commands
docs:
	@echo "Generating documentation..."
	pdoc --html app/ --output-dir docs/
	@echo "Documentation generated in docs/ directory"

# Backup and Restore with S3 (if configured)
backup-s3:
	@echo "Creating backup and uploading to S3..."
	@if [ -z "$(bucket)" ]; then \
		echo "Usage: make backup-s3 bucket=<s3_bucket_name>"; \
		exit 1; \
	fi
	$(MAKE) backup
	aws s3 sync backups/ s3://$(bucket)/backups/
	@echo "Backup uploaded to S3"

restore-s3:
	@echo "Downloading backup from S3 and restoring..."
	@if [ -z "$(bucket)" ] || [ -z "$(file)" ]; then \
		echo "Usage: make restore-s3 bucket=<s3_bucket_name> file=<backup_file>"; \
		exit 1; \
	fi
	aws s3 cp s3://$(bucket)/backups/$(file) backups/
	$(MAKE) restore file=$(file)
	@echo "Database restored from S3 backup"

# Health Check
health:
	@echo "Checking application health..."
	@if curl -f http://localhost:5000/health > /dev/null 2>&1; then \
		echo "✅ Application is healthy"; \
	else \
		echo "❌ Application is not responding"; \
		exit 1; \
	fi

# Quick Start for Development
dev-setup: install setup
	@echo "Development environment setup complete!"
	@echo "Run 'make run' to start the development server"

# Production Setup
prod-setup: docker-build docker-run
	@echo "Waiting for services to be ready..."
	@sleep 30
	@echo "Production environment setup complete!"
	@echo "Run 'make monitor' to start monitoring services"

# Full Test Suite
test-full: lint test-cov security-check
	@echo "Full test suite completed!"

# Emergency Commands
emergency-stop:
	@echo "EMERGENCY: Stopping all services..."
	docker-compose down --volumes --remove-orphans
	cd monitoring && docker-compose -f docker-compose.monitoring.yml down --volumes --remove-orphans
	@echo "All services stopped!"

emergency-restart:
	@echo "EMERGENCY: Restarting all services..."
	$(MAKE) emergency-stop
	$(MAKE) prod-setup
	@echo "All services restarted!"
