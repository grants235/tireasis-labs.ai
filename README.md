# Multi-Service FastAPI Application

A robust, containerized application with three isolated components:
- **PostgreSQL Database**: Secure data storage (no external access)
- **DB Server**: FastAPI service for database operations (isolated, no internet access)
- **Proxy Server**: FastAPI service for external third-party API access (internet only)

## Architecture

```
┌─────────────────┐                    ┌─────────────────┐    ┌─────────────────┐
│   Proxy Server  │                    │    DB Server    │◄──►│   PostgreSQL    │
│   (Port 8002)   │                    │   (Port 8001)   │    │   Database      │
│                 │                    │                 │    │                 │
│ • External APIs │    NO CONNECTION   │ • DB Operations │    │ • Data Storage  │
│ • Internet Only │ ◄─────────────────►│ • No Internet   │    │ • DB-Only Access│
└─────────────────┘                    └─────────────────┘    └─────────────────┘
        │                                       │
        ▼                                       ▲
   Internet Access                     Database Network
                                          (Isolated)
```

## Key Architectural Principles

- **Complete Isolation**: DB Server and Proxy Server do not communicate
- **Network Segmentation**: Database network is internal-only (no internet)
- **Single Purpose Services**: Each service has one clear responsibility
- **Security by Design**: Minimal attack surface through isolation

## Security Features

- **Network Isolation**: Database only accessible by DB Server
- **No Cross-Service Communication**: Proxy and DB servers are completely separate
- **API Key Authentication**: Both services require valid API keys
- **Non-root containers**: Services run as unprivileged users
- **Internal Database Network**: No external internet access for database operations
- **Health checks**: Automated service monitoring

## Quick Start

### Prerequisites
- Docker and Docker Compose installed
- Available ports 8001 and 8002

### Setup

1. **Clone and configure**:
   ```bash
   cd /path/to/app
   cp .env.example .env
   # Edit .env with your secure values
   ```

2. **Build and start services**:
   ```bash
   docker-compose up --build
   ```

3. **Verify services**:
   ```bash
   # Check DB Server health
   curl http://localhost:8001/health
   
   # Check Proxy Server health and connectivity
   curl http://localhost:8002/health
   ```

## Configuration

### Environment Variables (.env)

```env
# Database Configuration
POSTGRES_DB=app_database
POSTGRES_USER=app_user
POSTGRES_PASSWORD=your_secure_password
POSTGRES_HOST=postgres
POSTGRES_PORT=5432

# API Keys (CHANGE THESE!)
DB_SERVER_API_KEY=your_db_server_api_key_here
PROXY_API_KEY=your_proxy_api_key_here

# Server Ports
DB_SERVER_PORT=8001
PROXY_SERVER_PORT=8002

# Environment
ENVIRONMENT=development
```

**Important**: Change default API keys before deployment!

## API Usage

### Authentication
All API endpoints require Bearer token authentication:
```bash
curl -H "Authorization: Bearer YOUR_API_KEY" http://localhost:PORT/endpoint
```

### DB Server (Port 8001)
**Purpose**: Direct database operations only
- `GET /health` - Service health check
- `POST /users` - Create user
- `GET /users/{id}` - Get user by ID
- `GET /users` - List users
- `POST /data-entries` - Create data entry
- `GET /data-entries/{id}` - Get data entry
- `GET /data-entries` - List data entries

### Proxy Server (Port 8002)
**Purpose**: External third-party API access only
- `GET /health` - Service health check with connectivity test
- `POST /proxy` - Proxy any HTTP request to external APIs
- `GET /proxy/{url}` - Simple GET proxy for external URLs
- `GET /test-connectivity` - Test connectivity to various external services
- `GET /info` - Service information

### Example Requests

**Create a user (DB Server)**:
```bash
curl -X POST http://localhost:8001/users \
  -H "Authorization: Bearer your_db_server_api_key_here" \
  -H "Content-Type: application/json" \
  -d '{"username": "john_doe", "email": "john@example.com"}'
```

**Proxy external API request (Proxy Server)**:
```bash
curl -X POST http://localhost:8002/proxy \
  -H "Authorization: Bearer your_proxy_api_key_here" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://api.github.com/users/octocat",
    "method": "GET",
    "timeout": 30
  }'
```

**Simple GET proxy (Proxy Server)**:
```bash
curl http://localhost:8002/proxy/https://jsonplaceholder.typicode.com/posts/1 \
  -H "Authorization: Bearer your_proxy_api_key_here"
```

## Development

