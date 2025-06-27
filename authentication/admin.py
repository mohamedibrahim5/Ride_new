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
    ProductImage
)
from django import forms
from rest_framework.authtoken.models import Token
import ast
from django.conf import settings

admin.site.unregister(Group)
admin.site.register(User)
admin.site.register(UserOtp)
#admin.site.register(Service)
admin.site.register(Provider)
admin.site.register(DriverCar)
admin.site.register(Customer)
admin.site.register(CustomerPlace)
admin.site.register(RideStatus)

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
        images = obj.images.all()[:3]  # Show up to 3 images
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
    list_editable = ("available",)  # ✅ now you CAN edit if you really want
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

