"""
Setup and Installation Guide for SafeBoda Rwanda Platform

This Django-based platform provides a comprehensive ride-booking system specifically 
designed for Rwanda with mobile money integration, government compliance, and 
real-time tracking capabilities.

## Prerequisites

1. Python 3.9 or higher
2. PostgreSQL with PostGIS extension
3. Redis server
4. Git

## Installation Steps

### 1. Install Python
Download and install Python from https://www.python.org/downloads/
Ensure Python is added to your system PATH.

### 2. Clone and Setup Project
```bash
# Navigate to your project directory
cd "c:\Users\tharc\Desktop\Assignment"

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Database Setup
```bash
# Install PostgreSQL with PostGIS
# For Windows: Download from https://www.postgresql.org/download/windows/
# For macOS: brew install postgresql postgis
# For Ubuntu: sudo apt-get install postgresql postgis

# Create database
createdb safeboda_rwanda

# Add PostGIS extension (run in psql)
CREATE EXTENSION postgis;
```

### 4. Environment Configuration
```bash
# Copy environment file
copy .env.example .env

# Edit .env file with your configuration:
# - Database credentials
# - API keys for Rwanda services
# - Email settings
# - Redis URL
```

### 5. Django Setup
```bash
# Run migrations
python manage.py makemigrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Collect static files (for production)
python manage.py collectstatic
```

### 6. Redis Setup
```bash
# Install Redis
# Windows: Download from https://redis.io/download
# macOS: brew install redis
# Ubuntu: sudo apt-get install redis-server

# Start Redis server
redis-server
```

### 7. Run Development Server
```bash
# Start Django development server
python manage.py runserver

# In another terminal, start Celery (for async tasks)
celery -A safeboda_rwanda worker --loglevel=info

# In another terminal, start Celery Beat (for scheduled tasks)
celery -A safeboda_rwanda beat --loglevel=info
```

### 8. Access the Application
- API Documentation: http://localhost:8000/api/docs/
- Admin Panel: http://localhost:8000/admin/
- Health Check: http://localhost:8000/health/

## Key Features Implemented

### 1. Authentication System
- JWT-based authentication
- Role-based permissions (Customer, Driver, Admin, Government)
- Rwanda National ID validation
- Phone and email verification
- Driver profile management with Rwanda license validation

### 2. Booking System (10 Required Endpoints)
- POST /api/bookings/create/ - Create new ride booking
- GET /api/bookings/{id}/ - Get booking details  
- PUT /api/bookings/{id}/status/ - Update booking status
- POST /api/bookings/{id}/cancel/ - Cancel booking
- GET /api/bookings/active/ - Get active bookings
- Real-time location tracking via WebSocket
- Fare calculation with Rwanda pricing
- Status management workflow

### 3. Payment Integration (Rwanda-Specific)
- MTN Mobile Money integration design
- Airtel Money integration design  
- Cash payment handling
- Transaction management
- Rwanda VAT and commission calculation

### 4. Real-time Location Services
- WebSocket-based real-time tracking
- Driver location updates
- Geographic calculations for Rwanda
- Location history tracking

### 5. Rwanda Government Integration (6 Endpoints)
- RTDA compliance reporting
- Driver license verification
- Tax reporting system
- Emergency services integration
- Data export for government
- Audit trail maintenance

### 6. Analytics System (6 Endpoints)  
- Ride pattern analysis
- Driver performance metrics
- Revenue analytics
- Traffic hotspot analysis
- User behavior insights
- Custom report generation

### 7. Monitoring and Health Checks
- Comprehensive health checks
- Performance metrics
- System status monitoring
- Backup management
- Maintenance mode

## Rwanda-Specific Adaptations

### Mobile Money Integration
- MTN Rwanda Mobile Money API
- Airtel Rwanda Money API
- Rwanda Franc (RWF) currency
- Local payment workflows

### Administrative Divisions
- Province, District, Sector, Cell, Village
- Rwanda National ID validation (16 digits)
- Rwanda phone number validation (+250)
- Rwanda vehicle plate number validation

### Government Compliance
- RTDA (Rwanda Transport Development Agency) integration
- Tax reporting for Rwanda Revenue Authority
- Emergency services connectivity
- Data sovereignty compliance

### Language Support
- English, Kinyarwanda, French
- Localized messages and responses
- Rwanda-specific terminology

## Testing Strategy

### Unit Tests (90%+ Coverage)
```bash
# Run tests with coverage
pytest --cov=. --cov-report=html
```

### Integration Tests  
```bash
# Run integration tests
pytest tests/integration/
```

### Performance Tests
```bash
# Load testing for 10,000+ concurrent users
pytest tests/performance/
```

### Security Tests
```bash
# Security testing
pytest tests/security/
```

## Production Deployment

### 1. Environment Setup
- Set DEBUG=False in production
- Configure SSL/TLS certificates  
- Set up proper database connections
- Configure Redis for production

### 2. Server Configuration
```bash
# Use Gunicorn for production
gunicorn safeboda_rwanda.wsgi:application

# Set up Nginx reverse proxy
# Configure static file serving
# Set up SSL certificates
```

### 3. Monitoring
- Configure Sentry for error tracking
- Set up log aggregation
- Monitor database performance
- Configure backup systems

## API Documentation

Complete OpenAPI 3.0 specification available at:
- Interactive Docs: /api/docs/
- ReDoc: /api/redoc/  
- Schema: /api/schema/

## Rwanda Market Considerations

### Regulatory Compliance
- RTDA licensing requirements
- Rwanda Revenue Authority tax compliance
- Data protection regulations
- Emergency services integration

### Technical Infrastructure  
- 4G network coverage across Rwanda
- Mobile money penetration (80%+)
- Android device prevalence
- Intermittent connectivity handling

### Business Model
- Commission-based revenue (15%)
- Rwanda VAT compliance (18%)
- Driver partner onboarding
- Customer acquisition strategy

## Support and Maintenance

### Code Quality
- Black code formatting
- Flake8 linting
- Type annotations throughout
- Comprehensive documentation

### Version Control
- Git-based workflow
- Feature branch strategy
- Automated testing on CI/CD
- Code review process

### Scalability
- Async task processing with Celery
- Database optimization and indexing
- Caching with Redis
- Load balancing capabilities

## Next Steps

1. Install Python and required dependencies
2. Set up PostgreSQL and Redis
3. Configure environment variables
4. Run database migrations
5. Start development server
6. Test API endpoints
7. Review documentation
8. Implement additional Rwanda-specific features

For technical support or questions about Rwanda-specific implementations,
refer to the detailed documentation in each app directory.

The platform is designed to handle 10,000+ concurrent users with 99.9% uptime
as required for Rwanda government compliance.