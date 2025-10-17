# SafeBoda Rwanda Platform - Deployment Guide

## 🚀 Deployment Overview

This guide covers the complete deployment process for the SafeBoda Rwanda platform, from development setup to production deployment with Rwanda-specific configurations.

## 📋 Prerequisites

### System Requirements
- **Operating System**: Ubuntu 20.04 LTS or higher (recommended for production)
- **Python**: 3.11 or higher
- **Node.js**: 16.x or higher (for frontend assets)
- **Memory**: Minimum 4GB RAM (8GB+ recommended for production)
- **Storage**: SSD with minimum 50GB free space
- **Network**: Stable internet connection for external API integrations

### Required Services
- **PostgreSQL**: 15 or higher
- **Redis**: 7.0 or higher
- **Nginx**: 1.18 or higher (for production)
- **SSL Certificate**: Valid SSL certificate for HTTPS

## 🛠️ Development Environment Setup

### 1. Clone Repository
```bash
git clone https://github.com/safeboda-rwanda/platform.git
cd platform
```

### 2. Python Environment
```bash
# Create virtual environment
python -m venv safeboda_env
source safeboda_env/bin/activate  # Linux/Mac
# or
safeboda_env\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
```

### 3. Environment Configuration
```bash
# Copy environment template
cp .env.example .env

# Edit environment variables
vim .env
```

**Development Environment Variables** (`.env`):
```bash
# Django Settings
DJANGO_SETTINGS_MODULE=safeboda_rwanda.settings.development
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database
DATABASE_URL=postgresql://safeboda:password@localhost:5432/safeboda_dev

# Redis
REDIS_URL=redis://localhost:6379/0

# Celery
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2

# Rwanda Mobile Money (Development)
MTN_MOMO_API_URL=https://sandbox.momodeveloper.mtn.com
MTN_MOMO_SUBSCRIPTION_KEY=your-dev-subscription-key
AIRTEL_MONEY_API_URL=https://openapi-sandbox.airtel.africa
AIRTEL_MONEY_CLIENT_ID=your-dev-client-id

# Government APIs (Development)
BNR_API_URL=https://api-dev.bnr.rw
RRA_API_URL=https://api-dev.rra.gov.rw
RTDA_API_URL=https://api-dev.rtda.gov.rw

# Logging
LOG_LEVEL=DEBUG
LOG_FILE=logs/safeboda.log
```

### 4. Database Setup
```bash
# Start PostgreSQL
sudo systemctl start postgresql

# Create database and user
sudo -u postgres psql
CREATE DATABASE safeboda_dev;
CREATE USER safeboda WITH PASSWORD 'password';
GRANT ALL PRIVILEGES ON DATABASE safeboda_dev TO safeboda;
\q

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser
```

### 5. Redis Setup
```bash
# Install and start Redis
sudo apt update
sudo apt install redis-server
sudo systemctl start redis-server
sudo systemctl enable redis-server

# Test Redis connection
redis-cli ping
```

### 6. Start Development Server
```bash
# Terminal 1: Django development server
python manage.py runserver

# Terminal 2: Celery worker
celery -A safeboda_rwanda worker -l info

# Terminal 3: Celery beat (for scheduled tasks)
celery -A safeboda_rwanda beat -l info
```

## 🏭 Production Deployment

### 1. Server Preparation

#### Ubuntu Server Setup
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install system dependencies
sudo apt install -y python3.11 python3.11-venv python3-pip postgresql postgresql-contrib redis-server nginx supervisor git curl

# Install Docker (optional, for containerized deployment)
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
```

#### Create Application User
```bash
# Create dedicated user for SafeBoda
sudo adduser --system --group --home /opt/safeboda safeboda
sudo mkdir -p /opt/safeboda/{app,logs,static,media}
sudo chown -R safeboda:safeboda /opt/safeboda
```

### 2. Application Deployment

#### Clone and Setup Application
```bash
# Switch to safeboda user
sudo -u safeboda -i

# Clone repository
cd /opt/safeboda
git clone https://github.com/safeboda-rwanda/platform.git app
cd app

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install gunicorn psycopg2-binary
```

#### Production Environment Configuration
```bash
# Create production environment file
sudo -u safeboda vim /opt/safeboda/app/.env.production
```

**Production Environment Variables**:
```bash
# Django Settings
DJANGO_SETTINGS_MODULE=safeboda_rwanda.settings.production
SECRET_KEY=your-production-secret-key-here
DEBUG=False
ALLOWED_HOSTS=api.safeboda.rw,safeboda.rw

# Security Settings
SECURE_SSL_REDIRECT=True
SECURE_PROXY_SSL_HEADER=HTTP_X_FORWARDED_PROTO,https
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True

# Database
DATABASE_URL=postgresql://safeboda_prod:secure_password@localhost:5432/safeboda_prod

