#!/bin/bash

# SaaS ERP Deployment Script
# This script deploys the application to production

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
APP_NAME="saas-erp"
DOCKER_REGISTRY="your-registry.com"
DOCKER_IMAGE="$DOCKER_REGISTRY/$APP_NAME"
VERSION=$(git describe --tags --always --dirty)
ENVIRONMENT=${1:-production}

echo -e "${BLUE}🚀 Deploying SaaS ERP to $ENVIRONMENT${NC}"
echo -e "${BLUE}Version: $VERSION${NC}"
echo ""

# Function to print colored output
print_status() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    # Check if Docker is running
    if ! docker info > /dev/null 2>&1; then
        print_error "Docker is not running"
        exit 1
    fi
    
    # Check if docker-compose is available
    if ! command -v docker-compose &> /dev/null; then
        print_error "docker-compose is not installed"
        exit 1
    fi
    
    # Check if .env file exists
    if [ ! -f .env ]; then
        print_error ".env file not found. Please copy env.example to .env and configure it."
        exit 1
    fi
    
    print_status "Prerequisites check passed"
}

# Build Docker image
build_image() {
    print_status "Building Docker image..."
    
    docker build -t $DOCKER_IMAGE:$VERSION .
    docker tag $DOCKER_IMAGE:$VERSION $DOCKER_IMAGE:latest
    
    print_status "Docker image built successfully"
}

# Push Docker image
push_image() {
    print_status "Pushing Docker image to registry..."
    
    docker push $DOCKER_IMAGE:$VERSION
    docker push $DOCKER_IMAGE:latest
    
    print_status "Docker image pushed successfully"
}

# Deploy with Docker Compose
deploy_docker_compose() {
    print_status "Deploying with Docker Compose..."
    
    # Stop existing services
    docker-compose down
    
    # Pull latest images
    docker-compose pull
    
    # Start services
    docker-compose up -d
    
    # Wait for services to be healthy
    print_status "Waiting for services to be healthy..."
    sleep 30
    
    # Check service health
    if docker-compose ps | grep -q "unhealthy"; then
        print_error "Some services are unhealthy. Check logs with: docker-compose logs"
        exit 1
    fi
    
    print_status "Docker Compose deployment completed"
}

# Deploy to Kubernetes
deploy_kubernetes() {
    print_status "Deploying to Kubernetes..."
    
    # Update image tag in deployment
    sed -i "s|image: $DOCKER_IMAGE:.*|image: $DOCKER_IMAGE:$VERSION|g" k8s/deployment.yaml
    
    # Apply Kubernetes manifests
    kubectl apply -f k8s/
    
    # Wait for deployment to be ready
    kubectl rollout status deployment/$APP_NAME
    
    print_status "Kubernetes deployment completed"
}

# Deploy to Cloud Run (GCP)
deploy_cloud_run() {
    print_status "Deploying to Cloud Run..."
    
    # Build and push to Google Container Registry
    gcloud builds submit --tag gcr.io/$GCP_PROJECT/$APP_NAME:$VERSION .
    
    # Deploy to Cloud Run
    gcloud run deploy $APP_NAME \
        --image gcr.io/$GCP_PROJECT/$APP_NAME:$VERSION \
        --platform managed \
        --region $GCP_REGION \
        --allow-unauthenticated \
        --memory 2Gi \
        --cpu 2 \
        --max-instances 10
    
    print_status "Cloud Run deployment completed"
}

# Deploy to AWS ECS
deploy_ecs() {
    print_status "Deploying to AWS ECS..."
    
    # Update ECS task definition
    aws ecs register-task-definition \
        --cli-input-json file://aws/task-definition.json
    
    # Update ECS service
    aws ecs update-service \
        --cluster $ECS_CLUSTER \
        --service $ECS_SERVICE \
        --task-definition $APP_NAME
    
    print_status "ECS deployment completed"
}

# Run database migrations
run_migrations() {
    print_status "Running database migrations..."
    
    # Run migrations in a temporary container
    docker run --rm \
        --env-file .env \
        --network saas_erp_network \
        $DOCKER_IMAGE:$VERSION \
        flask db upgrade
    
    print_status "Database migrations completed"
}

# Health check
health_check() {
    print_status "Performing health check..."
    
    # Wait for application to be ready
    sleep 10
    
    # Check application health
    if curl -f http://localhost:5000/health > /dev/null 2>&1; then
        print_status "Application health check passed"
    else
        print_error "Application health check failed"
        exit 1
    fi
}

# Backup database
backup_database() {
    print_status "Creating database backup..."
    
    # Create backup directory
    mkdir -p backups
    
    # Create backup
    docker exec saas_erp_postgres pg_dump -U postgres saas_erp > backups/backup_$(date +%Y%m%d_%H%M%S).sql
    
    print_status "Database backup completed"
}

# Rollback function
rollback() {
    print_warning "Rolling back to previous version..."
    
    # Stop current services
    docker-compose down
    
    # Start previous version
    docker-compose up -d
    
    print_status "Rollback completed"
}

# Main deployment function
main() {
    echo -e "${BLUE}Starting deployment process...${NC}"
    
    # Check prerequisites
    check_prerequisites
    
    # Create backup
    backup_database
    
    # Build and push image
    build_image
    push_image
    
    # Deploy based on environment
    case $ENVIRONMENT in
        "docker-compose")
            deploy_docker_compose
            ;;
        "kubernetes")
            deploy_kubernetes
            ;;
        "cloud-run")
            deploy_cloud_run
            ;;
        "ecs")
            deploy_ecs
            ;;
        *)
            print_error "Unknown deployment method: $ENVIRONMENT"
            print_status "Available methods: docker-compose, kubernetes, cloud-run, ecs"
            exit 1
            ;;
    esac
    
    # Run migrations
    run_migrations
    
    # Health check
    health_check
    
    echo -e "${GREEN}🎉 Deployment completed successfully!${NC}"
    echo -e "${BLUE}Version: $VERSION${NC}"
    echo -e "${BLUE}Environment: $ENVIRONMENT${NC}"
}

# Error handling
trap 'print_error "Deployment failed. Rolling back..."; rollback; exit 1' ERR

# Run main function
main "$@"
