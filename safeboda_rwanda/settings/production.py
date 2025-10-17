"""
Production settings for SafeBoda Rwanda
"""

from .base import *
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

# Security settings
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'

# Static files
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Logging
LOGGING['handlers']['file']['filename'] = '/var/log/safeboda/django.log'
LOGGING['loggers']['django']['level'] = 'WARNING'
LOGGING['loggers']['safeboda_rwanda']['level'] = 'INFO'

# Sentry error tracking
sentry_sdk.init(
    dsn=config('SENTRY_DSN', default=''),
    integrations=[DjangoIntegration()],
    traces_sample_rate=0.1,
    send_default_pii=True,
    environment='production',
)

# Database connection pooling
DATABASES['default']['CONN_MAX_AGE'] = 60
DATABASES['default']['OPTIONS'] = {
    'MAX_CONNS': 20,
    'OPTIONS': {
        'autocommit': True,
    }
}

# Cache settings for production
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': config('REDIS_URL'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'CONNECTION_POOL_KWARGS': {'max_connections': 50}
        }
    }
}

# Email settings for production
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'

# CORS settings (restrictive in production)
CORS_ALLOW_ALL_ORIGINS = False

# Session configuration
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'
SESSION_COOKIE_AGE = 86400  # 24 hours
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

# Production-specific Rwanda settings
RTDA_API_BASE_URL = config('RTDA_API_BASE_URL')
RTDA_API_KEY = config('RTDA_API_KEY')
MTN_MOMO_API_KEY = config('MTN_MOMO_API_KEY')
AIRTEL_MONEY_API_KEY = config('AIRTEL_MONEY_API_KEY')