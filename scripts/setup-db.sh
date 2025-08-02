#!/bin/bash
set -e

echo "🔧 Setting up PostgreSQL database..."

# Setup PostgreSQL
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Create database and user if they don't exist
sudo -u postgres psql -c "SELECT 1 FROM pg_database WHERE datname = 'secure_search_prod';" | grep -q 1 || sudo -u postgres createdb secure_search_prod
sudo -u postgres psql -c "SELECT 1 FROM pg_roles WHERE rolname = 'secure_user';" | grep -q 1 || sudo -u postgres psql -c "CREATE USER secure_user WITH PASSWORD '$1';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE secure_search_prod TO secure_user;"
sudo -u postgres psql -c "ALTER USER secure_user CREATEDB;"

echo "✅ PostgreSQL setup completed"