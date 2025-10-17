"""
Testing settings for SafeBoda Rwanda
"""

from .base import *

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

# Use in-memory SQLite for faster tests
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

# Password hashers (use faster hasher for tests)
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

# Cache (use dummy cache for tests)
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
    }
}

# Email backend for testing
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'

# Celery (use synchronous execution for tests)
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# Disable migrations for faster tests
class DisableMigrations:
    def __contains__(self, item):
        return True

    def __getitem__(self, item):
        return None

MIGRATION_MODULES = DisableMigrations()

# Media files (use temporary directory)
import tempfile
MEDIA_ROOT = tempfile.mkdtemp()

# Testing-specific settings
TESTING = True

# Disable external service calls during testing
SMS_ENABLED = False
EMAIL_ENABLED = False
PAYMENT_GATEWAY_ENABLED = False

# Coverage settings
COVERAGE_REPORT_HTML_OUTPUT_DIR = BASE_DIR / 'htmlcov'
COVERAGE_MODULE_EXCLUDES = [
    'tests$', 'settings$', 'urls$', 'locale$',
    'migrations', 'fixtures', 'admin$', 'django_extensions',
]

# Performance testing settings
PERFORMANCE_TEST_USER_COUNT = 100
PERFORMANCE_TEST_DURATION = 60  # seconds
PERFORMANCE_TEST_RAMP_UP = 10   # seconds

# Security testing settings
SECURITY_TEST_ENABLED = True
SECURITY_SCAN_ENDPOINTS = True

# Rwanda-specific test settings
RWANDA_TEST_PROVINCES = ['Kigali', 'Northern', 'Southern', 'Eastern', 'Western']
RWANDA_TEST_PHONE_NUMBERS = ['+250788123456', '+250788654321', '+250788987654']
RWANDA_TEST_NATIONAL_IDS = ['1199712345678901', '1199812345678902', '1199912345678903']

# Add testing framework to installed apps
LOCAL_APPS = LOCAL_APPS + ['testing_framework'] if 'testing_framework' not in LOCAL_APPS else LOCAL_APPS

# Logging (minimal for tests)
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.NullHandler',
        },
    },
    'root': {
        'handlers': ['console'],
    },
}

# Test-specific Rwanda settings
MTN_MOMO_API_KEY = 'test-api-key'
AIRTEL_MONEY_API_KEY = 'test-api-key'
RTDA_API_BASE_URL = 'http://test.rtda.gov.rw/api'
RTDA_API_KEY = 'test-api-key'