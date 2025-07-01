#!/bin/bash

# =============================================================================
# AUTOMATED TRADING BOT - DEPLOYMENT MIGRATION SCRIPT
# =============================================================================
# This script deploys today's changes to the DigitalOcean droplet
# Run this script on your droplet via SSH
# =============================================================================

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_DIR="/opt/automated-trading-bot"  # Your actual project path
BACKUP_DIR="/var/backups/trading-bot"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_NAME="backup_${TIMESTAMP}"

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if running as root or with sudo
check_permissions() {
    if [[ $EUID -eq 0 ]]; then
        print_status "Running as root"
    elif sudo -n true 2>/dev/null; then
        print_status "Running with sudo privileges"
    else
        print_error "This script requires root privileges or sudo access"
        exit 1
    fi
}

# Function to create backup
create_backup() {
    print_status "Creating backup of current deployment..."
    
    # Create backup directory if it doesn't exist
    sudo mkdir -p "$BACKUP_DIR"
    
    # Stop services before backup
    print_status "Stopping services for backup..."
    sudo docker-compose -f "$PROJECT_DIR/docker-compose.yml" down || true
    
    # Create backup
    sudo tar -czf "$BACKUP_DIR/$BACKUP_NAME.tar.gz" -C "$(dirname $PROJECT_DIR)" "$(basename $PROJECT_DIR)"
    
    print_success "Backup created: $BACKUP_DIR/$BACKUP_NAME.tar.gz"
}

# Function to update code from GitHub
update_code() {
    print_status "Updating code from GitHub..."
    
    cd "$PROJECT_DIR"
    
    # Stash any local changes
    sudo git stash push -m "Auto-stash before migration $TIMESTAMP" || true
    
    # Fetch latest changes
    sudo git fetch origin
    
    # Show current commit
    print_status "Current commit: $(git rev-parse --short HEAD)"
    
    # Pull latest changes
    sudo git pull origin main
    
    # Show new commit
    print_success "Updated to commit: $(git rev-parse --short HEAD)"
    
    # Show what changed
    print_status "Recent commits:"
    git log --oneline -5
}

# Function to update Python dependencies
update_dependencies() {
    print_status "Checking for new Python dependencies..."
    
    cd "$PROJECT_DIR/backend"
    
    # Check if requirements.txt changed
    if git diff HEAD~1 HEAD --name-only | grep -q "requirements.txt"; then
        print_status "Requirements.txt changed, rebuilding Docker images..."
        return 0
    else
        print_status "No changes in requirements.txt"
        return 1
    fi
}

# Function to run database migrations
run_migrations() {
    print_status "Running database migrations..."
    
    cd "$PROJECT_DIR"
    
    # Start only database services first
    sudo docker-compose up -d postgres redis rabbitmq
    
    # Wait for database to be ready
    print_status "Waiting for database to be ready..."
    sleep 10
    
    # Run migrations
    sudo docker-compose exec -T backend python manage.py migrate
    
    print_success "Database migrations completed"
}

# Function to rebuild and restart services
restart_services() {
    print_status "Rebuilding and restarting services..."
    
    cd "$PROJECT_DIR"
    
    # Build and start all services
    sudo docker-compose down
    sudo docker-compose build --no-cache
    sudo docker-compose up -d
    
    # Wait for services to start
    print_status "Waiting for services to start..."
    sleep 30
    
    # Check service health
    check_service_health
}

# Function to check service health
check_service_health() {
    print_status "Checking service health..."
    
    # Check if containers are running
    print_status "Container status:"
    sudo docker-compose ps
    
    # Test API endpoints
    print_status "Testing API endpoints..."
    
    # Wait a bit more for services to be fully ready
    sleep 15
    
    # Test main API
    if curl -f -s http://localhost:8000/api/v1/health > /dev/null; then
        print_success "✅ Main API is healthy"
    else
        print_warning "⚠️  Main API check failed"
    fi
    
    # Test new endpoints we added today
    if curl -f -s http://localhost:8000/api/v1/trade-analytics/health > /dev/null; then
        print_success "✅ Trade Analytics API is healthy"
    else
        print_warning "⚠️  Trade Analytics API check failed"
    fi
    
    if curl -f -s http://localhost:8000/api/v1/grid-trading/health > /dev/null; then
        print_success "✅ Grid Trading API is healthy"
    else
        print_warning "⚠️  Grid Trading API check failed"
    fi
}

