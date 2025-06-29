# 🚀 Digital Ocean Deployment Guide

This guide will walk you through deploying your Automated Trading Bot Platform to Digital Ocean with automatic GitHub-to-production deployment.

## 📋 Prerequisites

1. **Digital Ocean Account** with API access
2. **Domain Name** (optional but recommended)
3. **GitHub Repository** with your code
4. **Docker & Docker Compose** installed locally

## 🏗 Step 1: Digital Ocean Setup

### 1.1 Create a Container Registry

1. Go to your Digital Ocean dashboard
2. Navigate to **Container Registry**
3. Create a new registry (e.g., `automated-trading-bot`)
4. Note the registry name for later use

### 1.2 Create a Droplet

1. Go to **Droplets** in your Digital Ocean dashboard
2. Click **Create** → **Droplets**
3. Choose configuration:
   - **Distribution**: Ubuntu 22.04 LTS
   - **Plan**: Basic
   - **Size**: 2GB RAM / 1 vCPU (minimum)
   - **Datacenter**: Choose closest to your users
   - **Authentication**: SSH Key (recommended) or Password
4. Note the droplet's IP address

### 1.3 Generate API Token

1. Go to **API** → **Tokens/Keys**
2. Generate a new token with **Write** access
3. Save the token securely

## 🔧 Step 2: Local Environment Setup

### 2.1 Configure Environment Variables

```bash
# Copy production environment template
cp env.prod.example .env

# Edit .env with your production values
nano .env
```

**Key variables to update:**
- `DIGITALOCEAN_REGISTRY`: Your registry name
- `NEXT_PUBLIC_API_URL`: Your domain or droplet IP
- `ALLOWED_HOSTS`: Your domain(s)
- `SECRET_KEY`: Generate a strong secret key
- Exchange API keys (set `BINANCE_TESTNET=false` for production)

### 2.2 Set GitHub Secrets

Go to your GitHub repository → **Settings** → **Secrets and variables** → **Actions**

Add these secrets:
- `DIGITALOCEAN_ACCESS_TOKEN`: Your Digital Ocean API token
- `DIGITALOCEAN_REGISTRY`: Your registry name
- `DIGITALOCEAN_HOST`: Your droplet's IP address
- `DIGITALOCEAN_USERNAME`: Usually `root`
- `DIGITALOCEAN_SSH_KEY`: Your private SSH key (base64 encoded)

## 🚀 Step 3: Server Setup

### 3.1 Connect to Your Droplet

```bash
ssh root@your-droplet-ip
```

### 3.2 Install Docker and Docker Compose

```bash
# Update system
apt update && apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Install Docker Compose
curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Add user to docker group
usermod -aG docker $USER
```

### 3.3 Clone Your Repository

```bash
# Create application directory
mkdir -p /opt/automated-trading-bot
cd /opt/automated-trading-bot

# Clone your repository
git clone https://github.com/yourusername/your-repo-name.git .

# Copy production environment
cp env.prod.example .env
nano .env  # Configure with your production values
```

### 3.4 Configure SSL (Optional but Recommended)

If you have a domain name:

```bash
# Install Certbot
apt install certbot python3-certbot-nginx -y

# Get SSL certificate
certbot certonly --standalone -d yourdomain.com -d www.yourdomain.com

# Copy certificates to nginx directory
mkdir -p /opt/automated-trading-bot/nginx/ssl
cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem /opt/automated-trading-bot/nginx/ssl/cert.pem
cp /etc/letsencrypt/live/yourdomain.com/privkey.pem /opt/automated-trading-bot/nginx/ssl/key.pem
```

## 🚀 Step 4: Initial Deployment

### 4.1 Manual First Deployment

```bash
# Login to Digital Ocean registry
docker login registry.digitalocean.com

# Build and push images
docker build -t registry.digitalocean.com/your-registry/automatedtradingbot-backend:latest ./backend
docker build -t registry.digitalocean.com/your-registry/automatedtradingbot-frontend:latest ./frontend
docker push registry.digitalocean.com/your-registry/automatedtradingbot-backend:latest
docker push registry.digitalocean.com/your-registry/automatedtradingbot-frontend:latest

# Start services
docker-compose -f docker-compose.prod.yml up -d
```

### 4.2 Verify Deployment

```bash
# Check service status
docker-compose -f docker-compose.prod.yml ps

# Check logs
docker-compose -f docker-compose.prod.yml logs -f

# Test health endpoints
curl http://localhost:8000/health
curl http://localhost:3000
```

## 🔄 Step 5: Automatic Deployment Setup

### 5.1 Push to GitHub

