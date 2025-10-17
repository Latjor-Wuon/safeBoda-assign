"""
Testing framework serializers for SafeBoda Rwanda
"""

from rest_framework import serializers
from .models import (
    TestSuite, TestCase, CoverageReport, PerformanceMetric, 
    SecurityScan, RwandaContextTest
)


class TestCaseSerializer(serializers.ModelSerializer):
    """
    Serializer for individual test cases
    """
    class Meta:
        model = TestCase
        fields = [
            'id', 'name', 'module', 'status', 'execution_time',
            'error_message', 'traceback', 'created_at'
        ]


class TestSuiteSerializer(serializers.ModelSerializer):
    """
    Serializer for test suites
    """
    test_cases = TestCaseSerializer(many=True, read_only=True)
    success_rate = serializers.SerializerMethodField()
    
    class Meta:
        model = TestSuite
        fields = [
            'id', 'name', 'test_type', 'status', 'total_tests',
            'passed_tests', 'failed_tests', 'skipped_tests',
            'coverage_percentage', 'lines_covered', 'lines_total',
            'execution_time', 'memory_usage', 'results', 'error_details',
            'created_at', 'updated_at', 'test_cases', 'success_rate'
        ]
    
    def get_success_rate(self, obj):
        """Calculate test success rate"""
        if obj.total_tests == 0:
            return 0
        return round((obj.passed_tests / obj.total_tests) * 100, 2)


class CoverageReportSerializer(serializers.ModelSerializer):
    """
    Serializer for code coverage reports
    """
    branch_coverage_percentage = serializers.SerializerMethodField()
    coverage_grade = serializers.SerializerMethodField()
    
    class Meta:
        model = CoverageReport
        fields = [
            'id', 'overall_percentage', 'lines_covered', 'lines_total',
            'branches_covered', 'branches_total', 'branch_coverage_percentage',
            'module_coverage', 'missing_lines', 'coverage_grade', 'created_at'
        ]
    
    def get_branch_coverage_percentage(self, obj):
        """Calculate branch coverage percentage"""
        if obj.branches_total == 0:
            return 0
        return round((obj.branches_covered / obj.branches_total) * 100, 2)
    
    def get_coverage_grade(self, obj):
        """Assign coverage grade based on percentage"""
        percentage = float(obj.overall_percentage)
        if percentage >= 95:
            return 'A+'
        elif percentage >= 90:
            return 'A'
        elif percentage >= 85:
            return 'B+'
        elif percentage >= 80:
            return 'B'
        elif percentage >= 70:
            return 'C'
        else:
            return 'F'


class PerformanceMetricSerializer(serializers.ModelSerializer):
    """
    Serializer for performance testing metrics
    """
    performance_grade = serializers.SerializerMethodField()
    throughput_status = serializers.SerializerMethodField()
    
    class Meta:
        model = PerformanceMetric
        fields = [
            'id', 'endpoint', 'method', 'concurrent_users', 'total_requests',
            'successful_requests', 'failed_requests', 'avg_response_time',
            'min_response_time', 'max_response_time', 'p95_response_time',
            'p99_response_time', 'requests_per_second', 'error_rate',
            'performance_grade', 'throughput_status', 'created_at'
        ]
    
    def get_performance_grade(self, obj):
        """Assign performance grade based on response times"""
        avg_time = float(obj.avg_response_time)
        if avg_time <= 200:
            return 'Excellent'
        elif avg_time <= 500:
            return 'Good'
        elif avg_time <= 1000:
            return 'Fair'
        else:
            return 'Poor'
    
    def get_throughput_status(self, obj):
        """Determine throughput status"""
        rps = float(obj.requests_per_second)
        if rps >= 1000:
            return 'High'
        elif rps >= 500:
            return 'Medium'
        elif rps >= 100:
            return 'Low'
        else:
            return 'Very Low'


