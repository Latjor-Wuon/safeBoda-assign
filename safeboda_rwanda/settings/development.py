"""
Development settings for SafeBoda Rwanda
"""

from .base import *

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Development middleware
MIDDLEWARE += [
    # 'debug_toolbar.middleware.DebugToolbarMiddleware',  # Disabled for basic setup
]

INSTALLED_APPS += [
    # 'debug_toolbar',  # Disabled for basic setup
    # 'django_extensions',  # Disabled for basic setup
]

# Internal IPs for debug toolbar
INTERNAL_IPS = [
    '127.0.0.1',
]

# Email backend for development
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Static files
STATICFILES_DIRS = [BASE_DIR / 'static']

# Media files
MEDIA_ROOT = BASE_DIR / 'media'

# Cache (use dummy cache in development)
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
    }
}

# Celery (use synchronous execution in development)
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# CORS (allow all origins in development)
CORS_ALLOW_ALL_ORIGINS = True

# Logging (simplified for development)

# Rwanda development settings
MTN_MOMO_API_KEY = 'sandbox-api-key'
AIRTEL_MONEY_API_KEY = 'sandbox-api-key'
RTDA_API_BASE_URL = 'http://sandbox.rtda.gov.rw/api'
RTDA_API_KEY = 'sandbox-api-key'