Your GitHub Actions workflow will automatically:
1. Build Docker images
2. Push to Digital Ocean Container Registry
3. Deploy to your droplet

```bash
# Commit and push your changes
git add .
git commit -m "Initial production deployment setup"
git push origin main
```

### 5.2 Monitor Deployment

1. Go to your GitHub repository → **Actions**
2. Monitor the deployment workflow
3. Check your application at `http://your-droplet-ip` or `https://yourdomain.com`

## 🔧 Step 6: Production Configuration

### 6.1 Set Up Monitoring

```bash
# Install monitoring tools
apt install htop iotop nethogs -y

# Set up log rotation
cat > /etc/logrotate.d/trading-bot << EOF
/opt/automated-trading-bot/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 root root
}
EOF
```

### 6.2 Configure Firewall

```bash
# Allow only necessary ports
ufw allow 22/tcp    # SSH
ufw allow 80/tcp    # HTTP
ufw allow 443/tcp   # HTTPS
ufw enable
```

### 6.3 Set Up Backups

```bash
# Create backup script
cat > /opt/backup.sh << 'EOF'
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/opt/backups"

mkdir -p $BACKUP_DIR

# Backup database
docker-compose -f /opt/automated-trading-bot/docker-compose.prod.yml exec -T postgres pg_dump -U trading_user trading_bot > $BACKUP_DIR/db_backup_$DATE.sql

# Backup uploads and data
tar -czf $BACKUP_DIR/data_backup_$DATE.tar.gz -C /opt/automated-trading-bot uploads data

# Keep only last 7 days of backups
find $BACKUP_DIR -name "*.sql" -mtime +7 -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete
EOF

chmod +x /opt/backup.sh

# Add to crontab (daily at 2 AM)
(crontab -l 2>/dev/null; echo "0 2 * * * /opt/backup.sh") | crontab -
```

## 🔍 Step 7: Troubleshooting

### Common Issues

1. **Services not starting**
   ```bash
   docker-compose -f docker-compose.prod.yml logs [service-name]
   ```

2. **Database connection issues**
   ```bash
   docker-compose -f docker-compose.prod.yml exec postgres psql -U trading_user -d trading_bot
   ```

3. **SSL certificate issues**
   ```bash
   certbot renew --dry-run
   ```

4. **Memory issues**
   ```bash
   # Check memory usage
   free -h
   # Restart services if needed
   docker-compose -f docker-compose.prod.yml restart
   ```

### Useful Commands

```bash
# View all logs
docker-compose -f docker-compose.prod.yml logs -f

# Restart specific service
docker-compose -f docker-compose.prod.yml restart backend

# Update and redeploy
cd /opt/automated-trading-bot
git pull origin main
docker-compose -f docker-compose.prod.yml pull
docker-compose -f docker-compose.prod.yml up -d

# Check disk space
df -h

# Check running containers
docker ps
```

## 📊 Step 8: Monitoring and Maintenance

### 8.1 Health Checks

Your application includes health check endpoints:
- Backend: `http://your-domain/api/health`
- Frontend: `http://your-domain`

### 8.2 Log Monitoring

```bash
# Monitor application logs
tail -f /opt/automated-trading-bot/logs/app.log

# Monitor nginx logs
tail -f /opt/automated-trading-bot/logs/nginx/access.log
tail -f /opt/automated-trading-bot/logs/nginx/error.log
```

### 8.3 Performance Monitoring

```bash
# Monitor system resources
htop

# Monitor Docker resources
docker stats

# Monitor disk I/O
iotop
```

## 🔒 Security Considerations

1. **Keep system updated**
   ```bash
   apt update && apt upgrade -y
   ```

2. **Regular security audits**
   ```bash
   # Check for security updates
   apt list --upgradable
   ```

3. **Monitor logs for suspicious activity**
   ```bash
   # Check failed login attempts
   grep "Failed password" /var/log/auth.log
   ```

4. **Backup regularly**
   - Database backups
   - Configuration backups
   - SSL certificates

## 🎉 Success!

Your Automated Trading Bot Platform is now deployed on Digital Ocean with:
- ✅ Automatic GitHub-to-production deployment
- ✅ SSL/TLS encryption (if domain configured)
- ✅ Health monitoring
- ✅ Automated backups
- ✅ Production-optimized configuration

## 📞 Support

If you encounter issues:
1. Check the logs: `docker-compose -f docker-compose.prod.yml logs -f`
2. Verify environment variables are correct
3. Ensure all required ports are open
4. Check Digital Ocean status page for any outages

For additional help, refer to the main README.md and documentation in the `docs/` folder. 