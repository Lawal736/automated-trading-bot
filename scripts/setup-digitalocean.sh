#!/bin/bash

# Digital Ocean Server Setup Script
# This script automates the initial setup of a Digital Ocean droplet for the Automated Trading Bot

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Digital Ocean Server Setup Script${NC}"
echo -e "${BLUE}=====================================${NC}"

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}❌ This script must be run as root${NC}"
    exit 1
fi

# Configuration
APP_DIR="/opt/automated-trading-bot"
BACKUP_DIR="/opt/backups"
LOG_DIR="/var/log/trading-bot"

echo -e "${YELLOW}📋 Starting server setup...${NC}"

# Update system
echo -e "${YELLOW}🔄 Updating system packages...${NC}"
apt update && apt upgrade -y

# Install essential packages
echo -e "${YELLOW}📦 Installing essential packages...${NC}"
apt install -y \
    curl \
    wget \
    git \
    vim \
    htop \
    iotop \
    nethogs \
    unzip \
    software-properties-common \
    apt-transport-https \
    ca-certificates \
    gnupg \
    lsb-release \
    ufw \
    fail2ban \
    logrotate \
    cron

# Install Docker
echo -e "${YELLOW}🐳 Installing Docker...${NC}"
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
rm get-docker.sh

# Install Docker Compose
echo -e "${YELLOW}🐳 Installing Docker Compose...${NC}"
curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Create application user
echo -e "${YELLOW}👤 Creating application user...${NC}"
if ! id "tradingbot" &>/dev/null; then
    useradd -m -s /bin/bash tradingbot
    usermod -aG docker tradingbot
    echo -e "${GREEN}✅ User 'tradingbot' created${NC}"
else
    echo -e "${YELLOW}⚠️  User 'tradingbot' already exists${NC}"
fi

# Create necessary directories
echo -e "${YELLOW}📁 Creating application directories...${NC}"
mkdir -p $APP_DIR
mkdir -p $BACKUP_DIR
mkdir -p $LOG_DIR
mkdir -p $APP_DIR/logs
mkdir -p $APP_DIR/uploads
mkdir -p $APP_DIR/data
mkdir -p $APP_DIR/nginx/ssl

# Set proper permissions
chown -R tradingbot:tradingbot $APP_DIR
chown -R tradingbot:tradingbot $BACKUP_DIR
chmod 755 $APP_DIR
chmod 755 $BACKUP_DIR

# Configure firewall
echo -e "${YELLOW}🔥 Configuring firewall...${NC}"
ufw --force enable
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp    # SSH
ufw allow 80/tcp    # HTTP
ufw allow 443/tcp   # HTTPS
ufw allow 5432/tcp  # PostgreSQL (if needed externally)
ufw allow 6379/tcp  # Redis (if needed externally)
ufw allow 5672/tcp  # RabbitMQ (if needed externally)
ufw allow 15672/tcp # RabbitMQ Management (if needed externally)

# Configure fail2ban
echo -e "${YELLOW}🛡️  Configuring fail2ban...${NC}"
systemctl enable fail2ban
systemctl start fail2ban

# Create fail2ban jail for SSH
cat > /etc/fail2ban/jail.local << EOF
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 3

[sshd]
enabled = true
port = ssh
filter = sshd
logpath = /var/log/auth.log
maxretry = 3
bantime = 3600
EOF

# Restart fail2ban
systemctl restart fail2ban

# Configure log rotation
echo -e "${YELLOW}📝 Configuring log rotation...${NC}"
cat > /etc/logrotate.d/trading-bot << EOF
$APP_DIR/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 tradingbot tradingbot
    postrotate
        systemctl reload nginx > /dev/null 2>&1 || true
    endscript
}

$LOG_DIR/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 tradingbot tradingbot
}
EOF

# Create backup script
echo -e "${YELLOW}💾 Creating backup script...${NC}"
cat > $BACKUP_DIR/backup.sh << 'EOF'
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/opt/backups"
APP_DIR="/opt/automated-trading-bot"

# Create backup directory
mkdir -p $BACKUP_DIR

# Backup database
if docker ps | grep -q postgres; then
    docker-compose -f $APP_DIR/docker-compose.prod.yml exec -T postgres pg_dump -U trading_user trading_bot > $BACKUP_DIR/db_backup_$DATE.sql
    echo "Database backup created: db_backup_$DATE.sql"
else
    echo "PostgreSQL container not running, skipping database backup"
fi

# Backup uploads and data
if [ -d "$APP_DIR/uploads" ]; then
    tar -czf $BACKUP_DIR/uploads_backup_$DATE.tar.gz -C $APP_DIR uploads
    echo "Uploads backup created: uploads_backup_$DATE.tar.gz"
fi

if [ -d "$APP_DIR/data" ]; then
    tar -czf $BACKUP_DIR/data_backup_$DATE.tar.gz -C $APP_DIR data
    echo "Data backup created: data_backup_$DATE.tar.gz"
fi

# Keep only last 7 days of backups
find $BACKUP_DIR -name "*.sql" -mtime +7 -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete

echo "Backup completed at $(date)"
EOF

chmod +x $BACKUP_DIR/backup.sh
chown tradingbot:tradingbot $BACKUP_DIR/backup.sh

# Add backup to crontab (daily at 2 AM)
(crontab -u tradingbot -l 2>/dev/null; echo "0 2 * * * $BACKUP_DIR/backup.sh >> $LOG_DIR/backup.log 2>&1") | crontab -u tradingbot -

