# Nexus ERP - Production Deployment Guide

This guide provides complete instructions for deploying Nexus ERP in a production environment.

## Prerequisites

- Docker and Docker Compose installed
- Domain name configured (optional but recommended)
- SSL certificate (for HTTPS)
- OpenAI API key (for AI features)
- Stripe account (for billing)

## Quick Start

### 1. Clone and Configure

```bash
# Navigate to the project directory
cd nexus-erp

# Copy environment file
cp .env.example .env

# Edit the environment file
nano .env
```

### 2. Configure Environment Variables

Edit `.env` with your production settings:

```env
# Application
APP_NAME=Nexus ERP
APP_VERSION=1.0.0
ENVIRONMENT=production
DEBUG=false
SECRET_KEY=your-very-secure-secret-key-change-this
LOG_LEVEL=INFO

# Database
DATABASE_URL=postgresql+asyncpg://nexus:your-secure-password@postgres:5432/nexus_erp
DATABASE_POOL_SIZE=20

# Redis
REDIS_URL=redis://redis:6379/0

# Security
JWT_SECRET_KEY=your-jwt-secret-key-change-this
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Stripe (for billing)
STRIPE_API_KEY=sk_live_your_stripe_key
STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret

# OpenAI (for AI features)
OPENAI_API_KEY=sk-your-openai-api-key
OPENAI_MODEL=gpt-4o

# Email (optional)
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=noreply@example.com
SMTP_PASSWORD=your-smtp-password
```

### 3. Deploy with Docker Compose

```bash
# Build and start all services
docker compose up -d --build

# Check service status
docker compose ps

# View logs
docker compose logs -f backend
```

### 4. Initialize Database

```bash
# Run database migrations
docker compose exec backend alembic upgrade head

# Create initial admin user (optional)
docker compose exec backend python -m app.scripts.create_admin
```

### 5. Verify Deployment

- **Frontend**: http://localhost (or your domain)
- **Backend API**: http://localhost/api/docs
- **Health Check**: http://localhost/health

## Service Architecture

```
┌─────────────────────────────────────────────────────────┐
│                      Nginx (Port 80/443)                │
│                    Reverse Proxy + SSL                  │
└─────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
        ▼                   ▼                   ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│   Frontend    │   │    Backend    │   │   Postgres    │
│   (React)     │   │   (FastAPI)   │   │   Database    │
│   Port 3000   │   │   Port 8000   │   │   Port 5432   │
└───────────────┘   └───────────────┘   └───────────────┘
                            │
                    ┌───────┼───────┐
                    │               │
                    ▼               ▼
            ┌───────────────┐   ┌───────────────┐
            │    Redis      │   │    Celery     │
            │    Cache      │   │   Workers     │
            │   Port 6379   │   │   (Tasks)     │
            └───────────────┘   └───────────────┘
```

## Production Checklist

### Security

- [ ] Change all default passwords and secret keys
- [ ] Enable HTTPS with valid SSL certificate
- [ ] Configure firewall rules (only expose ports 80, 443)
- [ ] Set up rate limiting
- [ ] Enable CORS for your domain only
- [ ] Review and update JWT token expiration times
- [ ] Set `DEBUG=false` in production

### Database

- [ ] Set strong PostgreSQL password
- [ ] Configure database backups
- [ ] Set up connection pooling
- [ ] Consider read replicas for high traffic

### Monitoring

- [ ] Set up log aggregation (ELK stack, etc.)
- [ ] Configure health checks and alerts
- [ ] Monitor resource usage (CPU, Memory, Disk)
- [ ] Set up uptime monitoring

### Backups

```bash
# Create database backup
docker compose exec postgres pg_dump -U nexus nexus_erp > backup_$(date +%Y%m%d).sql

# Restore from backup
cat backup_20240101.sql | docker compose exec -T postgres psql -U nexus nexus_erp
```

## Scaling

### Horizontal Scaling

```bash
# Scale backend workers
docker compose up -d --scale backend=3

# Scale Celery workers
docker compose up -d --scale celery=2
```

### Load Balancing

Use Nginx or a cloud load balancer to distribute traffic across multiple backend instances.

## Troubleshooting

### Common Issues

1. **Database Connection Errors**
   ```bash
   # Check database is running
   docker compose ps postgres
   
   # Check connection string in .env
   # Ensure database exists and user has permissions
   ```

2. **Migration Errors**
   ```bash
   # Check current migration status
   docker compose exec backend alembic current
   
   # Rollback last migration
   docker compose exec backend alembic downgrade -1
   ```

3. **AI Features Not Working**
   ```bash
   # Verify OpenAI API key is set
   docker compose exec backend env | grep OPENAI
   
   # Test API key
   curl https://api.openai.com/v1/models \
     -H "Authorization: Bearer $OPENAI_API_KEY"
   ```

### Viewing Logs

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f backend
docker compose logs -f frontend
docker compose logs -f postgres
```

## Maintenance

### Updates

```bash
# Pull latest code
git pull

# Rebuild and restart
docker compose up -d --build
```

### Database Migrations

```bash
# Create new migration after model changes
docker compose exec backend alembic revision --autogenerate -m "Description"

# Apply migrations
docker compose exec backend alembic upgrade head
```

### Backup Schedule

Add to crontab:
```bash
0 2 * * * cd /path/to/nexus-erp && docker compose exec postgres pg_dump -U nexus nexus_erp > /backups/nexus_erp_$(date +\%Y\%m\%d).sql
```

## Support

For issues and support:
- GitHub Issues: [Project Repository]
- Documentation: `/docs`
- Email: support@nexus-erp.com
