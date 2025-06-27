from rest_framework import permissions
from rest_framework.permissions import BasePermission, IsAdminUser, SAFE_METHODS


class IsAdminOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True

        return bool(request.user and request.user.is_staff)

class IsAdminOrCarAgency(BasePermission):
    """
    Only Admin or Provider with Car Agency service can add/update/delete.
    """
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        if request.user.is_staff:
            return True
        # Check if user is a provider with service 'Car Agency'
        provider = getattr(request.user, 'provider', None)
        if provider and provider.services.filter(name__iexact='car agency').exists():
            return True
        return False

    def has_object_permission(self, request, view, obj):
        if request.user.is_staff:
            return True
        provider = getattr(request.user, 'provider', None)
        if not provider or not provider.services.filter(name__iexact='car agency').exists():
            return False
        # CarAgency object
        if hasattr(obj, 'provider_id'):
            return obj.provider_id == provider.id
        # CarAvailability object
        if hasattr(obj, 'car') and hasattr(obj.car, 'provider_id'):
            return obj.car.provider_id == provider.id
        # CarRental object
        if hasattr(obj, 'car') and hasattr(obj.car, 'provider_id'):
            return obj.car.provider_id == provider.id
        return False

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
        provider = getattr(request.user, 'provider', None)
        if provider and provider.services.filter(name__icontains='store').exists():
            return True
        return False

class IsCustomerOrAdmin(BasePermission):
    def has_permission(self, request, view):
        return (hasattr(request.user, 'customer') or request.user.is_staff)

class IsAdminOrOwnCarAgency(BasePermission):
    """
    Only Admin or Provider with Car Agency service can access their own CarAgency data.
    """
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        if request.user.is_staff:
            return True
        provider = getattr(request.user, 'provider', None)
        if provider and provider.services.filter(name__iexact='car agency').exists():
            return True
        return False

    def has_object_permission(self, request, view, obj):
        if request.user.is_staff:
            return True
        provider = getattr(request.user, 'provider', None)
        if not provider or not provider.services.filter(name__iexact='car agency').exists():
            return False
        # CarAgency object
        if hasattr(obj, 'provider_id'):
            return obj.provider_id == provider.id
        # CarAvailability object
        if hasattr(obj, 'car') and hasattr(obj.car, 'provider_id'):
            return obj.car.provider_id == provider.id
        # CarRental object
        if hasattr(obj, 'car') and hasattr(obj.car, 'provider_id'):
            return obj.car.provider_id == provider.id
        return False

class ProductImagePermission(BasePermission):
    def has_permission(self, request, view):
        print("Checking ProductImagePermission...")
        if request.method in SAFE_METHODS:
            print("SAFE_METHODS: allowed")
            return True
        user = request.user
        print("User:", user)
        if not user.is_authenticated:
            print("User not authenticated")
            return False
        provider = getattr(user, 'provider', None)
        print("Provider:", provider)
        if not provider:
            print("User has no provider")
            return False
        has_store = provider.services.filter(name__icontains='store').exists()
        print(f"Provider has 'store' service: {has_store}")
        return has_store