# Create systemd service for the application
echo -e "${YELLOW}⚙️  Creating systemd service...${NC}"
cat > /etc/systemd/system/trading-bot.service << EOF
[Unit]
Description=Automated Trading Bot Platform
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=$APP_DIR
ExecStart=/usr/local/bin/docker-compose -f docker-compose.prod.yml up -d
ExecStop=/usr/local/bin/docker-compose -f docker-compose.prod.yml down
User=tradingbot
Group=tradingbot

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable trading-bot.service

# Create monitoring script
echo -e "${YELLOW}📊 Creating monitoring script...${NC}"
cat > $APP_DIR/monitor.sh << 'EOF'
#!/bin/bash
APP_DIR="/opt/automated-trading-bot"
LOG_FILE="/var/log/trading-bot/monitor.log"

# Check if containers are running
check_containers() {
    if ! docker-compose -f $APP_DIR/docker-compose.prod.yml ps | grep -q "Up"; then
        echo "$(date): Some containers are not running, attempting restart..." >> $LOG_FILE
        docker-compose -f $APP_DIR/docker-compose.prod.yml restart
    fi
}

# Check disk space
check_disk() {
    DISK_USAGE=$(df / | awk 'NR==2 {print $5}' | sed 's/%//')
    if [ $DISK_USAGE -gt 90 ]; then
        echo "$(date): Disk usage is high: ${DISK_USAGE}%" >> $LOG_FILE
    fi
}

# Check memory usage
check_memory() {
    MEMORY_USAGE=$(free | awk 'NR==2{printf "%.2f", $3*100/$2}')
    if (( $(echo "$MEMORY_USAGE > 90" | bc -l) )); then
        echo "$(date): Memory usage is high: ${MEMORY_USAGE}%" >> $LOG_FILE
    fi
}

# Run checks
check_containers
check_disk
check_memory
EOF

chmod +x $APP_DIR/monitor.sh
chown tradingbot:tradingbot $APP_DIR/monitor.sh

# Add monitoring to crontab (every 5 minutes)
(crontab -u tradingbot -l 2>/dev/null; echo "*/5 * * * * $APP_DIR/monitor.sh") | crontab -u tradingbot -

# Create SSL certificate renewal script
echo -e "${YELLOW}🔒 Creating SSL renewal script...${NC}"
cat > $APP_DIR/renew-ssl.sh << 'EOF'
#!/bin/bash
# Renew SSL certificates and restart nginx
certbot renew --quiet
if [ $? -eq 0 ]; then
    cp /etc/letsencrypt/live/$(hostname)/fullchain.pem /opt/automated-trading-bot/nginx/ssl/cert.pem
    cp /etc/letsencrypt/live/$(hostname)/privkey.pem /opt/automated-trading-bot/nginx/ssl/key.pem
    docker-compose -f /opt/automated-trading-bot/docker-compose.prod.yml restart nginx
    echo "$(date): SSL certificates renewed successfully" >> /var/log/trading-bot/ssl.log
else
    echo "$(date): SSL certificate renewal failed" >> /var/log/trading-bot/ssl.log
fi
EOF

chmod +x $APP_DIR/renew-ssl.sh
chown tradingbot:tradingbot $APP_DIR/renew-ssl.sh

# Add SSL renewal to crontab (twice daily)
(crontab -u tradingbot -l 2>/dev/null; echo "0 12,0 * * * $APP_DIR/renew-ssl.sh") | crontab -u tradingbot -

# Set up environment
echo -e "${YELLOW}🔧 Setting up environment...${NC}"
if [ -f "$APP_DIR/env.prod.example" ]; then
    cp $APP_DIR/env.prod.example $APP_DIR/.env
    chown tradingbot:tradingbot $APP_DIR/.env
    echo -e "${GREEN}✅ Environment file created from template${NC}"
    echo -e "${YELLOW}⚠️  Please edit $APP_DIR/.env with your production values${NC}"
else
    echo -e "${YELLOW}⚠️  Environment template not found, you'll need to create .env manually${NC}"
fi

# Final setup
echo -e "${YELLOW}🎯 Final setup...${NC}"

# Create a simple status script
cat > $APP_DIR/status.sh << 'EOF'
#!/bin/bash
echo "=== Automated Trading Bot Status ==="
echo "Docker status:"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
echo ""
echo "System resources:"
free -h
echo ""
echo "Disk usage:"
df -h /
echo ""
echo "Recent logs:"
tail -n 10 /var/log/trading-bot/monitor.log 2>/dev/null || echo "No monitor logs found"
EOF

chmod +x $APP_DIR/status.sh
chown tradingbot:tradingbot $APP_DIR/status.sh

echo -e "${GREEN}✅ Server setup completed successfully!${NC}"
echo ""
echo -e "${BLUE}📋 Next steps:${NC}"
echo -e "${YELLOW}1. Clone your repository to $APP_DIR${NC}"
echo -e "${YELLOW}2. Configure your .env file with production values${NC}"
echo -e "${YELLOW}3. Set up SSL certificates (if using a domain)${NC}"
echo -e "${YELLOW}4. Deploy your application${NC}"
echo ""
echo -e "${BLUE}🔧 Useful commands:${NC}"
echo -e "${YELLOW}  Check status: $APP_DIR/status.sh${NC}"
echo -e "${YELLOW}  View logs: docker-compose -f $APP_DIR/docker-compose.prod.yml logs -f${NC}"
echo -e "${YELLOW}  Restart services: systemctl restart trading-bot${NC}"
echo -e "${YELLOW}  Manual backup: $BACKUP_DIR/backup.sh${NC}"
echo ""
echo -e "${GREEN}🎉 Your Digital Ocean server is ready for deployment!${NC}" 