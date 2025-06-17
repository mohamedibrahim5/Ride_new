from rest_framework import permissions
from rest_framework.permissions import BasePermission, IsAdminUser


class IsAdminOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True

        return bool(request.user and request.user.is_staff)

class IsCustomer(BasePermission):
    def has_permission(self, request, view):
        return hasattr(request.user, 'customer')

class IsProvider(BasePermission):
    def has_permission(self, request, view):
        return hasattr(request.user, 'provider')

class IsCustomerOrAdmin(BasePermission):
    def has_permission(self, request, view):
        return (hasattr(request.user, 'customer') or request.user.is_staff)