# Redis
REDIS_URL=redis://localhost:6379/0

# Celery
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2

# Rwanda Mobile Money (Production)
MTN_MOMO_API_URL=https://api.momo.mtn.rw
MTN_MOMO_SUBSCRIPTION_KEY=your-production-subscription-key
MTN_MOMO_API_USER_ID=your-api-user-id
MTN_MOMO_API_KEY=your-api-key

AIRTEL_MONEY_API_URL=https://openapi.airtel.africa
AIRTEL_MONEY_CLIENT_ID=your-production-client-id
AIRTEL_MONEY_CLIENT_SECRET=your-client-secret

# Government APIs (Production)
BNR_API_URL=https://api.bnr.rw
BNR_API_TOKEN=your-bnr-api-token
RRA_API_URL=https://api.rra.gov.rw
RRA_API_TOKEN=your-rra-api-token
RTDA_API_URL=https://api.rtda.gov.rw
RTDA_API_TOKEN=your-rtda-api-token

# Monitoring and Logging
LOG_LEVEL=INFO
LOG_FILE=/opt/safeboda/logs/safeboda.log
SENTRY_DSN=your-sentry-dsn-here

# Static Files
STATIC_ROOT=/opt/safeboda/static
MEDIA_ROOT=/opt/safeboda/media

# Email Configuration
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=noreply@safeboda.rw
EMAIL_HOST_PASSWORD=your-email-password
```

### 3. Database Configuration

#### PostgreSQL Production Setup
```bash
# Secure PostgreSQL installation
sudo -u postgres psql

# Create production database and user
CREATE DATABASE safeboda_prod;
CREATE USER safeboda_prod WITH PASSWORD 'secure_password_here';
GRANT ALL PRIVILEGES ON DATABASE safeboda_prod TO safeboda_prod;

# Configure PostgreSQL for production
ALTER USER safeboda_prod CREATEDB;  -- For running tests
\q

# Configure PostgreSQL settings
sudo vim /etc/postgresql/15/main/postgresql.conf
```

**PostgreSQL Configuration** (`postgresql.conf`):
```bash
# Memory Settings
shared_buffers = 256MB
effective_cache_size = 1GB
work_mem = 4MB
maintenance_work_mem = 64MB

# WAL Settings
wal_buffers = 16MB
checkpoint_completion_target = 0.9

# Connection Settings
max_connections = 100
```

#### Run Production Migrations
```bash
# Switch to safeboda user
sudo -u safeboda -i
cd /opt/safeboda/app
source venv/bin/activate

# Set production environment
export $(cat .env.production | xargs)

# Run migrations
python manage.py migrate

# Collect static files
python manage.py collectstatic --noinput

# Create superuser (interactive)
python manage.py createsuperuser
```

### 4. Web Server Configuration

#### Gunicorn Configuration
```bash
# Create Gunicorn configuration
sudo -u safeboda vim /opt/safeboda/app/gunicorn.conf.py
```

**Gunicorn Configuration** (`gunicorn.conf.py`):
```python
import multiprocessing

# Server socket
bind = "unix:/opt/safeboda/app/gunicorn.sock"
backlog = 2048

# Worker processes
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "gevent"
worker_connections = 1000
timeout = 30
keepalive = 2

# Restart workers after this many requests, to help control memory leaks
max_requests = 1000
max_requests_jitter = 50

# Logging
accesslog = "/opt/safeboda/logs/gunicorn-access.log"
errorlog = "/opt/safeboda/logs/gunicorn-error.log"
loglevel = "info"

# Process naming
proc_name = 'safeboda-gunicorn'

# Server mechanics
daemon = False
pidfile = '/opt/safeboda/app/gunicorn.pid'
user = 'safeboda'
group = 'safeboda'
tmp_upload_dir = None

# SSL
keyfile = None
certfile = None
```

#### Nginx Configuration
```bash
# Create Nginx site configuration
sudo vim /etc/nginx/sites-available/safeboda
```

**Nginx Configuration**:
```nginx
upstream safeboda_app {
    server unix:/opt/safeboda/app/gunicorn.sock fail_timeout=0;
}

upstream safeboda_websocket {
    server 127.0.0.1:8001;
}

# HTTP redirect to HTTPS
server {
    listen 80;
    server_name api.safeboda.rw safeboda.rw;
    return 301 https://$server_name$request_uri;
}

