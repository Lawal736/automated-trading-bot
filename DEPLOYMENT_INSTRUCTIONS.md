# 🚀 Deployment Instructions for DigitalOcean Droplet

## 📋 Pre-Deployment Checklist

### 1. **Update Script Configuration**
Before running the deployment script, update the `PROJECT_DIR` variable in `deploy_migration.sh`:

```bash
# This is already set correctly for your droplet
PROJECT_DIR="/opt/automated-trading-bot"  # ✅ Configured for your setup
```

✅ **Already configured correctly for your droplet at:** `/opt/automated-trading-bot`

### 2. **Verify GitHub Repository is Up-to-Date**
Ensure all today's changes are pushed to GitHub:
```bash
git status
git log --oneline -5
```

## 🔧 Deployment Process

### Step 1: Copy Script to Droplet
```bash
# Copy the migration script to your droplet
scp deploy_migration.sh root@209.38.34.59:/tmp/
```

### Step 2: SSH into Your Droplet
```bash
ssh root@209.38.34.59
```

### Step 3: Make Script Executable and Run
```bash
# Make the script executable
chmod +x /tmp/deploy_migration.sh

# Run the deployment
/tmp/deploy_migration.sh
```

## 📊 What the Script Does

### 🔄 **Backup Phase**
- Creates timestamped backup of current deployment
- Stops services safely before backup
- Stores backup in `/var/backups/trading-bot/`

### 📥 **Update Phase**
- Stashes any local changes
- Pulls latest changes from GitHub
- Shows commit differences
- Checks for dependency changes

### 🗄️ **Migration Phase**
- Starts database services
- Runs Django migrations
- Updates database schema

### 🔄 **Restart Phase**
- Rebuilds Docker images (if needed)
- Restarts all services
- Waits for services to be ready

### ✅ **Verification Phase**
- Checks container status
- Tests API endpoints
- Verifies new features are working

### 🧹 **Post-Deployment**
- Collects static files
- Restarts Celery workers
- Shows deployment summary

## 🆘 **Rollback Process**

If deployment fails, the script automatically:
1. Stops all services
2. Restores from backup
3. Restarts services with previous version

Manual rollback:
```bash
cd /var/backups/trading-bot
# List available backups
ls -la

# Restore specific backup
sudo tar -xzf backup_YYYYMMDD_HHMMSS.tar.gz -C /opt/
cd /opt/automated-trading-bot
sudo docker-compose up -d
```

## 🧪 **Post-Deployment Testing**

After deployment, test these new endpoints:

```bash
# Enhanced Trade Analytics
curl http://209.38.34.59/api/v1/trade-analytics/health

# Advanced Position Management
curl http://209.38.34.59/api/v1/advanced-positions/health

# Grid Trading (existing)
curl http://209.38.34.59/api/v1/grid-trading/health

# Main API health
curl http://209.38.34.59/api/v1/health
```

## 📋 **Today's New Features Being Deployed**

### ✅ **Enhanced Trade Counts (#5)**
- **Files Added:**
  - `backend/app/services/trade_analytics_service.py`
  - `backend/app/api/v1/endpoints/trade_analytics.py`
  - `backend/app/tasks/trade_analytics_tasks.py`

- **New Endpoints:**
  - `GET /api/v1/trade-analytics/enhanced-counts`
  - `GET /api/v1/trade-analytics/real-time-metrics`
  - `GET /api/v1/trade-analytics/dashboard`
  - `GET /api/v1/trade-analytics/health`

### ✅ **Advanced Position Management (#6)**
- **Files Added:**
  - `backend/app/services/advanced_position_management_service.py`
  - `backend/app/api/v1/endpoints/advanced_positions.py`

- **New Endpoints:**
  - `GET /api/v1/advanced-positions/overview`
  - `GET /api/v1/advanced-positions/monitoring-dashboard`
  - `GET /api/v1/advanced-positions/health`

### ✅ **Enhanced Stop Loss Placement (#7)**
- **Files Added:**
  - `backend/app/services/enhanced_stop_loss_placement_service.py`

### 🔧 **System Updates**
- **Files Modified:**
  - `backend/app/api/v1/api.py` - Added new routers
  - `backend/app/core/celery.py` - Added new task scheduling
  - `backend/app/tasks/__init__.py` - Included new tasks

## 🔍 **Monitoring After Deployment**

### Check Container Status
```bash
cd /opt/automated-trading-bot
sudo docker-compose ps
```

### Monitor Logs
```bash
# Backend logs
sudo docker-compose logs -f backend

# Celery worker logs
sudo docker-compose logs -f celery_worker

# Celery beat logs
sudo docker-compose logs -f celery_beat

# All logs
sudo docker-compose logs -f
```

### Check Resource Usage
```bash
# CPU and memory usage
htop

# Docker stats
sudo docker stats

# Disk usage
df -h
```

## 🚨 **Troubleshooting**

### Common Issues and Solutions

**1. Permission Denied**
```bash
# Run with sudo
sudo /tmp/deploy_migration.sh
```

**2. Git Authentication Issues**
```bash
# Set up SSH key or use HTTPS with token
cd /opt/automated-trading-bot
sudo git remote set-url origin https://YOUR_TOKEN@github.com/Lawal736/automated-trading-bot.git
```

**3. Docker Issues**
```bash
# Restart Docker daemon
sudo systemctl restart docker

# Clean up Docker
sudo docker system prune -f
```

**4. Database Connection Issues**
```bash
# Check PostgreSQL container
sudo docker-compose exec postgres psql -U trading_user -d trading_bot -c "\l"

# Restart database
sudo docker-compose restart postgres
```

**5. Port Conflicts**
```bash
# Check what's using port 8000
sudo netstat -tulpn | grep :8000

# Kill process if needed
sudo fuser -k 8000/tcp
```

## 📞 **Support**

If you encounter issues:
1. Check the deployment logs
2. Verify all containers are running
3. Test API endpoints individually
4. Check resource usage (memory, disk space)
5. Review error messages in container logs

The script includes automatic rollback functionality, so your system should remain stable even if deployment fails.

## 🎉 **Success Indicators**

Deployment is successful when:
- ✅ All containers show "Up" status
- ✅ API health endpoints return 200 OK
- ✅ Dashboard at http://209.38.34.59/dashboard loads
- ✅ New trade analytics features are accessible
- ✅ Celery tasks are running (check logs)

Your automated trading bot will now have all 7 core features fully implemented and running! 🚀 