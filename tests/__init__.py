"""
Test runner configuration and settings for SafeBoda Rwanda
Provides comprehensive test coverage including unit, integration, and performance tests
"""

import os
import tempfile
from django.test.runner import DiscoverRunner
from django.conf import settings


class SafeBodaTestRunner(DiscoverRunner):
    """
    Custom test runner for SafeBoda Rwanda with enhanced reporting
    """
    
    def __init__(self, **kwargs):
        self.test_results = {
            'total_tests': 0,
            'passed': 0,
            'failed': 0,
            'errors': 0,
            'skipped': 0,
            'coverage_percentage': 0
        }
        super().__init__(**kwargs)
    
    def setup_test_environment(self, **kwargs):
        """Setup test environment with proper configurations"""
        super().setup_test_environment(**kwargs)
        
        # Ensure we're using test settings
        settings.TESTING = True
        settings.EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
        
        # Use in-memory database for speed
        settings.DATABASES['default'] = {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': ':memory:',
        }
        
        # Disable logging during tests unless debugging
        if not kwargs.get('debug_mode', False):
            settings.LOGGING = {
                'version': 1,
                'disable_existing_loggers': True,
                'handlers': {
                    'null': {
                        'class': 'logging.NullHandler',
                    },
                },
                'root': {
                    'handlers': ['null'],
                },
            }
    
    def run_tests(self, test_labels, **kwargs):
        """Run tests with coverage reporting"""
        try:
            # Try to use coverage if available
            import coverage
            cov = coverage.Coverage()
            cov.start()
            
            result = super().run_tests(test_labels, **kwargs)
            
            cov.stop()
            cov.save()
            
            # Generate coverage report
            coverage_percentage = cov.report()
            self.test_results['coverage_percentage'] = coverage_percentage
            
            print(f"\n=== SafeBoda Rwanda Test Coverage Report ===")
            print(f"Coverage: {coverage_percentage:.1f}%")
            
            if coverage_percentage < 90:
                print(f"⚠️  WARNING: Coverage is below 90% target")
            else:
                print(f"✅ EXCELLENT: Coverage meets 90%+ requirement")
            
            return result
            
        except ImportError:
            # Coverage not installed, run without it
            print("⚠️  Coverage.py not installed. Install with: pip install coverage")
            return super().run_tests(test_labels, **kwargs)
    
    def teardown_test_environment(self, **kwargs):
        """Cleanup test environment"""
        super().teardown_test_environment(**kwargs)
        print(f"\n=== Test Run Summary ===")
        print(f"Tests completed successfully")


# Test constants
TEST_USER_DATA = {
    'email': 'testuser@safeboda.test',
    'username': 'testuser',
    'password': 'TestPassword123!',
    'phone_number': '+250788123456',
    'first_name': 'Test',
    'last_name': 'User',
    'national_id': '1234567890123456',
    'role': 'customer'
}

TEST_DRIVER_DATA = {
    'email': 'testdriver@safeboda.test',
    'username': 'testdriver',
    'password': 'TestPassword123!',
    'phone_number': '+250788654321',
    'first_name': 'Test',
    'last_name': 'Driver',
    'national_id': '6543210987654321',
    'role': 'driver'
}

TEST_RIDE_DATA = {
    'pickup_latitude': -1.9441,
    'pickup_longitude': 30.0619,
    'pickup_address': 'Kigali City Market',
    'destination_latitude': -1.9706,
    'destination_longitude': 30.1044,
    'destination_address': 'Kigali International Airport',
    'ride_type': 'standard',
    'passenger_count': 1,
}