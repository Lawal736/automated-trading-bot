# Container Naming Standardization

## Overview
This document outlines the standardized container naming conventions implemented to ensure consistency between development and production environments, eliminating deployment conflicts.

## Standardized Container Names

### Infrastructure Services
- **postgres** - PostgreSQL database server
- **redis** - Redis cache and message broker  
- **rabbitmq** - RabbitMQ message queue

### Application Services
- **trading_bot_backend** - FastAPI backend service
- **trading_bot_frontend** - Next.js frontend application
- **trading_bot_nginx** - Nginx reverse proxy

### Background Workers
- **trading_bot_celery_worker** - Celery task worker
- **trading_bot_celery_beat** - Celery beat scheduler

## Changes Made

### 1. Docker Compose Files
- **docker-compose.yml** (development): Updated container names to use standardized naming
- **docker-compose.prod.yml** (production): Cleaned up and standardized container names
- Removed confusing network aliases and inconsistent naming

### 2. Backend Configuration
- **backend/app/core/config.py**: 
  - Added proper environment variable usage with `os.getenv()`
  - Implemented `@property` methods for dynamic database URL construction
  - Removed hardcoded database connection strings
  - Cleaned up duplicate Celery settings

### 3. Nginx Configuration
- **nginx/nginx.conf**: Updated upstream server names to match standardized container names
- Fixed incorrect container references (`trading_bot_backend_prod_prod` → `trading_bot_backend`)

## Environment Variable Structure

The backend now properly reads configuration from environment variables:

```bash
# Database
POSTGRES_SERVER=postgres
POSTGRES_USER=trading_user
POSTGRES_PASSWORD=your_password
POSTGRES_DB=trading_bot

# Redis
REDIS_URL=redis://redis:6379/0

# RabbitMQ
RABBITMQ_URL=amqp://guest:guest@rabbitmq:5672/
```

## Benefits

1. **Consistency**: Both development and production use identical container names
2. **Predictability**: No more guessing which container name to use in different environments
3. **Simplified Deployment**: Code works identically in both environments
4. **Easier Debugging**: Container names are consistent across all environments
5. **Reduced Errors**: Eliminates naming-related deployment failures

## Testing

Verified functionality:
- ✅ All containers start successfully with new naming
- ✅ Backend connects to database using standardized names
- ✅ API endpoints respond correctly (`/health` returns `{"status":"healthy"}`)
- ✅ Frontend loads and displays correctly
- ✅ Container networking functions properly

## Future Deployments

With this standardization:
1. Development and production will use identical container references
2. No more manual configuration changes during deployment
3. Environment-specific settings controlled solely through environment variables
4. Reduced risk of deployment conflicts

## Rollback Plan

If issues arise, the previous configuration can be restored by:
1. Reverting to the commit before this standardization
2. However, this is not recommended as it reintroduces the naming conflicts

The standardization is designed to be backward-compatible and safer than the previous mixed naming approach. 