from django.contrib import admin
from django.contrib.auth.models import Group
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from authentication.models import (
    User,
    UserOtp,
    Service,
    Provider,
    Driver,
    DriverCar,
    Customer,
    CustomerPlace,
    RideStatus,
    UserPoints,
    Product,
    ProductImage,
    Purchase
)
from django import forms

admin.site.unregister(Group)
admin.site.register(User)
admin.site.register(UserOtp)
admin.site.register(Service)
admin.site.register(Provider)
admin.site.register(Driver)
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
        self.fields['provider'].queryset = Provider.objects.filter(service__name__icontains='store')

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    form = ProductAdminForm
    list_display = ('name', 'provider_name', 'points_price', 'stock', 'status', 'created_at')
    list_filter = ('is_active', 'provider', 'created_at')
    search_fields = ('name', 'description', 'provider__user__name')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at', 'preview_image')
    fieldsets = (
        (_('Basic Information'), {
            'fields': ('name', 'description', 'provider')
        }),
        (_('Pricing and Stock'), {
            'fields': ('points_price', 'stock')
        }),
        (_('Status'), {
            'fields': ('is_active',)
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def provider_name(self, obj):
        return obj.provider.user.name
    provider_name.short_description = _('Provider Name')
    
    def status(self, obj):
        if obj.is_active:
            return format_html('<span style="color: green;">●</span> Active')
        return format_html('<span style="color: red;">●</span> Inactive')
    status.short_description = _('Status')
    
    def preview_image(self, obj):
        if obj.images.exists():
            return format_html('<img src="{}" width="100" height="100" style="object-fit: cover;" />', 
                             obj.images.first().image.url)
        return _('No image')
    preview_image.short_description = _('Preview')

@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ('product_name', 'preview_image')
    list_filter = ('product',)
    search_fields = ('product__name',)
    ordering = ('product',)
    readonly_fields = ('preview_image',)
    
    def product_name(self, obj):
        return obj.product.name
    product_name.short_description = _('Product Name')
    
    def preview_image(self, obj):
        return format_html('<img src="{}" width="100" height="100" style="object-fit: cover;" />', 
                         obj.image.url)
    preview_image.short_description = _('Preview')

@admin.register(Purchase)
class PurchaseAdmin(admin.ModelAdmin):
    list_display = ('customer_name', 'product_name', 'points_spent', 'quantity', 'created_at')
    list_filter = ('created_at', 'product__provider')
    search_fields = ('customer__user__name', 'product__name')
    ordering = ('-created_at',)
    readonly_fields = ('created_at',)
    fieldsets = (
        (_('Purchase Information'), {
            'fields': ('customer', 'product', 'quantity', 'points_spent')
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
