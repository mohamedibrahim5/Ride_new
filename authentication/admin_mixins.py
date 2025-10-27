"""
Admin mixins for controlling model visibility based on user groups.
"""
from django.contrib import admin
from django.contrib.auth.models import Group
from django.db import connection


class RestrictedModelAdminMixin:
    """
    Mixin to restrict model visibility in admin based on user groups.
    
    Usage:
        @admin.register(MyModel)
        class MyModelAdmin(RestrictedModelAdminMixin, admin.ModelAdmin):
            visible_groups = ['Super User', 'Admin']
            # or use visible_to_super_user_only = True
    """
    visible_groups = None  # List of group names that can see this model
    visible_to_super_user_only = False  # If True, only superusers can see
    
    def _get_user_groups(self, user):
        """Get user's groups using raw SQL since User model has groups=None"""
        if not user or not user.is_authenticated or not hasattr(user, 'id'):
            return []
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT g.name FROM auth_group g
                    INNER JOIN auth_user_groups ug ON g.id = ug.group_id
                    WHERE ug.user_id = %s
                    """,
                    [user.id]
                )
                return [row[0] for row in cursor.fetchall()]
        except:
            return []
    
    def has_module_permission(self, request):
        """
        Check if user has permission to see this module in admin.
        """
        # Allow Django superusers to see everything
        if request.user.is_superuser:
            return True
        
        # Check if this model should be visible to super user group only
        if self.visible_to_super_user_only:
            if not request.user.is_staff:
                return False
            user_groups = self._get_user_groups(request.user)
            if 'Super User' in user_groups:
                return True
            return False
        
        # Check visible_groups
        if self.visible_groups:
            if not request.user.is_staff:
                return False
            user_groups = self._get_user_groups(request.user)
            if any(group in user_groups for group in self.visible_groups):
                return True
            return False
        
        # Default: use parent's permission check
        return super().has_module_permission(request)
    
    def has_view_permission(self, request, obj=None):
        """
        Check if user can view this model instance.
        """
        if request.user.is_superuser:
            return True
        
        return self.has_module_permission(request)
    
    def has_add_permission(self, request):
        """
        Check if user can add new instances.
        """
        if request.user.is_superuser:
            return True
        
        return self.has_module_permission(request)
    
    def has_change_permission(self, request, obj=None):
        """
        Check if user can change instances.
        """
        if request.user.is_superuser:
            return True
        
        return self.has_module_permission(request)
    
    def has_delete_permission(self, request, obj=None):
        """
        Check if user can delete instances.
        """
        if request.user.is_superuser:
            return True
        
        return self.has_module_permission(request)

