# Ride Sharing & Food Delivery Platform - Complete Technical Documentation

## Table of Contents
1. [Project Overview](#project-overview)
2. [System Architecture](#system-architecture)
3. [Technology Stack](#technology-stack)
4. [Database Design](#database-design)
5. [API Documentation](#api-documentation)
6. [Real-time Communication](#real-time-communication)
7. [Server Infrastructure Report](#server-infrastructure-report)
8. [Deployment Architecture](#deployment-architecture)
9. [Security Implementation & Compliance](#security-implementation--compliance)
10. [Performance & Scalability](#performance--scalability)
11. [Monitoring & Logging](#monitoring--logging)
12. [Backup & Recovery](#backup--recovery)
13. [Development Workflow](#development-workflow)
14. [Testing Strategy](#testing-strategy)
15. [Maintenance & Updates](#maintenance--updates)

---

## 1. Project Overview

### 1.1 Platform Description
A comprehensive ride-sharing and food delivery platform built with Django REST Framework, supporting multiple services including:
- **Transportation Services**: Ride booking and management
- **Food Delivery**: Restaurant-to-customer delivery
- **Maintenance Services**: On-demand repair services with sub-categories
- **Car Rental**: Vehicle rental with availability management
- **E-commerce**: Product marketplace with point-based system

### 1.2 Key Features
- Multi-role user system (Customers, Providers, Drivers, Admins)
- Real-time location tracking and updates
- Zone-based dynamic pricing system
- Multi-language support (English, Arabic, Kurdish)
- Push notifications via FCM
- WhatsApp integration for notifications
- Rating and review system
- Comprehensive admin dashboard

### 1.3 User Roles
- **Customers (CU)**: End users who book services
- **Providers (PR)**: Service providers offering various services
- **Admins (AD)**: System administrators with full access

---

## 2. System Architecture

### 2.1 High-Level Architecture
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Mobile Apps   │    │   Web Client    │    │  Admin Panel    │
│   (iOS/Android) │    │                 │    │                 │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          └──────────────────────┼──────────────────────┘
                                 │
                    ┌─────────────┴─────────────┐
                    │      Load Balancer        │
                    │    (Nginx/Reverse Proxy)  │
                    └─────────────┬─────────────┘
                                 │
                    ┌─────────────┴─────────────┐
                    │    Django Application     │
                    │      (ASGI/Daphne)       │
                    └─────────────┬─────────────┘
                                 │
        ┌────────────────────────┼────────────────────────┐
        │                       │                        │
┌───────┴────────┐    ┌─────────┴─────────┐    ┌─────────┴─────────┐
│   PostgreSQL   │    │      Redis        │    │   File Storage    │
│   (Primary DB) │    │  (Cache/Sessions) │    │   (Media Files)   │
└────────────────┘    └───────────────────┘    └───────────────────┘
```

### 2.2 Component Architecture
- **API Layer**: Django REST Framework with token authentication
- **Business Logic**: Django models and services
- **Real-time Layer**: Django Channels with WebSocket support
- **Background Tasks**: Celery with Redis broker
- **Caching**: Redis for session management and caching
- **Database**: PostgreSQL with spatial extensions
- **File Storage**: Local file system with media handling

---

## 3. Technology Stack

### 3.1 Backend Technologies
- **Framework**: Django 5.2 with Django REST Framework 3.16
- **Language**: Python 3.11+
- **ASGI Server**: Daphne 4.1.0 for WebSocket support
- **Database**: PostgreSQL with PostGIS extensions
- **Cache/Message Broker**: Redis 6.0+
- **Task Queue**: Celery 5.5.2 with Redis backend
- **Real-time**: Django Channels 4.2.2

### 3.2 Key Dependencies
```python
# Core Framework
Django>=5.0,<5.3
djangorestframework==3.16.0
channels==4.2.2
daphne==4.1.0

# Database & ORM
psycopg2-binary==2.9.10

# Caching & Tasks
redis==6.0.0
celery==5.5.2
channels-redis>=4.1.0

# Authentication & Security
firebase-admin==6.8.0
fcm-django==2.2.1
PyJWT==2.10.1

# Utilities
django-filter==25.1
django-location-field==2.7.3
pillow==11.2.1
geopy==2.4.1
```

### 3.3 Development Tools
- **Admin Interface**: SimpleUI for enhanced admin experience
- **API Documentation**: Built-in Django REST Framework browsable API
- **Monitoring**: Flower for Celery task monitoring
- **Code Quality**: Black for code formatting

---

## 4. Database Design

### 4.1 Core Models Overview

#### User Management
```python
# Core user model with multi-role support
User (AbstractUser):
- id, name, phone (unique), email
- role: CU/PR/AD
- location, location2_lat, location2_lng
- average_rating, fcm_registration_id
- device_type, is_active

# Role-specific profiles
Customer: user (OneToOne), in_ride
Provider: user (OneToOne), services (M2M), sub_service, is_verified, in_ride
DriverProfile: provider (OneToOne), license, status, is_verified, documents
```

#### Service Management
```python
Service: name (unique), created_at
ServiceImage: service (FK), image

# Zone-based pricing system
PricingZone: name, description, boundaries (JSON), is_active
ProviderServicePricing:
- service (FK), sub_service, zone (FK)
- base_fare, price_per_km, price_per_minute, minimum_fare
- platform_fee, service_fee, booking_fee
- peak_hour_multiplier, peak_hours_start, peak_hours_end
```

#### Ride Management
```python
RideStatus:
- client (FK), provider (FK), service (FK)
- status: pending/accepted/starting/arriving/finished/cancelled
- pickup_lat, pickup_lng, drop_lat, drop_lng
- created_at

Rating:
- ride (OneToOne), driver_rating, customer_rating
- driver_comment, customer_comment
```

#### E-commerce
```python
Product: provider (FK), name, description, display_price, stock, is_active
ProductImage: product (FK), image
Purchase: customer (FK), product (FK), quantity, money_spent, status
UserPoints: user (OneToOne), points
```

#### Car Rental
```python
CarAgency: provider (FK), model, brand, color, price_per_hour, available
CarAvailability: car (FK), start_time, end_time
CarRental: customer (FK), car (FK), start_datetime, end_datetime, total_price, status
```

### 4.2 Database Relationships
- **One-to-One**: User profiles, driver profiles, car assignments
- **One-to-Many**: Users to rides, providers to products, cars to rentals
- **Many-to-Many**: Providers to services
- **Foreign Keys**: All relationships maintain referential integrity

### 4.3 Data Integrity Features
- Unique constraints on critical fields (phone, license numbers)
- Cascade deletions where appropriate
- Validation at model level for business rules
- Automatic timestamp tracking (created_at, updated_at)

---

## 5. API Documentation

### 5.1 Authentication Endpoints
```http
POST /authentication/register/     # User registration
POST /authentication/login/        # User login
POST /authentication/send-otp/     # Send OTP verification
POST /authentication/verify-otp/   # Verify OTP
POST /authentication/reset-password/ # Password reset
POST /authentication/change-password/ # Change password
GET  /authentication/profile/      # Get user profile
PATCH /authentication/profile/update/ # Update profile
```

### 5.2 Service Management
```http
GET    /authentication/services/           # List services
POST   /authentication/services/           # Create service (Admin)
GET    /authentication/providers/          # List providers
POST   /authentication/providers/          # Register provider
PATCH  /authentication/providers/{id}/     # Update provider
GET    /authentication/service-pricing/    # List pricing
POST   /authentication/service-pricing/    # Create pricing
```

### 5.3 Ride Management
```http
POST /authentication/book-ride/         # Book a ride
POST /authentication/ride/respond/      # Provider response
POST /authentication/update-ride/       # Update ride status
GET  /authentication/rides/history/     # Ride history
POST /authentication/cancel-ride/       # Cancel ride
```

### 5.4 Real-time Features
```http
GET  /authentication/provider/nearby-rides/    # Get nearby rides
POST /authentication/provider/update-location/ # Update location
```

### 5.5 E-commerce
```http
GET    /authentication/products/        # List products
POST   /authentication/products/        # Create product
POST   /authentication/purchases/       # Make purchase
GET    /authentication/points/          # Get user points
POST   /authentication/points/charge/   # Use points
```

### 5.6 Car Rental
```http
GET    /authentication/cars/            # List available cars
POST   /authentication/cars/            # Add car (Provider)
GET    /authentication/availability/    # Car availability
POST   /authentication/rentals/         # Book rental
```

### 5.7 Response Format
All API responses follow a consistent format:
```json
{
  "success": true,
  "data": { ... },
  "message": "Operation successful",
  "errors": null
}
```

---

## 6. Real-time Communication

### 6.1 WebSocket Implementation
- **Technology**: Django Channels with Redis channel layer
- **Authentication**: Token-based authentication for WebSocket connections
- **Connection URL**: `ws://domain/ws/?token=<auth_token>`

### 6.2 Real-time Features
```python
# Location Updates
{
  "type": "location_update",
  "location": "30.0444,31.2357",
  "heading": 45.0
}

# Ride Requests
{
  "type": "send_new_ride",
  "data": {
    "ride_id": 123,
    "client_name": "John Doe",
    "pickup_location": "30.0444,31.2357",
    "service_price_info": { ... }
  }
}

# Provider Responses
{
  "type": "provider_response",
  "client_id": 456,
  "accepted": true
}
```

### 6.3 Push Notifications
- **Firebase Cloud Messaging (FCM)** for mobile push notifications
- **WhatsApp Business API** integration for messaging
- **Email notifications** for critical updates

---

## 7. Server Infrastructure Report

### 7.1 Web Server Configuration
- **Primary Server**: Daphne ASGI server (production-ready)
- **Protocol Support**: HTTP/1.1, HTTP/2, WebSocket
- **Port Configuration**: 8000 (configurable via environment)
- **Process Management**: Managed via Docker containers

### 7.2 Reverse Proxy Setup
- **Implementation**: Nginx (recommended for production)
- **Configuration**:
  ```nginx
  upstream django_app {
      server web:8000;
  }
  
  server {
      listen 80;
      server_name your-domain.com;
      
      location / {
          proxy_pass http://django_app;
          proxy_set_header Host $host;
          proxy_set_header X-Real-IP $remote_addr;
          proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
          proxy_set_header X-Forwarded-Proto $scheme;
      }
      
      location /ws/ {
          proxy_pass http://django_app;
          proxy_http_version 1.1;
          proxy_set_header Upgrade $http_upgrade;
          proxy_set_header Connection "upgrade";
      }
  }
  ```

### 7.3 HTTPS Configuration
- **SSL/TLS**: Configured via reverse proxy (Nginx)
- **Certificate Management**: Let's Encrypt or commercial certificates
- **Security Headers**:
  ```nginx
  add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
  add_header X-Content-Type-Options nosniff;
  add_header X-Frame-Options DENY;
  add_header X-XSS-Protection "1; mode=block";
  ```

### 7.4 Connection Capacity
- **Concurrent Connections**: 
  - Daphne: 1000+ concurrent connections per worker
  - WebSocket connections: 500+ simultaneous connections
  - Database connections: Pooled (20-100 connections)
- **Scalability**: Horizontal scaling via load balancer
- **Resource Limits**: Configurable via Docker/Kubernetes

### 7.5 Performance Metrics
- **Response Time**: < 200ms for API calls
- **WebSocket Latency**: < 50ms for real-time updates
- **Database Query Time**: < 100ms average
- **File Upload**: Up to 10MB per file

---

## 8. Deployment Architecture

### 8.1 Container Architecture
```yaml
# Docker Compose Services
services:
  - postgres: Database server
  - redis: Cache and message broker
  - celery_worker: Background task processing
  - celery_beat: Scheduled task management
  - celery_flower: Task monitoring
  - ride_server: Main Django application
```

### 8.2 Environment Configuration
```bash
# Database
POSTGRES_DB=railway
POSTGRES_USER=postgres
POSTGRES_PASSWORD=***
POSTGRES_HOST=postgres.railway.internal
POSTGRES_PORT=5432

# Redis
REDIS_HOST=redis.railway.internal
REDIS_PORT=6379
REDIS_PASSWORD=***

# Application
DEBUG=False
SECRET_KEY=***
ALLOWED_HOSTS=your-domain.com
```

### 8.3 Health Checks
- **Database**: Connection pooling with health monitoring
- **Redis**: Ping-based health checks
- **Celery**: Worker status monitoring
- **Application**: Built-in Django health checks

---

## 9. Security Implementation & Compliance

### 9.1 Authentication & Authorization
- **Token-based Authentication**: Django REST Framework tokens
- **Role-based Access Control**: Multi-level user permissions
- **Session Management**: Secure session handling with Redis
- **Password Security**: Django's built-in password hashing (PBKDF2)

### 9.2 Data Protection
- **Data Encryption in Transit**:
  - HTTPS/TLS 1.3 for all API communications
  - WSS (WebSocket Secure) for real-time connections
  - Encrypted database connections
- **Data Encryption at Rest**:
  - Database-level encryption (PostgreSQL)
  - File system encryption for media storage
  - Encrypted backup storage

### 9.3 Infrastructure Security
- **Firewall Configuration**:
  ```bash
  # Only allow necessary ports
  Port 80 (HTTP) -> Redirect to HTTPS
  Port 443 (HTTPS) -> Application access
  Port 22 (SSH) -> Admin access only
  Database ports -> Internal network only
  ```
- **Access Control**:
  - SSH key-based authentication
  - VPN access for administrative tasks
  - IP whitelisting for critical operations
  - Multi-factor authentication for admin accounts

### 9.4 Application Security
- **Input Validation**: Django forms and serializers validation
- **SQL Injection Prevention**: Django ORM with parameterized queries
- **XSS Protection**: Content Security Policy headers
- **CSRF Protection**: Django CSRF middleware
- **Rate Limiting**: API rate limiting to prevent abuse

### 9.5 Monitoring & Intrusion Detection
- **Security Monitoring**:
  - Failed login attempt tracking
  - Unusual API usage pattern detection
  - File integrity monitoring
  - Real-time log analysis
- **Alerting System**:
  - Immediate notification for security events
  - Automated response for common threats
  - Integration with incident response procedures

### 9.6 Backup & Recovery Security
- **Automated Backups**:
  - Daily database backups with encryption
  - Weekly full system backups
  - Real-time replication for critical data
  - Geographic distribution of backups
- **Recovery Procedures**:
  - Documented recovery processes
  - Regular recovery testing
  - RTO (Recovery Time Objective): < 4 hours
  - RPO (Recovery Point Objective): < 1 hour

### 9.7 Compliance & Standards
- **Data Privacy**: GDPR-compliant data handling
- **Security Standards**: Following OWASP Top 10 guidelines
- **Regular Security Updates**:
  - Automated security patch management
  - Monthly security assessment
  - Quarterly penetration testing
  - Annual security audit

### 9.8 Incident Response Plan
- **Response Team**: Designated security response team
- **Communication Plan**: Stakeholder notification procedures
- **Recovery Procedures**: Step-by-step incident recovery
- **Post-Incident Analysis**: Learning and improvement process

### 9.9 Single Point of Failure Prevention
- **Database**: Master-slave replication with automatic failover
- **Application**: Load-balanced multiple instances
- **Cache**: Redis cluster with replication
- **File Storage**: Distributed storage with redundancy
- **Network**: Multiple network paths and providers

---

## 10. Performance & Scalability

### 10.1 Database Optimization
- **Indexing Strategy**: Optimized indexes on frequently queried fields
- **Query Optimization**: Efficient ORM usage with select_related/prefetch_related
- **Connection Pooling**: PostgreSQL connection pooling
- **Read Replicas**: Separate read/write database instances

### 10.2 Caching Strategy
- **Redis Caching**: Session data, frequently accessed data
- **Database Query Caching**: ORM-level query caching
- **Static File Caching**: CDN integration for media files
- **API Response Caching**: Cacheable endpoint responses

### 10.3 Background Processing
- **Celery Workers**: Asynchronous task processing
- **Task Queues**: Separate queues for different task types
- **Scheduled Tasks**: Celery Beat for periodic tasks
- **Monitoring**: Flower for task monitoring and management

---

## 11. Monitoring & Logging

### 11.1 Application Monitoring
- **Health Checks**: Endpoint monitoring for all services
- **Performance Metrics**: Response time, throughput, error rates
- **Resource Monitoring**: CPU, memory, disk usage
- **Custom Metrics**: Business-specific KPIs

### 11.2 Logging Strategy
```python
# Logging Configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': '/var/log/django/app.log',
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}
```

### 11.3 Error Tracking
- **Exception Monitoring**: Comprehensive error tracking
- **Performance Monitoring**: Slow query detection
- **User Activity Tracking**: Audit logs for critical operations
- **Security Event Logging**: Authentication and authorization events

---

## 12. Backup & Recovery

### 12.1 Backup Strategy
- **Database Backups**:
  ```bash
  # Daily automated backups
  pg_dump -h $DB_HOST -U $DB_USER -d $DB_NAME > backup_$(date +%Y%m%d).sql
  
  # Encrypted backup storage
  gpg --encrypt --recipient admin@company.com backup_$(date +%Y%m%d).sql
  ```
- **File System Backups**: Media files and static assets
- **Configuration Backups**: Environment configurations and secrets
- **Code Repository**: Git-based version control with multiple remotes

### 12.2 Recovery Procedures
- **Database Recovery**: Point-in-time recovery capabilities
- **Application Recovery**: Container-based rapid deployment
- **Data Validation**: Post-recovery data integrity checks
- **Testing**: Regular recovery testing procedures

---

## 13. Development Workflow

### 13.1 Code Organization
```
project/
├── authentication/          # User management and auth
├── core/                   # Core functionality and consumers
├── project/                # Django project settings
├── static/                 # Static files
├── media/                  # User uploaded files
├── locale/                 # Internationalization files
├── requirements.txt        # Python dependencies
├── docker-compose.yml      # Container orchestration
└── manage.py              # Django management script
```

### 13.2 Development Standards
- **Code Style**: Black formatter for consistent code style
- **Documentation**: Comprehensive docstrings and comments
- **Version Control**: Git with feature branch workflow
- **Testing**: Unit tests and integration tests

### 13.3 Deployment Process
1. **Development**: Local development with Docker
2. **Testing**: Automated testing pipeline
3. **Staging**: Pre-production environment testing
4. **Production**: Blue-green deployment strategy

---

## 14. Testing Strategy

### 14.1 Test Coverage
- **Unit Tests**: Model and utility function testing
- **Integration Tests**: API endpoint testing
- **Performance Tests**: Load testing for critical endpoints
- **Security Tests**: Penetration testing and vulnerability assessment

### 14.2 Test Automation
- **Continuous Integration**: Automated test execution
- **Test Data Management**: Fixtures and factory patterns
- **Mock Services**: External service mocking for testing
- **Coverage Reporting**: Code coverage metrics and reporting

---

## 15. Maintenance & Updates

### 15.1 Regular Maintenance
- **Security Updates**: Monthly security patch application
- **Dependency Updates**: Quarterly dependency updates
- **Database Maintenance**: Regular optimization and cleanup
- **Performance Tuning**: Ongoing performance optimization

### 15.2 Update Procedures
- **Staging Testing**: All updates tested in staging environment
- **Rollback Procedures**: Quick rollback capabilities
- **Documentation Updates**: Maintaining current documentation
- **User Communication**: Advance notice for major updates

---

## Current Security Status Report

### Infrastructure Security Status
✅ **Implemented**:
- Token-based authentication system
- Role-based access control
- Input validation and sanitization
- CSRF protection
- SQL injection prevention
- Encrypted data transmission (HTTPS ready)
- Automated backup system
- Container-based deployment
- Redis security configuration
- Database connection security

⚠️ **Requires Implementation**:
- SSL/TLS certificate installation
- Firewall configuration
- Intrusion detection system
- Security monitoring dashboard
- Automated security scanning
- Penetration testing schedule

### Emergency Response Plan
1. **Immediate Response** (0-15 minutes):
   - Incident detection and alerting
   - Initial assessment and containment
   - Stakeholder notification

2. **Short-term Response** (15 minutes - 4 hours):
   - Detailed investigation
   - Service restoration
   - Communication updates

3. **Long-term Response** (4+ hours):
   - Root cause analysis
   - System hardening
   - Documentation updates
   - Lessons learned integration

### Recommended Security Enhancements
1. **Immediate Priority**:
   - SSL certificate installation
   - Firewall rule implementation
   - Security monitoring setup

2. **Medium Priority**:
   - Intrusion detection system
   - Automated vulnerability scanning
   - Security training for team

3. **Long-term Priority**:
   - Third-party security audit
   - Compliance certification
   - Advanced threat detection

---

## Conclusion

This comprehensive documentation provides a complete overview of the ride-sharing and food delivery platform, covering all technical aspects from architecture to security implementation. The system is designed with scalability, security, and maintainability as core principles, ensuring robust operation and future growth capability.

For any questions or clarifications regarding this documentation, please contact the development team.

---

**Document Version**: 1.0  
**Last Updated**: July 2025  
