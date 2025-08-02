#!/bin/bash
set -e

echo "📝 Creating environment files..."

# Ensure directories have correct permissions
sudo chown -R $USER:$USER /opt/secure-search

# Create db-server .env file
cat > /opt/secure-search/db-server/.env << 'EOF'
POSTGRES_DB=secure_search_prod
POSTGRES_USER=secure_user
POSTGRES_PASSWORD=PLACEHOLDER_POSTGRES_PASSWORD
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
DB_SERVER_API_KEY=PLACEHOLDER_DB_SERVER_API_KEY
DB_SERVER_PORT=8001
ENVIRONMENT=production
EOF

# Create proxy-server .env file
cat > /opt/secure-search/proxy-server/.env << 'EOF'
PROXY_API_KEY=PLACEHOLDER_PROXY_API_KEY
PROXY_SERVER_PORT=8002
ENVIRONMENT=production
EOF

# Replace placeholders with actual values
sed -i "s/PLACEHOLDER_POSTGRES_PASSWORD/$1/g" /opt/secure-search/db-server/.env
sed -i "s/PLACEHOLDER_DB_SERVER_API_KEY/$2/g" /opt/secure-search/db-server/.env
sed -i "s/PLACEHOLDER_PROXY_API_KEY/$3/g" /opt/secure-search/proxy-server/.env

echo "✅ Environment files created"