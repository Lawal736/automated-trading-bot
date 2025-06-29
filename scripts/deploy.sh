#!/bin/bash

# Digital Ocean Deployment Script
# This script handles the deployment of the Automated Trading Bot to Digital Ocean

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
PROJECT_NAME="automated-trading-bot"
DOCKER_REGISTRY="registry.digitalocean.com"
REGISTRY_NAME="${DIGITALOCEAN_REGISTRY:-your-registry-name}"

echo -e "${GREEN}🚀 Starting Digital Ocean Deployment${NC}"

# Check if required environment variables are set
if [ -z "$DIGITALOCEAN_ACCESS_TOKEN" ]; then
    echo -e "${RED}❌ DIGITALOCEAN_ACCESS_TOKEN is not set${NC}"
    exit 1
fi

if [ -z "$DIGITALOCEAN_REGISTRY" ]; then
    echo -e "${RED}❌ DIGITALOCEAN_REGISTRY is not set${NC}"
    exit 1
fi

# Login to Digital Ocean Container Registry
echo -e "${YELLOW}📦 Logging into Digital Ocean Container Registry...${NC}"
echo "$DIGITALOCEAN_ACCESS_TOKEN" | docker login $DOCKER_REGISTRY -u $DIGITALOCEAN_ACCESS_TOKEN --password-stdin

# Build and push backend image
echo -e "${YELLOW}🔨 Building and pushing backend image...${NC}"
docker build -t $DOCKER_REGISTRY/$REGISTRY_NAME/automatedtradingbot-backend:latest ./backend
docker push $DOCKER_REGISTRY/$REGISTRY_NAME/automatedtradingbot-backend:latest

# Build and push frontend image
echo -e "${YELLOW}🔨 Building and pushing frontend image...${NC}"
docker build -t $DOCKER_REGISTRY/$REGISTRY_NAME/automatedtradingbot-frontend:latest ./frontend
docker push $DOCKER_REGISTRY/$REGISTRY_NAME/automatedtradingbot-frontend:latest

# Deploy to Digital Ocean Droplet (if SSH details are provided)
if [ ! -z "$DIGITALOCEAN_HOST" ] && [ ! -z "$DIGITALOCEAN_USERNAME" ]; then
    echo -e "${YELLOW}🚀 Deploying to Digital Ocean Droplet...${NC}"
    
    # Create deployment script for remote execution
    cat > /tmp/deploy_remote.sh << 'EOF'
#!/bin/bash
set -e

cd /opt/automated-trading-bot

# Pull latest changes
git pull origin main

# Pull latest images
docker-compose -f docker-compose.prod.yml pull

# Stop existing services
docker-compose -f docker-compose.prod.yml down

# Start services with new images
docker-compose -f docker-compose.prod.yml up -d

# Clean up old images
docker system prune -f

echo "Deployment completed successfully!"
EOF

    # Copy deployment script to remote server
    scp -i ~/.ssh/id_rsa /tmp/deploy_remote.sh $DIGITALOCEAN_USERNAME@$DIGITALOCEAN_HOST:/tmp/
    
    # Execute deployment script on remote server
    ssh -i ~/.ssh/id_rsa $DIGITALOCEAN_USERNAME@$DIGITALOCEAN_HOST "chmod +x /tmp/deploy_remote.sh && /tmp/deploy_remote.sh"
    
    # Clean up local deployment script
    rm /tmp/deploy_remote.sh
    
    echo -e "${GREEN}✅ Deployment completed successfully!${NC}"
else
    echo -e "${YELLOW}⚠️  SSH details not provided. Images have been pushed to registry.${NC}"
    echo -e "${YELLOW}   To deploy manually, run on your Digital Ocean droplet:${NC}"
    echo -e "${YELLOW}   cd /opt/automated-trading-bot && docker-compose -f docker-compose.prod.yml pull && docker-compose -f docker-compose.prod.yml up -d${NC}"
fi

echo -e "${GREEN}🎉 Deployment process completed!${NC}" 