# Function to run post-deployment tasks
post_deployment_tasks() {
    print_status "Running post-deployment tasks..."
    
    cd "$PROJECT_DIR"
    
    # Collect static files
    sudo docker-compose exec -T backend python manage.py collectstatic --noinput || true
    
    # Create superuser if needed (interactive, so skip in automated mode)
    # sudo docker-compose exec backend python manage.py createsuperuser
    
    # Restart Celery services to pick up new tasks
    sudo docker-compose restart celery_worker celery_beat
    
    print_success "Post-deployment tasks completed"
}

# Function to show deployment summary
show_summary() {
    print_success "=============================================================================
DEPLOYMENT COMPLETED SUCCESSFULLY!
============================================================================="
    
    echo -e "📅 Deployment Time: ${GREEN}$TIMESTAMP${NC}"
    echo -e "💾 Backup Location: ${GREEN}$BACKUP_DIR/$BACKUP_NAME.tar.gz${NC}"
    echo -e "🌐 Dashboard URL: ${GREEN}http://209.38.34.59/dashboard${NC}"
    echo -e "🔗 API Base URL: ${GREEN}http://209.38.34.59/api/v1/${NC}"
    
    echo -e "\n${BLUE}New Features Deployed Today:${NC}"
    echo -e "✅ Enhanced Trade Counts & Analytics"
    echo -e "✅ Advanced Position Management"
    echo -e "✅ Enhanced Stop Loss Placement"
    
    echo -e "\n${BLUE}Test New Endpoints:${NC}"
    echo -e "curl http://209.38.34.59/api/v1/trade-analytics/health"
    echo -e "curl http://209.38.34.59/api/v1/advanced-positions/health"
    echo -e "curl http://209.38.34.59/api/v1/grid-trading/health"
    
    echo -e "\n${YELLOW}Monitor logs with:${NC}"
    echo -e "sudo docker-compose logs -f backend"
    echo -e "sudo docker-compose logs -f celery_worker"
    echo -e "sudo docker-compose logs -f celery_beat"
}

# Function to rollback if needed
rollback() {
    print_error "Deployment failed! Rolling back..."
    
    cd "$PROJECT_DIR"
    sudo docker-compose down
    
    # Extract backup
    sudo tar -xzf "$BACKUP_DIR/$BACKUP_NAME.tar.gz" -C "$(dirname $PROJECT_DIR)"
    
    # Restart services
    sudo docker-compose up -d
    
    print_success "Rollback completed"
    exit 1
}

# Main deployment function
main() {
    print_status "=============================================================================
STARTING AUTOMATED TRADING BOT DEPLOYMENT
============================================================================="
    
    # Set trap for error handling
    trap rollback ERR
    
    # Pre-flight checks
    check_permissions
    
    # Check if project directory exists
    if [ ! -d "$PROJECT_DIR" ]; then
        print_error "Project directory not found: $PROJECT_DIR"
        print_error "Please update the PROJECT_DIR variable in this script"
        exit 1
    fi
    
    # Create backup
    create_backup
    
    # Update code
    update_code
    
    # Check if we need to rebuild
    REBUILD_NEEDED=false
    if update_dependencies; then
        REBUILD_NEEDED=true
    fi
    
    # Run migrations
    run_migrations
    
    # Restart services (rebuild if needed)
    if [ "$REBUILD_NEEDED" = true ]; then
        print_status "Rebuilding Docker images due to dependency changes..."
        restart_services
    else
        print_status "Restarting services without rebuild..."
        cd "$PROJECT_DIR"
        sudo docker-compose restart
        sleep 15
        check_service_health
    fi
    
    # Post-deployment tasks
    post_deployment_tasks
    
    # Show summary
    show_summary
    
    print_success "Deployment completed successfully! 🚀"
}

# Run main function
main "$@" 