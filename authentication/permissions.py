from rest_framework import permissions
from rest_framework.permissions import BasePermission, IsAdminUser


class IsAdminOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True

        return bool(request.user and request.user.is_staff)

class IsAdminOrCarAgency(BasePermission):
    """
    Only Admin or Car Agency role can add/update/delete.
    """
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            (request.user.is_staff or request.user.role == "CA")
        )

class IsCustomer(BasePermission):
    def has_permission(self, request, view):
        return hasattr(request.user, 'customer')

class IsProvider(BasePermission):
    def has_permission(self, request, view):
        return hasattr(request.user, 'provider')

class IsStoreProvider(BasePermission):
    """
    Only providers with service name containing 'store' can access.
    """
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        # Allow admin access
        if request.user.is_staff:
            return True
            
        # Check if user is a provider with store service
        if hasattr(request.user, 'provider'):
            provider = request.user.provider
            return provider and 'store' in provider.service.name.lower()
        
        return False

class IsCustomerOrAdmin(BasePermission):
    def has_permission(self, request, view):
        return (hasattr(request.user, 'customer') or request.user.is_staff)
