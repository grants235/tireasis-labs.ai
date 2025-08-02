#!/bin/bash
set -e

echo "🔧 Setting up PostgreSQL database..."

# Setup PostgreSQL
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Create database if it doesn't exist
sudo -u postgres psql -c "SELECT 1 FROM pg_database WHERE datname = 'secure_search_prod';" | grep -q 1 || sudo -u postgres createdb secure_search_prod

# Create or update user password
if sudo -u postgres psql -c "SELECT 1 FROM pg_roles WHERE rolname = 'secure_user';" | grep -q 1; then
  echo "User exists, updating password..."
  sudo -u postgres psql -c "ALTER USER secure_user WITH PASSWORD '$1';"
else
  echo "Creating new user..."
  sudo -u postgres psql -c "CREATE USER secure_user WITH PASSWORD '$1';"
fi
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE secure_search_prod TO secure_user;"
sudo -u postgres psql -c "ALTER USER secure_user CREATEDB;"

echo "✅ PostgreSQL setup completed"