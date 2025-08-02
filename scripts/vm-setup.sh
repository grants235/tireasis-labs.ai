#!/bin/bash

# VM Setup Script - Run this on the Azure VM to prepare it for deployment
# This script is called by the GitHub Actions workflow

set -e

echo "🔧 Setting up Azure VM for secure search deployment..."

# Update system packages
echo "📦 Updating system packages..."
sudo apt update
sudo apt upgrade -y

# Install required packages
echo "📦 Installing required packages..."
sudo apt install -y \
    python3 \
    python3-pip \
    python3-venv \
    postgresql \
    postgresql-contrib \
    nginx \
    htop \
    curl \
    wget \
    git \
    ufw

# Configure firewall
echo "🛡️ Configuring firewall..."
sudo ufw --force enable
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 8001/tcp
sudo ufw allow 8002/tcp

# Setup PostgreSQL
echo "🗄️ Setting up PostgreSQL..."
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Configure PostgreSQL to allow local connections
sudo -u postgres sed -i "s/#listen_addresses = 'localhost'/listen_addresses = 'localhost'/" /etc/postgresql/*/main/postgresql.conf
sudo -u postgres echo "host    all             all             127.0.0.1/32            md5" >> /etc/postgresql/*/main/pg_hba.conf
sudo systemctl restart postgresql

# Setup application directory structure
echo "📁 Setting up application directories..."
sudo mkdir -p /opt/secure-search
sudo chown $USER:$USER /opt/secure-search
mkdir -p /opt/secure-search/logs

# Setup log rotation
sudo tee /etc/logrotate.d/secure-search << 'EOF'
/opt/secure-search/logs/*.log {
    daily
    missingok
    rotate 7
    compress
    delaycompress
    notifempty
    create 644 azureuser azureuser
    postrotate
        systemctl reload secure-search-db || true
        systemctl reload secure-search-proxy || true
    endscript
}
EOF

# Setup monitoring script
tee /opt/secure-search/monitor.sh << 'EOF'
#!/bin/bash
# Simple monitoring script
echo "=== Secure Search Services Status ==="
echo "Date: $(date)"
echo ""
echo "DB Server Status:"
systemctl status secure-search-db --no-pager -l
echo ""
echo "Proxy Server Status:"  
systemctl status secure-search-proxy --no-pager -l
echo ""
echo "PostgreSQL Status:"
systemctl status postgresql --no-pager -l
echo ""
echo "Nginx Status:"
systemctl status nginx --no-pager -l
echo ""
echo "=== Resource Usage ==="
free -h
df -h /
echo ""
echo "=== Network Connections ==="
ss -tulpn | grep -E ":(8001|8002|5432|80)"
EOF

chmod +x /opt/secure-search/monitor.sh

# Setup health check endpoint
tee /opt/secure-search/health-check.sh << 'EOF'
#!/bin/bash
# Health check script for monitoring
set -e

DB_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8001/health || echo "000")
PROXY_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8002/health || echo "000")

if [ "$DB_STATUS" = "200" ] && [ "$PROXY_STATUS" = "200" ]; then
    echo "OK - All services healthy"
    exit 0
else
    echo "ERROR - DB: $DB_STATUS, Proxy: $PROXY_STATUS"
    exit 1
fi
EOF

chmod +x /opt/secure-search/health-check.sh

# Add health check to crontab (check every 5 minutes)
(crontab -l 2>/dev/null; echo "*/5 * * * * /opt/secure-search/health-check.sh >> /opt/secure-search/logs/health.log 2>&1") | crontab -

echo "✅ VM setup completed!"
echo ""
echo "🔧 Available commands:"
echo "  Monitor services: /opt/secure-search/monitor.sh"
echo "  Health check: /opt/secure-search/health-check.sh"
echo "  View logs: journalctl -u secure-search-db -f"
echo "  View logs: journalctl -u secure-search-proxy -f"