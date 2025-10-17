"""
Testing framework models for SafeBoda Rwanda
Stores test results, coverage data, and performance metrics
"""

from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
import json

User = get_user_model()


class TestSuite(models.Model):
    """
    Test suite execution record
    """
    name = models.CharField(max_length=200)
    test_type = models.CharField(max_length=50, choices=[
        ('unit', 'Unit Tests'),
        ('integration', 'Integration Tests'),
        ('api', 'API Tests'),
        ('performance', 'Performance Tests'),
        ('security', 'Security Tests'),
        ('rwanda', 'Rwanda Context Tests'),
    ])
    status = models.CharField(max_length=20, choices=[
        ('running', 'Running'),
        ('passed', 'Passed'),
        ('failed', 'Failed'),
        ('error', 'Error'),
    ], default='running')
    
    # Test metrics
    total_tests = models.PositiveIntegerField(default=0)
    passed_tests = models.PositiveIntegerField(default=0)
    failed_tests = models.PositiveIntegerField(default=0)
    skipped_tests = models.PositiveIntegerField(default=0)
    
    # Coverage metrics
    coverage_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    lines_covered = models.PositiveIntegerField(null=True, blank=True)
    lines_total = models.PositiveIntegerField(null=True, blank=True)
    
    # Performance metrics
    execution_time = models.DurationField(null=True, blank=True)
    memory_usage = models.PositiveIntegerField(null=True, blank=True, help_text="Memory usage in MB")
    
    # Results
    results = models.JSONField(default=dict)
    error_details = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} - {self.status}"


class TestCase(models.Model):
    """
    Individual test case record
    """
    suite = models.ForeignKey(TestSuite, on_delete=models.CASCADE, related_name='test_cases')
    name = models.CharField(max_length=300)
    module = models.CharField(max_length=200)
    status = models.CharField(max_length=20, choices=[
        ('passed', 'Passed'),
        ('failed', 'Failed'),
        ('error', 'Error'),
        ('skipped', 'Skipped'),
    ])
    
    execution_time = models.DurationField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    traceback = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.module}.{self.name} - {self.status}"


class CoverageReport(models.Model):
    """
    Code coverage report
    """
    test_suite = models.OneToOneField(TestSuite, on_delete=models.CASCADE, related_name='coverage_report')
    
    # Overall coverage
    overall_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    lines_covered = models.PositiveIntegerField()
    lines_total = models.PositiveIntegerField()
    branches_covered = models.PositiveIntegerField(default=0)
    branches_total = models.PositiveIntegerField(default=0)
    
    # Module-specific coverage
    module_coverage = models.JSONField(default=dict)
    
    # Missing lines
    missing_lines = models.JSONField(default=dict)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Coverage Report - {self.overall_percentage}%"


class PerformanceMetric(models.Model):
    """
    Performance testing metrics
    """
    test_suite = models.ForeignKey(TestSuite, on_delete=models.CASCADE, related_name='performance_metrics')
    
    endpoint = models.CharField(max_length=200)
    method = models.CharField(max_length=10)
    
    # Load testing metrics
    concurrent_users = models.PositiveIntegerField()
    total_requests = models.PositiveIntegerField()
    successful_requests = models.PositiveIntegerField()
    failed_requests = models.PositiveIntegerField()
    
    # Response time metrics (in milliseconds)
    avg_response_time = models.DecimalField(max_digits=10, decimal_places=2)
    min_response_time = models.DecimalField(max_digits=10, decimal_places=2)
    max_response_time = models.DecimalField(max_digits=10, decimal_places=2)
    p95_response_time = models.DecimalField(max_digits=10, decimal_places=2)
    p99_response_time = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Throughput metrics
    requests_per_second = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Error rate
    error_rate = models.DecimalField(max_digits=5, decimal_places=2)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.method} {self.endpoint} - {self.concurrent_users} users"


class SecurityScan(models.Model):
    """
    Security vulnerability scan results
    """
    test_suite = models.OneToOneField(TestSuite, on_delete=models.CASCADE, related_name='security_scan')
    
    # Scan results
    vulnerabilities_found = models.PositiveIntegerField(default=0)
    critical_issues = models.PositiveIntegerField(default=0)
    high_issues = models.PositiveIntegerField(default=0)
    medium_issues = models.PositiveIntegerField(default=0)
    low_issues = models.PositiveIntegerField(default=0)
    
    # Specific checks
    authentication_secure = models.BooleanField(default=True)
    authorization_secure = models.BooleanField(default=True)
    input_validation_secure = models.BooleanField(default=True)
    sql_injection_protected = models.BooleanField(default=True)
    xss_protected = models.BooleanField(default=True)
    csrf_protected = models.BooleanField(default=True)
    
    # Detailed results
    vulnerability_details = models.JSONField(default=list)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Security Scan - {self.vulnerabilities_found} vulnerabilities"


class RwandaContextTest(models.Model):
    """
    Rwanda-specific validation tests
    """
    test_suite = models.ForeignKey(TestSuite, on_delete=models.CASCADE, related_name='rwanda_tests')
    
    test_category = models.CharField(max_length=50, choices=[
        ('national_id', 'National ID Validation'),
        ('phone_number', 'Phone Number Validation'),
        ('location', 'Location Hierarchy'),
        ('payment', 'Mobile Money Integration'),
        ('language', 'Multi-language Support'),
        ('compliance', 'RTDA Compliance'),
    ])
    
    test_name = models.CharField(max_length=200)
    status = models.CharField(max_length=20, choices=[
        ('passed', 'Passed'),
        ('failed', 'Failed'),
        ('warning', 'Warning'),
    ])
    
    details = models.JSONField(default=dict)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.test_category} - {self.test_name}"