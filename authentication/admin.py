from django.contrib import admin
from django.contrib.auth.models import Group
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from authentication.models import (
    User,
    UserOtp,
    Service,
    Provider,
    DriverCar,
    Customer,
    CustomerPlace,
    RideStatus,
    UserPoints,
    Product,
    Purchase,
    CarAgency,
    CarAvailability,
    CarRental,
    DriverProfile,
    ProductImage,
    ProviderServicePricing,
    PricingZone
)
from django import forms
from rest_framework.authtoken.models import Token
import dal.autocomplete
from dal import autocomplete

admin.site.unregister(Group)

admin.site.register(User)
admin.site.register(UserOtp)
admin.site.register(DriverCar)
admin.site.register(Customer)
admin.site.register(CustomerPlace)

@admin.register(PricingZone)
class PricingZoneAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'description')
    readonly_fields = ('created_at',)
    fieldsets = (
        (_('Basic Information'), {
            'fields': ('name', 'description', 'is_active')
        }),
        (_('Zone Boundaries'), {
            'fields': ('boundaries',),
            'description': _('Define zone boundaries as JSON array of coordinates: [{"lat": 30.0444, "lng": 31.2357}, ...]')
        }),
        (_('Timestamps'), {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
# --- Customized RideStatus admin ---
@admin.register(RideStatus)
class RideStatusAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'client_name', 'provider_name', 'status_display',
        'service_name', 'pickup_coords', 'drop_coords', 'created_at', 'service_price_info'
    )
    list_filter = ('status', 'service')
    search_fields = ('client__name', 'provider__name')
    ordering = ('-created_at',)
    readonly_fields = ('created_at',)

    def client_name(self, obj):
        return obj.client.name
    client_name.short_description = _('Client')

    def provider_name(self, obj):
        return obj.provider.name if obj.provider else '-'
    provider_name.short_description = _('Provider')

    def service_name(self, obj):
        return obj.service.name if obj.service else '-'
    service_name.short_description = _('Service')

    def pickup_coords(self, obj):
        if obj.pickup_lat is not None and obj.pickup_lng is not None:
            return f"{obj.pickup_lat}, {obj.pickup_lng}"
        return "-"
    pickup_coords.short_description = _('Pickup Location')

    def drop_coords(self, obj):
        if obj.drop_lat is not None and obj.drop_lng is not None:
            return f"{obj.drop_lat}, {obj.drop_lng}"
        return "-"
    drop_coords.short_description = _('Drop Location')

    def status_display(self, obj):
        color_map = {
            "pending": "orange",
            "accepted": "blue",
            "starting": "purple",
            "arriving": "teal",
            "finished": "green",
            "cancelled": "red",
        }
        color = color_map.get(obj.status, "black")
        return format_html('<span style="color: {};">●</span> {}', color, obj.get_status_display())
    status_display.short_description = _('Status')

    def service_price_info(self, obj):
        if not obj.provider or not obj.service:
            return "-"
        try:
            pricing = ProviderServicePricing.objects.get(
                provider=obj.provider.provider,
                service=obj.service,
                sub_service=obj.provider.provider.sub_service if obj.provider.provider.sub_service else None
            )
            return f"App Fee: {pricing.application_fee}, Price: {pricing.service_price}, Delivery/km: {pricing.delivery_fee_per_km}"
        except ProviderServicePricing.DoesNotExist:
            return "-"
    service_price_info.short_description = "Service Price Info"

# --- Other existing admin registrations ---

@admin.register(UserPoints)
class UserPointsAdmin(admin.ModelAdmin):
    list_display = ('user_name', 'user_phone', 'points', 'created_at')
    list_filter = ('points',)
    search_fields = ('user__name', 'user__phone')
    ordering = ('-points',)
    readonly_fields = ('created_at',)
    
    def user_name(self, obj):
        return obj.user.name
    user_name.short_description = _('User Name')
    
    def user_phone(self, obj):
        return obj.user.phone
    user_phone.short_description = _('Phone Number')
    
    def created_at(self, obj):
        return obj.user.date_joined
    created_at.short_description = _('Created At')

class ProductAdminForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['provider'].queryset = Provider.objects.filter(services__name__icontains='store')

class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    form = ProductAdminForm
    list_display = ('image_preview', 'name', 'provider_name', 'display_price', 'stock', 'status', 'created_at')
    list_filter = ('is_active', 'provider', 'created_at')
    search_fields = ('name', 'description', 'provider__user__name')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        (_('Basic Information'), {
            'fields': ('name', 'description', 'provider')
        }),
        (_('Pricing and Stock'), {
            'fields': ('display_price', 'stock')
        }),
        (_('Status'), {
            'fields': ('is_active',)
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    inlines = [ProductImageInline]

    def provider_name(self, obj):
        return obj.provider.user.name
    provider_name.short_description = _('Provider Name')

    def status(self, obj):
        if obj.is_active:
            return format_html('<span style="color: green;">●</span> {}', _('Active'))
        return format_html('<span style="color: red;">●</span> {}', _('Inactive'))
    status.short_description = _('Status')

    def image_preview(self, obj):
        images = obj.images.all()[:3]
        if images:
            html = ""
            for image in images:
                html += format_html(
                    '<img src="{}" style="max-height: 40px; max-width: 40px; object-fit: cover; border-radius: 4px; margin-right: 2px;" />',
                    image.image.url
                )
            return format_html(html)
        return "No image"
    image_preview.short_description = _("Preview")
    image_preview.allow_tags = True

@admin.register(Purchase)
class PurchaseAdmin(admin.ModelAdmin):
    list_display = ('customer_name', 'product_name', 'money_spent', 'quantity', 'status_display', 'created_at')
    list_filter = ('status', 'created_at', 'product__provider')
    search_fields = ('customer__user__name', 'product__name')
    ordering = ('-created_at',)
    readonly_fields = ('created_at',)
    fieldsets = (
        (_('Purchase Information'), {
            'fields': ('customer', 'product', 'quantity', 'money_spent')
        }),
        (_('Status'), {
            'fields': ('status',)
        }),
        (_('Timestamps'), {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def customer_name(self, obj):
        return obj.customer.user.name
    customer_name.short_description = _('Customer Name')
    
    def product_name(self, obj):
        return obj.product.name
    product_name.short_description = _('Product Name')
    
    def status_display(self, obj):
        status_colors = {
            'pending': 'orange',
            'confirmed': 'blue',
            'in_progress': 'purple',
            'completed': 'green',
            'cancelled': 'red',
        }
        color = status_colors.get(obj.status, 'black')
        return format_html('<span style="color: {};">●</span> {}', color, obj.get_status_display())
    status_display.short_description = _('Status')

@admin.register(Token)
class TokenAdmin(admin.ModelAdmin):
    list_display = ['key', 'user', 'created']
    search_fields = ['key', 'user__username']

@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ['name', 'created_at']
    search_fields = ['name']
    ordering = ['-created_at']
    
@admin.register(CarAgency)
class CarAgencyAdmin(admin.ModelAdmin):
    list_display = ("provider", "brand", "model", "color", "price_per_hour", "available", "created_at")
    list_filter = ("provider", "brand", "color", "available", "created_at")
    list_editable = ("available",)
    search_fields = ("provider__user__name", "brand", "model", "color")
    readonly_fields = ("created_at",)
    ordering = ("-created_at",)

@admin.register(CarAvailability)
class CarAvailabilityAdmin(admin.ModelAdmin):
    list_display = ("car", "start_time", "end_time")
    list_filter = ("car__brand", "car__model", "start_time", "end_time")
    search_fields = ("car__brand", "car__model")
    ordering = ("-start_time",)

@admin.register(CarRental)
class CarRentalAdmin(admin.ModelAdmin):
    list_display = ("customer", "car", "start_datetime", "end_datetime", "total_price", "status", "created_at")
    list_filter = ("car__brand", "car__model", "start_datetime", "end_datetime", "status")
    search_fields = ("customer__user__name", "car__brand", "car__model")
    readonly_fields = ("total_price", "created_at")
    ordering = ("-created_at",)

@admin.register(DriverProfile)
class DriverProfileAdmin(admin.ModelAdmin):
    list_display = ('user_name', 'user_phone')
    search_fields = ('provider__user__name', 'provider__user__phone')
    
    def user_name(self, obj):
        return obj.provider.user.name
    user_name.short_description = _('User Name')
    
    def user_phone(self, obj):
        return obj.provider.user.phone
    user_phone.short_description = _('Phone Number')

@admin.register(Provider)
class ProviderAdmin(admin.ModelAdmin):
    list_display = ['user', 'is_verified', 'in_ride', 'sub_service']
    list_filter = ['is_verified', 'in_ride', 'sub_service']
    search_fields = ['user__name', 'user__phone', 'sub_service']
    filter_horizontal = ['services']
    
    def get_fields(self, request, obj=None):
        fields = list(super().get_fields(request, obj))
        if obj and not obj.has_maintenance_service():
            if 'sub_service' in fields:
                fields.remove('sub_service')
        return fields
    
    def get_readonly_fields(self, request, obj=None):
        readonly_fields = list(super().get_readonly_fields(request, obj))
        if obj and not obj.has_maintenance_service():
            readonly_fields.append('sub_service')
        return readonly_fields

from dal import autocomplete

class ProviderServicePricingForm(forms.ModelForm):
    class Meta:
        model = ProviderServicePricing
        fields = '__all__'
        widgets = {
            'provider': autocomplete.ModelSelect2(url='provider-autocomplete'),
            'service': autocomplete.ModelSelect2(url='service-autocomplete', forward=['provider']),
        }


# In your admin
from django.contrib import admin

@admin.register(ProviderServicePricing)
class ProviderServicePricingAdmin(admin.ModelAdmin):
    form = ProviderServicePricingForm
    list_display = ('provider_name', 'service_name', 'sub_service', 'zone_name', 'base_fare', 'price_per_km', 'price_per_minute', 'is_active', 'created_at')
    list_filter = ('service', 'zone', 'is_active', 'created_at')
    search_fields = ('provider__user__name', 'service__name', 'sub_service', 'zone__name')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        (_('Basic Information'), {
            'fields': ('provider', 'service', 'sub_service', 'zone', 'is_active')
        }),
        (_('Legacy Pricing (Backward Compatibility)'), {
            'fields': ('application_fee', 'service_price', 'delivery_fee_per_km'),
            'classes': ('collapse',),
            'description': _('These fields are kept for backward compatibility. Use zone-based pricing for new implementations.')
        }),
        (_('Zone-Based Pricing'), {
            'fields': ('base_fare', 'price_per_km', 'price_per_minute', 'minimum_fare')
        }),
        (_('Peak Hour Settings'), {
            'fields': ('peak_hour_multiplier', 'peak_hours_start', 'peak_hours_end'),
            'classes': ('collapse',)
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def provider_name(self, obj):
        return obj.provider.user.name
    provider_name.short_description = _('Provider')
    
    def service_name(self, obj):
        return obj.service.name
    service_name.short_description = _('Service')
    
    def zone_name(self, obj):
        return obj.zone.name if obj.zone else _('Default Zone')
    zone_name.short_description = _('Zone')
