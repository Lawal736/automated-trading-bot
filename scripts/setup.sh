#!/bin/bash

# Automated Trading Bot Platform Setup Script
# This script will help you set up the entire project

set -e

echo "🚀 Setting up Automated Trading Bot Platform..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

# Check if Docker is installed
check_docker() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    print_success "Docker and Docker Compose are installed"
}

# Check if Node.js is installed
check_node() {
    if ! command -v node &> /dev/null; then
        print_warning "Node.js is not installed. Installing frontend dependencies will be skipped."
        return 1
    fi
    
    if ! command -v npm &> /dev/null; then
        print_warning "npm is not installed. Installing frontend dependencies will be skipped."
        return 1
    fi
    
    print_success "Node.js and npm are installed"
    return 0
}

# Check if Python is installed
check_python() {
    if ! command -v python3 &> /dev/null; then
        print_warning "Python 3 is not installed. Installing backend dependencies will be skipped."
        return 1
    fi
    
    print_success "Python 3 is installed"
    return 0
}

# Create environment file
setup_environment() {
    print_status "Setting up environment configuration..."
    
    if [ ! -f .env ]; then
        cp env.example .env
        print_success "Created .env file from template"
        print_warning "Please edit .env file with your configuration before starting the application"
    else
        print_warning ".env file already exists. Skipping..."
    fi
}

# Install backend dependencies
install_backend_deps() {
    if check_python; then
        print_status "Installing backend dependencies..."
        
        if [ ! -d "backend/venv" ]; then
            cd backend
            python3 -m venv venv
            source venv/bin/activate
            pip install --upgrade pip
            pip install -r requirements.txt
            cd ..
            print_success "Backend dependencies installed"
        else
            print_warning "Backend virtual environment already exists. Skipping..."
        fi
    fi
}

# Install frontend dependencies
install_frontend_deps() {
    if check_node; then
        print_status "Installing frontend dependencies..."
        
        cd frontend
        npm install
        cd ..
        print_success "Frontend dependencies installed"
    fi
}

# Create necessary directories
create_directories() {
    print_status "Creating necessary directories..."
    
    mkdir -p data/backtest
    mkdir -p uploads
    mkdir -p logs
    mkdir -p nginx/ssl
    
    print_success "Directories created"
}

# Start services with Docker
start_services() {
    print_status "Starting services with Docker Compose..."
    
    # Start only the infrastructure services first
    docker-compose up -d postgres redis rabbitmq
    
    print_status "Waiting for services to be ready..."
    sleep 10
    
    # Start all services
    docker-compose up -d
    
    print_success "All services started"
}

# Show status
show_status() {
    print_status "Checking service status..."
    
    docker-compose ps
    
    echo ""
    print_success "Setup completed! 🎉"
    echo ""
    echo "Services are running on:"
    echo "  - Frontend: http://localhost:3000"
    echo "  - Backend API: http://localhost:8000"
    echo "  - API Documentation: http://localhost:8000/docs"
    echo "  - RabbitMQ Management: http://localhost:15672"
    echo ""
    echo "Next steps:"
    echo "  1. Edit .env file with your configuration"
    echo "  2. Add your exchange API keys"
    echo "  3. Access the frontend at http://localhost:3000"
    echo ""
    echo "Useful commands:"
    echo "  - View logs: docker-compose logs -f"
    echo "  - Stop services: docker-compose down"
    echo "  - Restart services: docker-compose restart"
}

# Main setup function
main() {
    print_status "Starting setup process..."
    
    check_docker
    setup_environment
    install_backend_deps
    install_frontend_deps
    create_directories
    start_services
    show_status
}

# Run main function
main "$@" 