# HTTPS server
server {
    listen 443 ssl http2;
    server_name api.safeboda.rw safeboda.rw;

    # SSL Configuration
    ssl_certificate /etc/ssl/certs/safeboda.rw.crt;
    ssl_certificate_key /etc/ssl/private/safeboda.rw.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options DENY always;
    add_header X-Content-Type-Options nosniff always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    client_max_body_size 10M;

    # Static files
    location /static/ {
        alias /opt/safeboda/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # Media files
    location /media/ {
        alias /opt/safeboda/media/;
        expires 1y;
        add_header Cache-Control "public";
    }

    # WebSocket for real-time features
    location /ws/ {
        proxy_pass http://safeboda_websocket;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }

    # Main application
    location / {
        proxy_pass http://safeboda_app;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;

        # API-specific settings
        location /api/ {
            proxy_pass http://safeboda_app;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            
            # CORS headers for API
            add_header Access-Control-Allow-Origin $http_origin always;
            add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS" always;
            add_header Access-Control-Allow-Headers "Origin, Content-Type, Accept, Authorization" always;
            add_header Access-Control-Allow-Credentials true always;

            if ($request_method = 'OPTIONS') {
                return 204;
            }
        }
    }

    # Health check endpoint
    location /health/ {
        access_log off;
        return 200 "healthy\n";
        add_header Content-Type text/plain;
    }
}
```

```bash
# Enable site and test configuration
sudo ln -s /etc/nginx/sites-available/safeboda /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 5. Process Management with Supervisor

#### Supervisor Configuration
```bash
# Create supervisor configurations
sudo vim /etc/supervisor/conf.d/safeboda.conf
```

**Supervisor Configuration**:
```ini
[group:safeboda]
programs=safeboda-web,safeboda-celery,safeboda-websocket

[program:safeboda-web]
command=/opt/safeboda/app/venv/bin/gunicorn safeboda_rwanda.wsgi:application -c /opt/safeboda/app/gunicorn.conf.py
directory=/opt/safeboda/app
user=safeboda
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/opt/safeboda/logs/gunicorn-supervisor.log
environment=PATH="/opt/safeboda/app/venv/bin",DJANGO_SETTINGS_MODULE="safeboda_rwanda.settings.production"

[program:safeboda-celery]
command=/opt/safeboda/app/venv/bin/celery -A safeboda_rwanda worker -l info
directory=/opt/safeboda/app
user=safeboda
numprocs=2
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/opt/safeboda/logs/celery-worker.log
environment=PATH="/opt/safeboda/app/venv/bin",DJANGO_SETTINGS_MODULE="safeboda_rwanda.settings.production"

[program:safeboda-websocket]
command=/opt/safeboda/app/venv/bin/daphne -b 127.0.0.1 -p 8001 safeboda_rwanda.asgi:application
directory=/opt/safeboda/app
user=safeboda
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/opt/safeboda/logs/websocket.log
environment=PATH="/opt/safeboda/app/venv/bin",DJANGO_SETTINGS_MODULE="safeboda_rwanda.settings.production"
```

```bash
# Update supervisor and start services
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start safeboda:*
sudo supervisorctl status
```

## 🐳 Docker Deployment (Alternative)

### 1. Docker Compose for Production

**docker-compose.prod.yml**:
```yaml
version: '3.8'

services:
  web:
    build:
      context: .
      dockerfile: Dockerfile.prod
    environment:
      - DJANGO_SETTINGS_MODULE=safeboda_rwanda.settings.production
    volumes:
      - static_volume:/app/staticfiles
      - media_volume:/app/mediafiles
    depends_on:
      - postgres
      - redis
    restart: unless-stopped

  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: safeboda_prod
      POSTGRES_USER: safeboda_prod
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    restart: unless-stopped

  celery:
    build:
      context: .
      dockerfile: Dockerfile.prod
    command: celery -A safeboda_rwanda worker -l info
    environment:
      - DJANGO_SETTINGS_MODULE=safeboda_rwanda.settings.production
    depends_on:
      - postgres
      - redis
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.prod.conf:/etc/nginx/nginx.conf
      - static_volume:/var/www/static
      - media_volume:/var/www/media
      - /etc/ssl/certs:/etc/ssl/certs:ro
      - /etc/ssl/private:/etc/ssl/private:ro
    depends_on:
      - web
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
  static_volume:
  media_volume:
```

### 2. Production Dockerfile

**Dockerfile.prod**:
```dockerfile
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        postgresql-client \
        build-essential \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install gunicorn psycopg2-binary

# Copy project
COPY . .

# Create non-root user
RUN adduser --disabled-password --gecos '' appuser
RUN chown -R appuser:appuser /app
USER appuser

# Collect static files
RUN python manage.py collectstatic --noinput

# Run gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "safeboda_rwanda.wsgi:application"]
```

## 🔧 Environment-Specific Settings

### Development Settings (`settings/development.py`)
```python
from .base import *

DEBUG = True
ALLOWED_HOSTS = ['localhost', '127.0.0.1']

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'safeboda_dev',
        'USER': 'safeboda',
        'PASSWORD': 'password',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}

# Cache
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/0',
    }
}

# Celery
CELERY_TASK_ALWAYS_EAGER = True  # Execute tasks synchronously for development

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'DEBUG',
    },
}
```

### Production Settings (`settings/production.py`)
```python
from .base import *
import os

DEBUG = False
ALLOWED_HOSTS = ['api.safeboda.rw', 'safeboda.rw']

# Security settings
SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True

# Database
DATABASES = {
    'default': dj_database_url.parse(os.environ.get('DATABASE_URL'))
}

# Cache
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': os.environ.get('REDIS_URL'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}

# Static files
STATIC_ROOT = '/opt/safeboda/static'
MEDIA_ROOT = '/opt/safeboda/media'

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/opt/safeboda/logs/safeboda.log',
            'maxBytes': 1024*1024*15,  # 15MB
            'backupCount': 10,
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['file'],
        'level': 'INFO',
    },
}
```

## 🔍 Monitoring and Maintenance

### 1. Health Checks

**Health Check Script** (`scripts/health_check.py`):
```python
#!/usr/bin/env python
import requests
import sys
import time

def check_api_health():
    try:
        response = requests.get('https://api.safeboda.rw/health/', timeout=10)
        return response.status_code == 200
    except:
        return False

def check_database():
    # Add database connectivity check
    pass

def check_redis():
    # Add Redis connectivity check
    pass

def main():
    checks = [
        ('API', check_api_health),
        ('Database', check_database),
        ('Redis', check_redis),
    ]
    
    all_healthy = True
    for name, check_func in checks:
        if check_func():
            print(f"✅ {name} is healthy")
        else:
            print(f"❌ {name} is unhealthy")
            all_healthy = False
    
    sys.exit(0 if all_healthy else 1)

if __name__ == '__main__':
    main()
```

### 2. Backup Scripts

**Database Backup** (`scripts/backup_db.sh`):
```bash
#!/bin/bash
BACKUP_DIR="/opt/safeboda/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/safeboda_backup_$TIMESTAMP.sql"

mkdir -p $BACKUP_DIR

# Create database backup
pg_dump -h localhost -U safeboda_prod safeboda_prod > $BACKUP_FILE

# Compress backup
gzip $BACKUP_FILE

# Remove backups older than 7 days
find $BACKUP_DIR -name "safeboda_backup_*.sql.gz" -mtime +7 -delete

echo "Backup completed: ${BACKUP_FILE}.gz"
```

### 3. Log Rotation
```bash
# Add to /etc/logrotate.d/safeboda
/opt/safeboda/logs/*.log {
    daily
    missingok
    rotate 52
    compress
    notifempty
    create 0644 safeboda safeboda
    postrotate
        supervisorctl restart safeboda:*
    endscript
}
```

## 🚨 Troubleshooting

### Common Issues and Solutions

#### 1. Application Won't Start
```bash
# Check supervisor status
sudo supervisorctl status

# Check logs
tail -f /opt/safeboda/logs/gunicorn-error.log

# Check environment variables
sudo -u safeboda -i
cd /opt/safeboda/app
source venv/bin/activate
python manage.py check
```

#### 2. Database Connection Issues
```bash
# Test database connection
sudo -u postgres psql -d safeboda_prod -c "SELECT 1;"

# Check PostgreSQL status
sudo systemctl status postgresql
```

#### 3. Redis Connection Issues
```bash
# Test Redis connection
redis-cli ping

# Check Redis status
sudo systemctl status redis-server
```

#### 4. SSL Certificate Issues
```bash
# Check certificate validity
openssl x509 -in /etc/ssl/certs/safeboda.rw.crt -text -noout

# Test SSL configuration
sudo nginx -t
```

### Performance Optimization

#### 1. Database Optimization
```sql
-- Create indexes for better performance
CREATE INDEX CONCURRENTLY idx_rides_created_at ON rides(created_at);
CREATE INDEX CONCURRENTLY idx_rides_customer_status ON rides(customer_id, status);
CREATE INDEX CONCURRENTLY idx_transactions_ride_status ON transactions(ride_id, status);

-- Analyze query performance
EXPLAIN ANALYZE SELECT * FROM rides WHERE customer_id = 'uuid' ORDER BY created_at DESC LIMIT 10;
```

#### 2. Application Optimization
```python
# Enable query optimization in production
DATABASES = {
    'default': {
        # ... other settings
        'OPTIONS': {
            'MAX_CONNS': 20,
            'OPTIONS': {
                'MAX_CONNS': 20,
            }
        }
    }
}

# Optimize Redis connections
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
        'OPTIONS': {
            'CONNECTION_POOL_KWARGS': {
                'max_connections': 50,
                'retry_on_timeout': True,
            }
        }
    }
}
```

---

**Document Version**: 1.0  
**Last Updated**: October 17, 2025  
**Author**: SafeBoda Rwanda DevOps Team