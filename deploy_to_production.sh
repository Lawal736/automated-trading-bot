#!/bin/bash

# Production Deployment Script for DigitalOcean
# Run this script on your DigitalOcean server

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Starting Production Deployment - BOT Scheduling System${NC}"
echo -e "${BLUE}📅 This deployment includes:${NC}"
echo -e "${BLUE}   - Event-driven BOT scheduling system${NC}"
echo -e "${BLUE}   - strategy_params field for future flexibility${NC}"
echo -e "${BLUE}   - Cassava BOT daily signals at 00:05 UTC${NC}"
echo -e "${BLUE}   - Cassava BOT stop loss updates at 00:20 UTC${NC}"
echo -e "${BLUE}   - Replacement of continuous loops with scheduled tasks${NC}"
echo ""

# Check if we're in the right directory
if [ ! -f "docker-compose.prod.yml" ]; then
    echo -e "${RED}❌ docker-compose.prod.yml not found. Please run this script from the project root directory.${NC}"
    exit 1
fi

# Step 1: Pull latest changes
echo -e "${YELLOW}📥 Step 1: Pulling latest changes from repository...${NC}"
git pull origin main

# Step 2: Stop current services
echo -e "${YELLOW}🛑 Step 2: Stopping current services...${NC}"
docker-compose -f docker-compose.prod.yml down

# Step 3: Rebuild images
echo -e "${YELLOW}🔨 Step 3: Rebuilding images with new code...${NC}"
docker-compose -f docker-compose.prod.yml build --no-cache

# Step 4: Run database migration
echo -e "${YELLOW}🗄️ Step 4: Running database migration...${NC}"
docker-compose -f docker-compose.prod.yml run --rm backend alembic upgrade head

# Step 5: Start all services
echo -e "${YELLOW}🚀 Step 5: Starting all services...${NC}"
docker-compose -f docker-compose.prod.yml up -d

# Step 6: Wait for services to be ready
echo -e "${YELLOW}⏳ Step 6: Waiting for services to be ready...${NC}"
sleep 30

# Step 7: Check service status
echo -e "${YELLOW}📊 Step 7: Checking service status...${NC}"
docker-compose -f docker-compose.prod.yml ps

# Step 8: Verify new tasks are loaded
echo -e "${YELLOW}✅ Step 8: Verifying new Cassava BOT tasks are loaded...${NC}"
echo -e "${BLUE}Celery Worker Tasks:${NC}"
docker logs trading_bot_celery_worker_prod --tail 20 | grep -E "(process_cassava_bot_signals_and_trades|update_cassava_bot_stop_losses|Connected to redis)" || true

echo -e "${BLUE}Celery Beat Status:${NC}"
docker logs trading_bot_celery_beat_prod --tail 10

# Step 9: Verify database migration
echo -e "${YELLOW}🔍 Step 9: Verifying database migration...${NC}"
docker exec trading_bot_backend_prod python3 -c "
from app.core.database import SessionLocal
from sqlalchemy import text
db = SessionLocal()
result = db.execute(text('SELECT column_name FROM information_schema.columns WHERE table_name = \'bots\' AND column_name = \'strategy_params\''))
if list(result):
    print('✅ strategy_params field successfully added to bots table')
else:
    print('❌ strategy_params field not found')
db.close()
"

# Step 10: Clean up old images
echo -e "${YELLOW}🧹 Step 10: Cleaning up old Docker images...${NC}"
docker system prune -f

echo ""
echo -e "${GREEN}🎉 DEPLOYMENT COMPLETED SUCCESSFULLY!${NC}"
echo ""
echo -e "${GREEN}📅 New Scheduled Tasks Active:${NC}"
echo -e "${GREEN}   • 00:05 UTC: Cassava data update + BOT signals/trading${NC}"
echo -e "${GREEN}   • 00:10 UTC: Cassava data cleanup (50-day FIFO)${NC}"
echo -e "${GREEN}   • 00:15 UTC: Manual stop loss updates${NC}"
echo -e "${GREEN}   • 00:20 UTC: Cassava BOT stop loss updates${NC}"
echo -e "${GREEN}   • Every 4 hours: Position synchronization${NC}"
echo -e "${GREEN}   • Every hour: Failed stop loss sweep${NC}"
echo ""
echo -e "${GREEN}🚀 Your BOT scheduling system is now live and event-driven!${NC}" 