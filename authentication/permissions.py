"""
Custom permissions for SafeBoda Rwanda
"""
from rest_framework import permissions


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow owners to edit their objects.
    """
    def has_object_permission(self, request, view, obj):
        # Read permissions for any request
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Write permissions only to the owner
        return obj.user == request.user if hasattr(obj, 'user') else obj == request.user


class IsDriverUser(permissions.BasePermission):
    """
    Permission for driver-only endpoints
    """
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.role in ['driver', 'admin']
        )


class IsAdminOrDriver(permissions.BasePermission):
    """
    Permission for admin or driver users
    """
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.role in ['admin', 'driver']
        )


class IsAdminUser(permissions.BasePermission):
    """
    Permission for admin users only
    """
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.role == 'admin'
        )


class IsGovernmentUser(permissions.BasePermission):
    """
    Permission for government officials
    """
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.role in ['government', 'admin']
        )


class IsCustomerUser(permissions.BasePermission):
    """
    Permission for customer users
    """
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.role in ['customer', 'admin']
        )