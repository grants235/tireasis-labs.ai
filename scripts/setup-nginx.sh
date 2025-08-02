#!/bin/bash
set -e

echo "🌐 Setting up nginx reverse proxy..."

# Create nginx configuration
cat > /etc/nginx/sites-available/secure-search << 'EOF'
server {
    listen 80;
    server_name _;
    
    location /api/ {
        proxy_pass http://localhost:8001/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    location /proxy/ {
        proxy_pass http://localhost:8002/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    location /health {
        return 200 'OK';
        add_header Content-Type text/plain;
    }
}
EOF

# Enable the configuration
ln -sf /etc/nginx/sites-available/secure-search /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

# Test and reload nginx
nginx -t && systemctl reload nginx

echo "✅ Nginx setup completed"