class SecurityScanSerializer(serializers.ModelSerializer):
    """
    Serializer for security vulnerability scans
    """
    security_score = serializers.SerializerMethodField()
    risk_level = serializers.SerializerMethodField()
    
    class Meta:
        model = SecurityScan
        fields = [
            'id', 'vulnerabilities_found', 'critical_issues', 'high_issues',
            'medium_issues', 'low_issues', 'authentication_secure',
            'authorization_secure', 'input_validation_secure',
            'sql_injection_protected', 'xss_protected', 'csrf_protected',
            'vulnerability_details', 'security_score', 'risk_level', 'created_at'
        ]
    
    def get_security_score(self, obj):
        """Calculate security score (0-100)"""
        base_score = 100
        base_score -= obj.critical_issues * 20
        base_score -= obj.high_issues * 10
        base_score -= obj.medium_issues * 5
        base_score -= obj.low_issues * 2
        return max(0, base_score)
    
    def get_risk_level(self, obj):
        """Determine overall risk level"""
        if obj.critical_issues > 0:
            return 'Critical'
        elif obj.high_issues > 0:
            return 'High'
        elif obj.medium_issues > 3:
            return 'Medium'
        elif obj.vulnerabilities_found > 0:
            return 'Low'
        else:
            return 'Minimal'


class RwandaContextTestSerializer(serializers.ModelSerializer):
    """
    Serializer for Rwanda-specific context tests
    """
    class Meta:
        model = RwandaContextTest
        fields = [
            'id', 'test_category', 'test_name', 'status', 'details', 'created_at'
        ]


class LoadTestRequestSerializer(serializers.Serializer):
    """
    Serializer for load test requests
    """
    concurrent_users = serializers.IntegerField(min_value=1, max_value=1000, default=100)
    duration = serializers.IntegerField(min_value=10, max_value=300, default=60)
    endpoints = serializers.ListField(
        child=serializers.CharField(max_length=200),
        default=['/api/v1/auth/profile/', '/api/v1/bookings/']
    )
    ramp_up = serializers.IntegerField(min_value=1, max_value=60, default=10)
    
    def validate_endpoints(self, value):
        """Validate endpoint URLs"""
        if not value:
            raise serializers.ValidationError("At least one endpoint must be specified")
        
        valid_endpoints = [
            '/api/v1/auth/', '/api/v1/bookings/', '/api/v1/payments/',
            '/api/v1/analytics/', '/api/v1/notifications/'
        ]
        
        for endpoint in value:
            if not any(endpoint.startswith(valid) for valid in valid_endpoints):
                raise serializers.ValidationError(f"Invalid endpoint: {endpoint}")
        
        return value


class TestDataSeedSerializer(serializers.Serializer):
    """
    Serializer for test data seeding requests
    """
    users = serializers.IntegerField(min_value=1, max_value=1000, default=50)
    rides = serializers.IntegerField(min_value=1, max_value=5000, default=100)
    payments = serializers.IntegerField(min_value=1, max_value=5000, default=80)
    reset = serializers.BooleanField(default=False)
    
    def validate(self, data):
        """Validate that payments don't exceed rides"""
        if data['payments'] > data['rides']:
            raise serializers.ValidationError(
                "Number of payments cannot exceed number of rides"
            )
        return data


class TestResultSummarySerializer(serializers.Serializer):
    """
    Serializer for comprehensive test result summaries
    """
    test_suite_id = serializers.IntegerField()
    test_name = serializers.CharField()
    test_type = serializers.CharField()
    status = serializers.CharField()
    execution_time = serializers.DurationField()
    
    # Unit test metrics
    total_tests = serializers.IntegerField()
    passed_tests = serializers.IntegerField()
    failed_tests = serializers.IntegerField()
    success_rate = serializers.DecimalField(max_digits=5, decimal_places=2)
    
    # Coverage metrics
    coverage_percentage = serializers.DecimalField(max_digits=5, decimal_places=2)
    coverage_grade = serializers.CharField()
    
    # Performance metrics
    avg_response_time = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    throughput = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    error_rate = serializers.DecimalField(max_digits=5, decimal_places=2, required=False)
    
    # Security metrics
    vulnerabilities_found = serializers.IntegerField(required=False)
    security_score = serializers.IntegerField(required=False)
    risk_level = serializers.CharField(required=False)
    
    created_at = serializers.DateTimeField()