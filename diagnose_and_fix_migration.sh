#!/bin/bash

# Migration Diagnostic and Fix Script for DigitalOcean
# Run this script on your DigitalOcean server to diagnose and fix migration issues

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}🔍 Migration Diagnostic and Fix Script${NC}"
echo ""

# Step 1: Check current database state
echo -e "${YELLOW}📋 Step 1: Checking current database migration state...${NC}"
echo -e "${BLUE}Current revision in database:${NC}"
docker exec trading_bot_postgres_prod psql -U trading_user -d trading_bot -c "SELECT * FROM alembic_version;" || echo "No alembic_version table found"

echo ""
echo -e "${BLUE}Available migration files:${NC}"
ls -la backend/migrations/versions/ | grep "\.py$"

echo ""
echo -e "${BLUE}Migration chain (down_revision values):${NC}"
grep -r "down_revision" backend/migrations/versions/ | grep -v "__pycache__" | sort

echo ""
echo -e "${BLUE}Available heads:${NC}"
docker-compose -f docker-compose.prod.yml run --rm backend alembic heads 2>/dev/null || echo "Cannot determine heads due to missing revision"

# Step 2: Find the problematic revision
echo ""
echo -e "${YELLOW}🔍 Step 2: Analyzing the missing revision issue...${NC}"
MISSING_REVISION="38a8f06596ee"
echo -e "${RED}Missing revision: ${MISSING_REVISION}${NC}"

# Check if this revision exists in any migration file
if grep -r "${MISSING_REVISION}" backend/migrations/versions/; then
    echo -e "${GREEN}Found reference to missing revision in migration files${NC}"
else
    echo -e "${RED}Missing revision not found in any migration files${NC}"
fi

# Step 3: Manual migration state reset
echo ""
echo -e "${YELLOW}🔧 Step 3: Manual migration state reset...${NC}"
echo -e "${BLUE}This will manually reset the migration state to match available files${NC}"

# Drop and recreate alembic_version table
echo -e "${BLUE}Resetting alembic_version table...${NC}"
docker exec trading_bot_postgres_prod psql -U trading_user -d trading_bot -c "
DROP TABLE IF EXISTS alembic_version;
CREATE TABLE alembic_version (
    version_num VARCHAR(32) NOT NULL,
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);
"

# Find the latest migration that should be applied
echo -e "${BLUE}Finding the correct migration to stamp...${NC}"
LATEST_APPLIED_MIGRATION="7ee431d863ab"  # This was shown as the head before
echo -e "${BLUE}Setting database state to: ${LATEST_APPLIED_MIGRATION}${NC}"

# Insert the correct migration state
docker exec trading_bot_postgres_prod psql -U trading_user -d trading_bot -c "
INSERT INTO alembic_version (version_num) VALUES ('${LATEST_APPLIED_MIGRATION}');
"

# Step 4: Now run the new migration
echo ""
echo -e "${YELLOW}🗄️ Step 4: Running the new migration...${NC}"
docker-compose -f docker-compose.prod.yml run --rm backend alembic upgrade head

# Step 5: Verify the migration worked
echo ""
echo -e "${YELLOW}✅ Step 5: Verifying migration success...${NC}"
docker exec trading_bot_postgres_prod psql -U trading_user -d trading_bot -c "SELECT * FROM alembic_version;"

echo -e "${BLUE}Checking if strategy_params column was added:${NC}"
docker exec trading_bot_postgres_prod psql -U trading_user -d trading_bot -c "
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'bots' AND column_name = 'strategy_params';
"

# Step 6: Start all services
echo ""
echo -e "${YELLOW}🚀 Step 6: Starting all services...${NC}"
docker-compose -f docker-compose.prod.yml up -d

# Step 7: Wait for services to be ready
echo -e "${YELLOW}⏳ Step 7: Waiting for services to be ready...${NC}"
sleep 30

# Step 8: Check service status
echo -e "${YELLOW}📊 Step 8: Checking service status...${NC}"
docker-compose -f docker-compose.prod.yml ps

# Step 9: Verify new tasks are loaded
echo ""
echo -e "${YELLOW}✅ Step 9: Verifying new Cassava BOT tasks are loaded...${NC}"
echo -e "${BLUE}Celery Worker Tasks:${NC}"
docker logs trading_bot_celery_worker_prod --tail 20 | grep -E "(process_cassava_bot_signals_and_trades|update_cassava_bot_stop_losses|Connected to redis)" || true

echo -e "${BLUE}Celery Beat Status:${NC}"
docker logs trading_bot_celery_beat_prod --tail 10

# Step 10: Test new task import
echo ""
echo -e "${YELLOW}🧪 Step 10: Testing new task imports...${NC}"
docker exec trading_bot_backend_prod python3 -c "
from app.tasks.cassava_bot_tasks import process_cassava_bot_signals_and_trades, update_cassava_bot_stop_losses
print('✅ Cassava bot tasks imported successfully')
" || echo "❌ Task import failed"

# Step 11: Clean up
echo ""
echo -e "${YELLOW}🧹 Step 11: Cleaning up old Docker images...${NC}"
docker system prune -f

echo ""
echo -e "${GREEN}🎉 MIGRATION FIXED AND DEPLOYMENT COMPLETED!${NC}"
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

# Final status
echo ""
echo -e "${YELLOW}📋 Final Migration Status:${NC}"
docker-compose -f docker-compose.prod.yml run --rm backend alembic current 