### Local Development
```bash
# Start only database for local development
docker-compose up postgres

# Run services locally with database access
cd db-server
pip install -r requirements.txt
python app.py

cd ../proxy-server  
pip install -r requirements.txt
python app.py
```

### Service Management
```bash
# View logs
docker-compose logs -f [service-name]

# Restart specific service
docker-compose restart db-server
docker-compose restart proxy-server

# Stop all services
docker-compose down

# Remove volumes (WARNING: deletes data)
docker-compose down -v
```

### Database Management
```bash
# Connect to PostgreSQL
docker-compose exec postgres psql -U app_user -d app_database

# View database logs
docker-compose logs postgres

# Backup database
docker-compose exec postgres pg_dump -U app_user app_database > backup.sql

# Restore database
docker-compose exec -T postgres psql -U app_user -d app_database < backup.sql
```

## Service Details

### DB Server
- **Network**: Internal database network only
- **Purpose**: Database operations and data management
- **Internet Access**: None (by design)
- **Dependencies**: PostgreSQL database
- **API Key**: `DB_SERVER_API_KEY`

### Proxy Server  
- **Network**: External network only
- **Purpose**: External third-party API access
- **Internet Access**: Full (required for functionality)
- **Dependencies**: None
- **API Key**: `PROXY_API_KEY`

### PostgreSQL Database
- **Network**: Internal database network only
- **Access**: DB Server only
- **Internet Access**: None (completely isolated)
- **Data Persistence**: Docker volume

## Monitoring & Troubleshooting

### Health Checks
Each service has specific health checks:

**DB Server** (`/health`):
- Service status
- Database connectivity
- No external connectivity (by design)

**Proxy Server** (`/health`):
- Service status  
- External connectivity test
- Internet access verification

### Common Issues

**DB Server can't connect to database**:
- Check PostgreSQL container health: `docker-compose ps`
- Verify database credentials in `.env`
- Check database network connectivity

**Proxy Server can't reach external APIs**:
- Test connectivity: `curl http://localhost:8002/test-connectivity`
- Check external network configuration
- Verify proxy server has internet access

**Services won't start**:
- Check port availability: `netstat -tulpn | grep :800[12]`
- Verify environment variables in `.env`
- Check Docker logs: `docker-compose logs`

**API authentication failed**:
- Verify API keys match between `.env` and requests
- Check Authorization header format: `Bearer YOUR_KEY`
- Ensure you're using the correct API key for each service

## Production Deployment

### Security Checklist
- [ ] Change all default passwords and API keys
- [ ] Use secure, randomly generated API keys (32+ characters)
- [ ] Enable HTTPS with proper certificates
- [ ] Configure firewall rules (only ports 8001, 8002 exposed)
- [ ] Set up log rotation and monitoring
- [ ] Review network isolation configuration
- [ ] Harden PostgreSQL configuration
- [ ] Regular security updates

### Performance Optimization
- Configure PostgreSQL for your workload
- Add resource limits to Docker services
- Implement connection pooling for database
- Set up monitoring and alerting
- Consider load balancing for high availability

### Environment Variables for Production
```env
ENVIRONMENT=production
POSTGRES_PASSWORD=very_secure_random_password_here
DB_SERVER_API_KEY=secure_random_32_char_api_key_here
PROXY_API_KEY=another_secure_32_char_key_here
```

## Project Structure

```
├── README.md
├── docker-compose.yml           # Service orchestration
├── .env.example                 # Environment template
├── .env                        # Local configuration
├── .gitignore                  # Git ignore rules
├── init-db.sql                 # Database initialization
├── db-server/                  # Database service
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app.py                  # FastAPI database app
└── proxy-server/              # Proxy service
    ├── Dockerfile
    ├── requirements.txt
    └── app.py                  # FastAPI proxy app
```

## Network Architecture

```yaml
# docker-compose.yml networks:
db_network:
  driver: bridge
  internal: true    # No external internet access
  services: [postgres, db-server]

external:
  driver: bridge 
  services: [proxy-server]
```

## Use Cases

### DB Server
- User management and authentication
- Data storage and retrieval
- Internal business logic
- Reporting and analytics
- Data validation and processing

### Proxy Server
- Third-party API integration
- External service communication
- Webhook handling
- API rate limiting and caching
- External data fetching

## Contributing

1. Follow the existing code structure and patterns
2. Maintain service isolation principles
3. Update this README for any architectural changes
4. Ensure all services pass health checks
5. Test with both development and production configurations
6. Respect network isolation boundaries

## License

This project is available under the MIT License.