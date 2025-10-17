"""
Testing framework configuration for SafeBoda Rwanda
"""
from django.apps import AppConfig


class TestingFrameworkConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'testing_framework'
    verbose_name = 'Testing Framework'