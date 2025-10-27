"""
EXAMPLES: How to Use RestrictedModelAdminMixin

This file shows examples of how to restrict model visibility in Django admin.
Copy these examples into your authentication/admin.py file.
"""

from authentication.admin_mixins import RestrictedModelAdminMixin

# ============================================
# EXAMPLE 1: Restrict to Super User group only
# ============================================

@admin.register(RestaurantModel)
class RestaurantModelAdmin(RestrictedModelAdminMixin, admin.ModelAdmin):
    """
    Only users in the 'Super User' group can see this model.
    Django superusers will always see everything.
    """
    visible_to_super_user_only = True
    
    list_display = [
        'restaurant_name', 
        'provider', 
        'phone', 
        'email', 
        'is_verified', 
        'created_at'
    ]
    # ... rest of your configuration ...


# ============================================
# EXAMPLE 2: Multiple allowed groups
# ============================================

@admin.register(ProductRestaurant)
class ProductRestaurantAdmin(RestrictedModelAdminMixin, admin.ModelAdmin):
    """
    Users in 'Super User' OR 'Restaurant Manager' groups can see this model.
    """
    visible_groups = ['Super User', 'Restaurant Manager']
    
    list_display = ['name', 'category', 'display_price', 'stock', 'is_active']
    # ... rest of your configuration ...


# ============================================
# EXAMPLE 3: Hide from specific groups
# ============================================

@admin.register(PricingZone)
class PricingZoneAdmin(RestrictedModelAdminMixin, admin.ModelAdmin):
    """
    Only superusers and 'Super User' group can see configuration models.
    Regular admins won't see this.
    """
    visible_groups = ['Super User']  # Only Super User group
    
    list_display = ['name', 'is_active', 'created_at']
    # ... rest of your configuration ...


# ============================================
# EXAMPLE 4: Combine with existing admin classes
# ============================================

# If you already have a complex admin class with mixins:
@admin.register(Order)
class OrderAdmin(RestrictedModelAdminMixin, ExportMixin, admin.ModelAdmin):
    """
    Multi-inheritance example: RestrictedModelAdminMixin + ExportMixin
    """
    visible_groups = ['Super User', 'Restaurant Manager']
    
    # Your existing configuration
    list_display = ['id', 'customer', 'restaurant', 'status', 'total_price', 'created_at']
    # ... rest of your configuration ...


# ============================================
# NOTES:
# ============================================
# 
# 1. Django superusers (is_superuser=True) will ALWAYS see all models
#    regardless of group membership or mixin settings.
#
# 2. The mixin checks both:
#    - Group membership (visible_groups)
#    - Special flag (visible_to_super_user_only)
#
# 3. Users must have:
#    - is_staff = True
#    - Be in one of the allowed groups
#    - Have permissions for the model (via group permissions)
#
# 4. To create groups with specific permissions:
#    python manage.py create_superuser_group --group-name "Restaurant Manager" --models restaurantmodel order productrestaurant
#
# 5. Always test with a non-superuser account to verify restrictions work correctly!

