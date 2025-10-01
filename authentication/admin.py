from django.contrib import admin
from .models import ScheduledRide, ScheduledRideRating
@admin.register(ScheduledRideRating)
class ScheduledRideRatingAdmin(admin.ModelAdmin):
    list_display = ('ride', 'driver_rating', 'customer_rating', 'created_at')
    search_fields = ('ride__client__name', 'ride__provider__name')
    readonly_fields = ('created_at', 'updated_at')


class ScheduledRideRatingInline(admin.StackedInline):
    model = ScheduledRideRating
    extra = 0
    max_num = 1
    can_delete = False
    verbose_name = "Rating"
    verbose_name_plural = "Rating"
    readonly_fields = ('created_at', 'updated_at',)


@admin.register(ScheduledRide)
class ScheduledRideAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'client', 'provider', 'service', 'scheduled_time', 'status', 'created_at'
    )
    list_filter = ('status', 'service')
    search_fields = ('client__name', 'provider__name')
    readonly_fields = ('created_at',)
    inlines = [ScheduledRideRatingInline]
from django.contrib.auth.models import Group
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from django.urls import path, reverse
from authentication.models import (
    User,
    UserOtp,
    Service,
    SubService,
    NameOfCar,
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
    CarPurchase,
    CarSaleListing,
    CarSaleImage,
    DriverProfile,
    ProductImage,
    ProviderServicePricing,
    PricingZone,
    WhatsAppAPISettings,
    PlatformSettings,
    Coupon,
    Notification,
    DriverCarImage,
    RestaurantModel,
    WorkingDay,
    Rating,
    Invoice,
    ProductCategory,
    Cart,
    CartItem,
    Order,
    OrderItem,
    ReviewRestaurant,
    OfferRestaurant,
    DeliveryAddress,
    ProductRestaurant,
    ProductImageRestaurant,
    CouponRestaurant,
)
from .widgets import GoogleMapWidget
from django import forms
from django.utils.timezone import make_aware, get_default_timezone
import pytz
import json
import urllib.parse
from django.conf import settings
from django.template.response import TemplateResponse
from django.contrib.admin import SimpleListFilter, DateFieldListFilter
from django.utils import timezone
from datetime import timedelta
from rest_framework.authtoken.models import Token
import dal.autocomplete
from dal import autocomplete
from import_export import resources, fields
from import_export.admin import ImportExportModelAdmin, ExportMixin
from django.http import HttpResponse
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import io
from django.http import HttpResponse, HttpResponseRedirect
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle, SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from django.contrib import messages
from django.shortcuts import render
from firebase_admin import messaging
import logging
from django.utils.html import escape
from django.utils.safestring import mark_safe

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)



import os
from utils.pdf_export import export_pdf

admin.site.unregister(Group)

class UserAdminForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(render_value=True),
        required=False,
        help_text=_("Leave empty to keep current password. Enter new password to change it.")
    )
    
    class Meta:
        model = User
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make image and location optional for admins
        if self.instance and self.instance.role == 'AD':
            self.fields['image'].required = False
            self.fields['location'].required = False
        elif self.instance and self.instance.pk is None:
            # For new users, make fields optional initially
            self.fields['image'].required = False
            self.fields['location'].required = False

    def clean(self):
        cleaned_data = super().clean()
        role = cleaned_data.get('role')
        image = cleaned_data.get('image')
        location = cleaned_data.get('location')
        
        # Only require image and location if not admin
        if role != 'AD':
            if not image:
                self.add_error('image', 'This field is required for non-admin users.')
            if not location:
                self.add_error('location', 'This field is required for non-admin users.')
        return cleaned_data
    
    def save(self, commit=True):
        user = super().save(commit=False)
        
        # Handle password hashing only if password field was changed
        if 'password' in self.changed_data:
            password = self.cleaned_data.get('password')
            if password:
                user.set_password(password)
            elif not user.pk:  # Only set unusable password for new users
                user.set_unusable_password()
        
        if commit:
            user.save()
        return user

class UserAdmin(admin.ModelAdmin):
    form = UserAdminForm
    list_display = ('name', 'phone', 'role', 'is_staff', 'is_superuser', 'is_active')
    list_filter = ('role', 'is_staff', 'is_superuser', 'is_active')
    search_fields = ('name', 'phone', 'role')
    ordering = ('-date_joined',)
    
    # Organize fields into logical groups
    fieldsets = (
        (_('Basic Information'), {
            'fields': ('name', 'phone', 'email', 'role'),
            'classes': ('wide',)
        }),
        (_('Authentication'), {
            'fields': ('password', 'is_active', 'is_staff', 'is_superuser'),
            'classes': ('wide',)
        }),
        (_('Profile Information'), {
            'fields': ('image', 'location', 'location2_lat', 'location2_lng'),
            'classes': ('wide',),
            'description': _('Image and location are optional for admin users.')
        }),
        (_('System Information'), {
            'fields': ('date_joined', 'last_login', 'average_rating', 'fcm_registration_id', 'device_type'),
            'classes': ('collapse',),
            'description': _('System-generated information.')
        }),
    )
    
    # Make certain fields read-only
    readonly_fields = ('date_joined', 'last_login', 'average_rating')
    actions = ['activate_users', 'deactivate_users', 'make_staff', 'remove_staff', 'send_bulk_notification']
    
    def activate_users(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} users have been activated.')
    activate_users.short_description = "Activate selected users"
    
    def deactivate_users(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} users have been deactivated.')
    deactivate_users.short_description = "Deactivate selected users"
    
    def make_staff(self, request, queryset):
        updated = queryset.update(is_staff=True)
        self.message_user(request, f'{updated} users have been made staff.')
    make_staff.short_description = "Make selected users staff"
    
    def remove_staff(self, request, queryset):
        updated = queryset.update(is_staff=False)
        self.message_user(request, f'{updated} users have been removed from staff.')
    remove_staff.short_description = "Remove staff status from selected users"
    
    def get_fieldsets(self, request, obj=None):
        """Dynamically adjust fieldsets based on user role"""
        fieldsets = list(super().get_fieldsets(request, obj))
        
        # If editing an existing user and they're not admin, make image/location required
        if obj and obj.role != 'AD':
            # Update the description for Profile Information
            for i, (title, fieldset) in enumerate(fieldsets):
                if title == _('Profile Information'):
                    fieldset['description'] = _('Image and location are required for non-admin users.')
                    fieldsets[i] = (title, fieldset)
                    break
        
        return fieldsets    
    
    def send_fcm_notification(self, token, title, body, data=None):
        """
        Sends an FCM notification to a specific device.
        Args:
            token (str): The FCM device token.
            title (str): Notification title.
            body (str): Notification body.
            data (dict, optional): Custom data payload.
        Returns:
            str or None: Message ID if sent successfully, None otherwise.
        """
        logger.info(f"Sending FCM notification to token: {token}")
        try:
            message = messaging.Message(
                notification=messaging.Notification(
                    title=title,
                    body=body,
                ),
                token=token,
                data=data or {}
            )
            response = messaging.send(message)
            logger.info(f"Successfully sent FCM message: {response}")
            return response
        except messaging.ApiCallError as e:
            logger.error(f"FCM API error: {e.code} - {e.message}")
        except Exception as e:
            logger.exception(f"Unexpected error sending FCM message: {e}")
        return None
    
    
    def send_bulk_notification(self, request, queryset):
        if request.POST.get('action') == 'send_bulk_notification' and request.POST.get('apply'):
            title = request.POST.get('title', 'Notification')
            message = request.POST.get('message', '')
        
            if not message:
                self.message_user(request, "Message cannot be empty", level=messages.ERROR)
                return HttpResponseRedirect(request.get_full_path())
        
        # Get the originally selected users from POST data
            selected_ids = request.POST.getlist('_selected_action')
            if not selected_ids:
                selected_ids = queryset.values_list('id', flat=True)
        
        # Get the full queryset again to ensure we have all selected users
            users = User.objects.filter(id__in=selected_ids)
        
            success_count = 0
            failure_count = 0
        
            for user in users:
                if not user.fcm_registration_id:
                   failure_count += 1
                   continue
                
                try:
                    result = self.send_fcm_notification(
                        token=user.fcm_registration_id,
                        title=title,
                        body=message,
                        data={
                            "type": "bulk_notification",
                            "message": message,
                        }
                    )
                    if result:
                        success_count += 1
                    else:
                        failure_count += 1
                except Exception:
                    failure_count += 1
        
            msg = f"Notifications sent: {success_count} successful, {failure_count} failed"
            level = messages.SUCCESS if success_count > 0 else messages.ERROR
            self.message_user(request, msg, level=level)
            return HttpResponseRedirect(request.get_full_path())
    
    # Render the form
        return render(request, 'admin/bulk_notify.html', {
            'users': queryset,
            'opts': self.model._meta,
            'action': 'send_bulk_notification',
            'select_across': request.POST.get('select_across', '0'),
            'selected_ids': request.POST.getlist('_selected_action'),
        })

try:
    admin.site.unregister(User)
except admin.sites.NotRegistered:
    pass
admin.site.register(User, UserAdmin)
admin.site.register(UserOtp)

# @admin.register(Customer)
# class CustomerAdmin(admin.ModelAdmin):
#     list_display = ('user_name', 'user_phone', 'user_email', 'in_ride', 'user_is_active', 'date_joined')
#     list_filter = ('in_ride', 'user__is_active', 'user__role', 'user__date_joined')
#     search_fields = ('user__name', 'user__phone', 'user__email')
#     ordering = ('-user__date_joined',)
#     readonly_fields = ('user',)
    
#     def user_name(self, obj):
#         return obj.user.name
#     user_name.short_description = _('Customer Name')
#     user_name.admin_order_field = 'user__name'
    
#     def user_phone(self, obj):
#         return obj.user.phone
#     user_phone.short_description = _('Phone Number')
#     user_phone.admin_order_field = 'user__phone'
    
#     def user_email(self, obj):
#         return obj.user.email
#     user_email.short_description = _('Email')
#     user_email.admin_order_field = 'user__email'
    
#     def user_is_active(self, obj):
#         if obj.user.is_active:
#             return format_html('<span style="color: green;">✓</span> Active')
#         else:
#             return format_html('<span style="color: red;">✗</span> Inactive')
#     user_is_active.short_description = _('Status')
#     user_is_active.admin_order_field = 'user__is_active'
    
#     def date_joined(self, obj):
#         return obj.user.date_joined.strftime('%Y-%m-%d %H:%M')
#     date_joined.short_description = _('Date Joined')
#     date_joined.admin_order_field = 'user__date_joined'
    
#     # Add custom actions
#     actions = ['activate_customers', 'deactivate_customers', 'mark_in_ride', 'mark_not_in_ride']
    
#     def activate_customers(self, request, queryset):
#         updated = queryset.update(user__is_active=True)
#         self.message_user(request, f'{updated} customers have been activated.')
#     activate_customers.short_description = "Activate selected customers"
    
#     def deactivate_customers(self, request, queryset):
#         updated = queryset.update(user__is_active=False)
#         self.message_user(request, f'{updated} customers have been deactivated.')
#     deactivate_customers.short_description = "Deactivate selected customers"
    
#     def mark_in_ride(self, request, queryset):
#         updated = queryset.update(in_ride=True)
#         self.message_user(request, f'{updated} customers have been marked as in ride.')
#     mark_in_ride.short_description = "Mark selected customers as in ride"
    
#     def mark_not_in_ride(self, request, queryset):
#         updated = queryset.update(in_ride=False)
#         self.message_user(request, f'{updated} customers have been marked as not in ride.')
#     mark_not_in_ride.short_description = "Mark selected customers as not in ride"

# admin.site.register(CustomerPlace)


class GooglePolygonWidget(forms.Textarea):
    class Media:
        js = (
            f'https://maps.googleapis.com/maps/api/js?key={settings.GOOGLE_MAPS_API_KEY}&libraries=drawing',
        )

    def render(self, name, value, attrs=None, renderer=None):
        # Ensure value is JSON list
        if not value or value in ("null", "None"):
            value = "[]"
        else:
            try:
                json.loads(value)
            except Exception:
                value = "[]"

        html = super().render(name, value, attrs, renderer)

        map_html = f"""
        <div id="mapid" style="height: 500px; margin-top: 10px;"></div>
        <script>
        (function() {{
            var map = new google.maps.Map(document.getElementById('mapid'), {{
                center: {{lat: 30.0444, lng: 31.2357}}, // Default Cairo
                zoom: 12
            }});

            var drawingManager = new google.maps.drawing.DrawingManager({{
                drawingMode: google.maps.drawing.OverlayType.POLYGON,
                drawingControl: true,
                drawingControlOptions: {{
                    position: google.maps.ControlPosition.TOP_CENTER,
                    drawingModes: ['polygon']
                }},
                polygonOptions: {{
                    editable: true,
                    draggable: true
                }}
            }});
            drawingManager.setMap(map);

            var existingCoords = {value};
            var drawnPolygon = null;

            // Load existing polygon if present
            if (Array.isArray(existingCoords) && existingCoords.length) {{
                var path = existingCoords.map(function(coord) {{
                    return {{lat: coord.lat, lng: coord.lng}};
                }});
                drawnPolygon = new google.maps.Polygon({{
                    paths: path,
                    editable: true,
                    draggable: true
                }});
                drawnPolygon.setMap(map);

                var bounds = new google.maps.LatLngBounds();
                path.forEach(p => bounds.extend(p));
                map.fitBounds(bounds);

                attachPathListeners(drawnPolygon);
            }}

            function updateTextarea(polygon) {{
                var coords = polygon.getPath().getArray().map(function(latlng) {{
                    return {{lat: latlng.lat(), lng: latlng.lng()}};
                }});
                document.getElementById('id_{name}').value = JSON.stringify(coords);
            }}

            function attachPathListeners(polygon) {{
                google.maps.event.addListener(polygon.getPath(), 'set_at', function() {{
                    updateTextarea(polygon);
                }});
                google.maps.event.addListener(polygon.getPath(), 'insert_at', function() {{
                    updateTextarea(polygon);
                }});
                google.maps.event.addListener(polygon.getPath(), 'remove_at', function() {{
                    updateTextarea(polygon);
                }});
            }}

            // Handle new polygon drawing
            google.maps.event.addListener(drawingManager, 'overlaycomplete', function(event) {{
                if (event.type === google.maps.drawing.OverlayType.POLYGON) {{
                    if (drawnPolygon) drawnPolygon.setMap(null);
                    drawnPolygon = event.overlay;
                    updateTextarea(drawnPolygon);
                    attachPathListeners(drawnPolygon);
                }}
            }});
        }})();
        </script>
        """
        return html + map_html


@admin.register(NameOfCar)
class NameOfCarAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)
    list_filter = ('created_at',)
    readonly_fields = ('created_at',)
    
    def model_list(self, obj):
        # Assuming 'models' is a TextField or CharField containing comma-separated models
        if obj.models:
            return ", ".join([m.strip() for m in obj.models.split(',')])
        return "-"
    model_list.short_description = 'Models'


class PricingZoneForm(forms.ModelForm):
    class Meta:
        model = PricingZone
        fields = '__all__'
        widgets = {
            'boundaries': GoogleMapWidget(),
        }


@admin.register(PricingZone)
class PricingZoneAdmin(admin.ModelAdmin):
    form = PricingZoneForm
    list_display = ('name', 'is_active', 'display_boundaries', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'description')
    readonly_fields = ('created_at',)
    fieldsets = (
        (_('Basic Information'), {
            'fields': ('name', 'description', 'is_active')
        }),
        (_('Zone Boundaries'), {
            'fields': ('boundaries',),
            'description': _('Draw the zone boundaries on the map below.')
        }),
        (_('Timestamps'), {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def display_boundaries(self, obj):
        """Display all boundary points in the admin list."""
        if obj.boundaries and isinstance(obj.boundaries, list):
            boundary_count = len(obj.boundaries)
            if boundary_count > 0:
                # Show all coordinates
                coords = ', '.join([f"lat: {b.get('lat', 'N/A')}, lng: {b.get('lng', 'N/A')}" for b in obj.boundaries])
                return f"{boundary_count} points: {coords}"
        return "No boundaries"

    display_boundaries.short_description = 'Boundaries'
    
class RatingInline(admin.StackedInline):
    model = Rating
    extra = 0
    max_num = 1
    can_delete = False
    verbose_name = "Rating"
    verbose_name_plural = "Rating"
    readonly_fields = ('created_at', 'updated_at',)

@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'ride',
        'client_name',
        'client_phone',
        'driver_name',
        'driver_phone',
        'service_name',
        'issued_at',
        'total_amount',
        'tax',
        'discount',
        'final_amount',
        'status',
        'print_invoice_link',
    )
    list_filter = ('status', 'issued_at')
    search_fields = (
        'ride__id',
        'ride__client__name',
        'ride__client__phone',
        'ride__provider__name',
        'ride__provider__phone',
        'ride__service__name',
    )
    date_hierarchy = 'issued_at'
    ordering = ('-issued_at',)
    readonly_fields = ('issued_at',)

    fieldsets = (
        (None, {
            'fields': ('ride', 'status', 'notes')
        }),
        ('Amounts', {
            'fields': ('total_amount', 'tax', 'discount', 'final_amount')
        }),
        ('Timestamps', {
            'fields': ('issued_at',)
        }),
    )

    def client_name(self, obj):
        return obj.ride.client.name if obj.ride and obj.ride.client else "-"
    client_name.short_description = "Client Name"

    def client_phone(self, obj):
        return obj.ride.client.phone if obj.ride and obj.ride.client else "-"
    client_phone.short_description = "Client Phone"

    def driver_name(self, obj):
        return obj.ride.provider.name if obj.ride and obj.ride.provider else "-"
    driver_name.short_description = "Driver Name"

    def driver_phone(self, obj):
        return obj.ride.provider.phone if obj.ride and obj.ride.provider else "-"
    driver_phone.short_description = "Driver Phone"

    def service_name(self, obj):
        return obj.ride.service.name if obj.ride and obj.ride.service else "-"
    service_name.short_description = "Service"

    def print_invoice_link(self, obj):
        return format_html(
            '<a class="button" target="_blank" href="print/{}/">🖨️ Print</a>', obj.id
        )
    print_invoice_link.short_description = "Print"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('print/<int:invoice_id>/', self.admin_site.admin_view(print_invoice_view), name='print-invoice'),
        ]
        return custom_urls + urls


from django.utils.html import format_html
from django.contrib import admin
from .models import Rating

@admin.register(Rating)
class RatingAdmin(admin.ModelAdmin):
    list_display = (
        'ride_id',
        'driver_name',
        'driver_phone',
        'customer_name',
        'customer_phone',
        'service_name',
        'driver_rating_stars',
        'customer_rating_stars',
        'created_at',
        'updated_at',
    )
    list_filter = ('driver_rating', 'customer_rating', 'created_at')
    search_fields = (
        'ride__id',
        'ride__client__name',
        'ride__provider__name',
        'driver_comment',
        'customer_comment',
        'ride__client__phone',
        'ride__provider__phone',
        'ride__service__name',
    )
    readonly_fields = ('created_at', 'updated_at')

    def ride_id(self, obj):
        return f"Ride #{obj.ride.id}"
    ride_id.short_description = "Ride ID"

    def service_name(self, obj):
        return obj.ride.service.name if obj.ride and obj.ride.service else "-"
    service_name.short_description = "Service"

    def driver_name(self, obj):
        return obj.ride.provider.name if obj.ride and obj.ride.provider else "-"
    driver_name.short_description = "Driver Name"

    def driver_phone(self, obj):
        return obj.ride.provider.phone if obj.ride and obj.ride.provider else "-"
    driver_phone.short_description = "Driver Phone"

    def customer_name(self, obj):
        return obj.ride.client.name if obj.ride and obj.ride.client else "-"
    customer_name.short_description = "Customer Name"

    def customer_phone(self, obj):
        return obj.ride.client.phone if obj.ride and obj.ride.client else "-"
    customer_phone.short_description = "Customer Phone"

    def driver_rating_stars(self, obj):
        return self._render_stars(obj.driver_rating)
    driver_rating_stars.short_description = "⭐ Driver Rating"
    driver_rating_stars.admin_order_field = 'driver_rating'

    def customer_rating_stars(self, obj):
        return self._render_stars(obj.customer_rating)
    customer_rating_stars.short_description = "⭐ Customer Rating"
    customer_rating_stars.admin_order_field = 'customer_rating'

    def _render_stars(self, value):
        if value is None:
            return "-"
        full_star = "★"
        empty_star = "☆"
        return format_html(
            '<span style="color: gold; font-size: 16px;">{}</span>',
            full_star * value + empty_star * (5 - value)
        )


# --- Map Widget ---
class PickupDropMapWidget(forms.Widget):
    def render(self, name, value, attrs=None, renderer=None):
        html = f"""
        <div id="map-container" style="width: 100%; max-width: 1200px; margin:15px auto; border:1px solid #ddd; border-radius:6px; padding:15px; background-color: #f9f9f9;">
            <div id="map" style="width:100%; height:600px; border-radius:4px; border:1px solid #ddd; margin-bottom:15px;"></div>
            <div style="margin-bottom:15px;">
                <span id="pickup_display" style="font-weight: bold; color: #007bff;">Pickup: Not set</span>
                <span id="drop_display" style="font-weight: bold; color: #28a745; margin-left:20px;">Drop: Not set</span>
            </div>
            <div style="display: flex; justify-content: flex-start; align-items: center; margin-bottom:15px;">
                <input type="text" id="search_input" placeholder="Search city or lat,lng (e.g., 30.0444,31.2357)" style="flex:1; max-width:400px; padding:8px; border:1px solid #ccc; border-radius:4px; font-size:14px;">
                <button type="button" id="searchBtn" style="background:#ffc107;color:#333;padding:8px 16px;border:none;border-radius:4px;cursor:pointer; margin-left:10px; font-weight:bold;">Search</button>
            </div>
            <div style="display: flex; justify-content: center; margin-bottom:15px;">
                <button type="button" id="pickupBtn" style="background:#007bff;color:white;padding:8px 16px;border:none;border-radius:4px;cursor:pointer; margin:0 5px; font-weight:bold;">Select Pickup</button>
                <button type="button" id="dropBtn" style="background:#28a745;color:white;padding:8px 16px;border:none;border-radius:4px;cursor:pointer; margin:0 5px; font-weight:bold;">Select Drop</button>
                <button type="button" id="clearBtn" style="background:#dc3545;color:white;padding:8px 16px;border:none;border-radius:4px;cursor:pointer; margin:0 5px; font-weight:bold;">Clear</button>
            </div>
        </div>

        <script>
        (function() {{
            let map, pickupMarker, dropMarker;
            let currentMode = null;

            function updateDisplays() {{
                let pickupText = "Pickup: ";
                const pLat = document.getElementById("pickup_lat").value;
                const pLng = document.getElementById("pickup_lng").value;
                if (pLat && pLng) {{
                    pickupText += parseFloat(pLat).toFixed(6) + ", " + parseFloat(pLng).toFixed(6);
                }} else {{
                    pickupText += "Not set";
                }}
                document.getElementById("pickup_display").innerText = pickupText;

                let dropText = "Drop: ";
                const dLat = document.getElementById("drop_lat").value;
                const dLng = document.getElementById("drop_lng").value;
                if (dLat && dLng) {{
                    dropText += parseFloat(dLat).toFixed(6) + ", " + parseFloat(dLng).toFixed(6);
                }} else {{
                    dropText += "Not set";
                }}
                document.getElementById("drop_display").innerText = dropText;
            }}

            function initMap() {{
                const defaultCenter = {{ lat: 30.0444, lng: 31.2357 }};
                map = new google.maps.Map(document.getElementById("map"), {{
                    center: defaultCenter,
                    zoom: 12,
                }});

                // Load existing pickup
                const pLat = parseFloat(document.getElementById("pickup_lat").value);
                const pLng = parseFloat(document.getElementById("pickup_lng").value);
                if (!isNaN(pLat) && !isNaN(pLng)) {{
                    pickupMarker = new google.maps.Marker({{
                        position: {{ lat: pLat, lng: pLng }},
                        map: map,
                        label: "P"
                    }});
                    map.setCenter({{ lat: pLat, lng: pLng }});
                }}

                // Load existing drop
                const dLat = parseFloat(document.getElementById("drop_lat").value);
                const dLng = parseFloat(document.getElementById("drop_lng").value);
                if (!isNaN(dLat) && !isNaN(dLng)) {{
                    dropMarker = new google.maps.Marker({{
                        position: {{ lat: dLat, lng: dLng }},
                        map: map,
                        label: "D"
                    }});
                }}

                updateDisplays();

                map.addListener("click", function(e) {{
                    const lat = e.latLng.lat();
                    const lng = e.latLng.lng();

                    if (currentMode === "pickup") {{
                        if (pickupMarker) pickupMarker.setMap(null);
                        pickupMarker = new google.maps.Marker({{
                            position: e.latLng,
                            map: map,
                            label: "P"
                        }});
                        document.getElementById("pickup_lat").value = lat;
                        document.getElementById("pickup_lng").value = lng;
                        updateDisplays();
                    }}

                    if (currentMode === "drop") {{
                        if (dropMarker) dropMarker.setMap(null);
                        dropMarker = new google.maps.Marker({{
                            position: e.latLng,
                            map: map,
                            label: "D"
                        }});
                        document.getElementById("drop_lat").value = lat;
                        document.getElementById("drop_lng").value = lng;
                        updateDisplays();
                    }}
                }});
            }}

            document.getElementById("pickupBtn").addEventListener("click", function() {{
                currentMode = "pickup";
                alert("Click on the map or search to select Pickup location.");
            }});

            document.getElementById("dropBtn").addEventListener("click", function() {{
                currentMode = "drop";
                alert("Click on the map or search to select Drop location.");
            }});

            document.getElementById("clearBtn").addEventListener("click", function() {{
                if (pickupMarker) pickupMarker.setMap(null);
                if (dropMarker) dropMarker.setMap(null);
                document.getElementById("pickup_lat").value = "";
                document.getElementById("pickup_lng").value = "";
                document.getElementById("drop_lat").value = "";
                document.getElementById("drop_lng").value = "";
                updateDisplays();
                currentMode = null;
            }});

            document.getElementById("searchBtn").addEventListener("click", function() {{
                const query = document.getElementById("search_input").value.trim();
                if (!query) return;

                const latLngRegex = /^(-?\\d+\\.?\\d*),\\s*(-?\\d+\\.?\\d*)$/;
                const match = query.match(latLngRegex);

                if (match) {{
                    const lat = parseFloat(match[1]);
                    const lng = parseFloat(match[2]);
                    if (!isNaN(lat) && !isNaN(lng)) {{
                        const location = {{ lat, lng }};
                        map.setCenter(location);
                        map.setZoom(15);

                        if (currentMode === "pickup") {{
                            if (pickupMarker) pickupMarker.setMap(null);
                            pickupMarker = new google.maps.Marker({{
                                position: location,
                                map: map,
                                label: "P"
                            }});
                            document.getElementById("pickup_lat").value = lat;
                            document.getElementById("pickup_lng").value = lng;
                            updateDisplays();
                        }} else if (currentMode === "drop") {{
                            if (dropMarker) dropMarker.setMap(null);
                            dropMarker = new google.maps.Marker({{
                                position: location,
                                map: map,
                                label: "D"
                            }});
                            document.getElementById("drop_lat").value = lat;
                            document.getElementById("drop_lng").value = lng;
                            updateDisplays();
                        }}
                        return;
                    }}
                }}

                // Geocode address
                const geocoder = new google.maps.Geocoder();
                geocoder.geocode({{ address: query }}, (results, status) => {{
                    if (status === "OK") {{
                        const location = results[0].geometry.location;
                        map.setCenter(location);
                        map.setZoom(15);

                        if (currentMode === "pickup") {{
                            if (pickupMarker) pickupMarker.setMap(null);
                            pickupMarker = new google.maps.Marker({{
                                position: location,
                                map: map,
                                label: "P"
                            }});
                            document.getElementById("pickup_lat").value = location.lat();
                            document.getElementById("pickup_lng").value = location.lng();
                            updateDisplays();
                        }} else if (currentMode === "drop") {{
                            if (dropMarker) dropMarker.setMap(null);
                            dropMarker = new google.maps.Marker({{
                                position: location,
                                map: map,
                                label: "D"
                            }});
                            document.getElementById("drop_lat").value = location.lat();
                            document.getElementById("drop_lng").value = location.lng();
                            updateDisplays();
                        }}
                    }} else {{
                        alert("Search failed: " + status);
                    }}
                }});
            }});

            window.initMap = initMap;
        }})();
        </script>

        <script async defer src="https://maps.googleapis.com/maps/api/js?key={settings.GOOGLE_MAPS_API_KEY}&callback=initMap"></script>
        """
        return mark_safe(html)



class RideStatusForm(forms.ModelForm):
    map = forms.CharField(widget=PickupDropMapWidget(), required=False, label="Pickup and Drop Locations")

    class Meta:
        model = RideStatus
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["pickup_lat"].widget = forms.HiddenInput(attrs={"id": "pickup_lat"})
        self.fields["pickup_lng"].widget = forms.HiddenInput(attrs={"id": "pickup_lng"})
        self.fields["drop_lat"].widget = forms.HiddenInput(attrs={"id": "drop_lat"})
        self.fields["drop_lng"].widget = forms.HiddenInput(attrs={"id": "drop_lng"})
        
        
@admin.register(RideStatus)
class RideStatusAdmin(admin.ModelAdmin):
    form = RideStatusForm
    list_display = (
        'id', 'client_name', 'provider_name', 'status_display',
        'service_name', 'pickup_coords', 'drop_coords', 'created_at', 'service_price_info','total_price','distance_km', 'duration_minutes'
    )
    list_filter = ('status', 'service')
    search_fields = ('client__name', 'provider__name')
    ordering = ('-created_at',)
    readonly_fields = ('created_at',)
    inlines = [RatingInline]

    

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
        if not obj.service or obj.pickup_lat is None or obj.pickup_lng is None:
            return "-"

        # Get sub_service only for maintenance services
        sub_service = None
        try:
            if obj.service.name.lower() == "maintenance service":
                sub_service = obj.provider.provider.sub_service
        except AttributeError:
            pass  # provider or sub_service might be missing

        # Try to get matching pricing
        pricing = ProviderServicePricing.get_pricing_for_location(
            service=obj.service,
            sub_service=sub_service,
            lat=obj.pickup_lat,
            lng=obj.pickup_lng
        )

        if not pricing:
            return "No pricing found"

        # Estimate duration: assume 30 km/h average speed
        distance_km = obj.distance_km if hasattr(obj, "distance_km") and obj.distance_km else 0
        duration_minutes = (distance_km / 30) * 60 if distance_km > 0 else 0

        # Calculate price using model method
        price = pricing.calculate_price(
            distance_km=distance_km,
            duration_minutes=duration_minutes,
            pickup_time=obj.created_at
        )

        return (
            f"Estimated Price: {price} | Base: {pricing.base_fare}, "
            f"Per km: {pricing.price_per_km}, Per min: {pricing.price_per_minute}, "
            f"Min Fare: {pricing.minimum_fare}"
        )

    service_price_info.short_description = "Service Price Info"

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if obj.status in ("finished", "cancelled"):
            self._reset_flags(obj)
        elif obj.status == "accepted":
            self._set_flags(obj)
            
    def delete_model(self, request, obj):
        client_user = obj.client
        provider_user = obj.provider
        super().delete_model(request, obj)
        self._reset_flags_if_no_active_rides(client_user, provider_user)

    # Handle bulk delete
    def delete_queryset(self, request, queryset):
        affected_clients = set(queryset.values_list("client", flat=True))
        affected_providers = set(queryset.values_list("provider", flat=True))

        queryset.delete()

        from django.contrib.auth import get_user_model
        User = get_user_model()

        for client_id in affected_clients:
            try:
                self._reset_flags_if_no_active_rides(User.objects.get(id=client_id), None)
            except User.DoesNotExist:
                pass

        for provider_id in affected_providers:
            try:
                self._reset_flags_if_no_active_rides(None, User.objects.get(id=provider_id))
            except User.DoesNotExist:
                pass

    def _reset_flags(self, instance):
        # Reset customer in_ride
        try:
            customer = Customer.objects.get(user=instance.client)
            if customer.in_ride:
                customer.in_ride = False
                customer.save()
        except Customer.DoesNotExist:
            pass

        # Reset provider in_ride and driver status
        if instance.provider:
            try:
                provider = Provider.objects.get(user=instance.provider)
                if provider.in_ride:
                    provider.in_ride = False
                    provider.save()

                if hasattr(provider, "driver_profile"):
                    driver = provider.driver_profile
                    if driver.status != "available":
                        driver.status = "available"
                        driver.save()
            except Provider.DoesNotExist:
                pass
            
    def _set_flags(self, instance):
        # Set customer in_ride
        try:
            customer = Customer.objects.get(user=instance.client)
            if not customer.in_ride:
                customer.in_ride = True
                customer.save()
        except Customer.DoesNotExist:
            pass

        # Set provider in_ride and driver status
        if instance.provider:
            try:
                provider = Provider.objects.get(user=instance.provider)
                if not provider.in_ride:
                    provider.in_ride = True
                    provider.save()

                if hasattr(provider, "driver_profile"):
                    driver = provider.driver_profile
                    if driver.status != "in_ride":
                        driver.status = "in_ride"
                        driver.save()
            except Provider.DoesNotExist:
                pass
            
    def _reset_flags_if_no_active_rides(self, client_user, provider_user):
        from django.db.models import Q

        def has_active_rides(user, is_provider=False):
            if not user:
                return False
            filters = {"provider": user} if is_provider else {"client": user}
            return RideStatus.objects.filter(
                Q(**filters),
                status__in=["pending", "accepted", "starting", "arriving"]
            ).exists()

        # Reset client
        if client_user:
            try:
                customer = Customer.objects.get(user=client_user)
                if not has_active_rides(client_user) and customer.in_ride:
                    customer.in_ride = False
                    customer.save()
            except Customer.DoesNotExist:
                pass

        # Reset provider
        if provider_user:
            try:
                provider = Provider.objects.get(user=provider_user)
                if not has_active_rides(provider_user, is_provider=True):
                    if provider.in_ride:
                        provider.in_ride = False
                        provider.save()

                    if hasattr(provider, "driver_profile"):
                        driver = provider.driver_profile
                        if driver.status != "available":
                            driver.status = "available"
                            driver.save()
            except Provider.DoesNotExist:
                pass


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

# class ProductAdminForm(forms.ModelForm):
#     class Meta:
#         model = Product
#         fields = '__all__'

#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)
#         self.fields['provider'].queryset = Provider.objects.filter(services__name__icontains='store')

# class ProductImageInline(admin.TabularInline):
#     model = ProductImage
#     extra = 1
    
# @admin.register(Product)
# class ProductAdmin(admin.ModelAdmin):
#     form = ProductAdminForm
#     list_display = ('image_preview', 'name', 'provider_name', 'display_price', 'stock', 'status', 'created_at')
#     list_filter = ('is_active', 'provider', 'created_at')
#     search_fields = ('name', 'description', 'provider__user__name')
#     ordering = ('-created_at',)
#     readonly_fields = ('created_at', 'updated_at')
#     fieldsets = (
#         (_('Basic Information'), {
#             'fields': ('name', 'description', 'provider')
#         }),
#         (_('Pricing and Stock'), {
#             'fields': ('display_price', 'stock')
#         }),
#         (_('Status'), {
#             'fields': ('is_active',)
#         }),
#         (_('Timestamps'), {
#             'fields': ('created_at', 'updated_at'),
#             'classes': ('collapse',)
#         }),
#     )
#     inlines = [ProductImageInline]

#     def provider_name(self, obj):
#         return obj.provider.user.name
#     provider_name.short_description = _('Provider Name')

#     def status(self, obj):
#         if obj.is_active:
#             return format_html('<span style="color: green;">●</span> {}', _('Active'))
#         return format_html('<span style="color: red;">●</span> {}', _('Inactive'))
#     status.short_description = _('Status')

#     def image_preview(self, obj):
#         images = obj.images.all()[:3]
#         if images:
#             html = ""
#             for image in images:
#                 html += format_html(
#                     '<img src="{}" style="max-height: 40px; max-width: 40px; object-fit: cover; border-radius: 4px; margin-right: 2px;" />',
#                     image.image.url
#                 )
#             return format_html(html)
#         return "No image"
#     image_preview.short_description = _("Preview")
#     image_preview.allow_tags = True
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'display_price', 'stock', 'is_offer', 'is_active', 'created_at')
    list_filter = ('is_active', 'is_offer', 'category', 'created_at')
    search_fields = ('name', 'description', 'category__name')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at')

@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ('product', 'image')
    search_fields = ('product__name',)

@admin.register(Purchase)
class PurchaseAdmin(admin.ModelAdmin):
    list_display = ('customer_name', 'product_name', 'money_spent', 'quantity', 'status_display', 'created_at')
    list_filter = ('status', 'created_at')
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

@admin.register(SubService)
class SubServiceAdmin(admin.ModelAdmin):
    list_display = ['name', 'created_at']
    search_fields = ['name']
    ordering = ['-created_at']

@admin.register(RestaurantModel)
class RestaurantModelAdmin(admin.ModelAdmin):
    list_display = [
        'restaurant_name', 
        'provider', 
        'phone', 
        'email', 
        'is_verified', 
        'average_rating', 
        'working_days_count',
        'created_at'
    ]
    list_filter = [
        'is_verified', 
        'provider',
        'created_at', 
        'average_rating'
    ]
    search_fields = [
        'restaurant_name', 
        'phone', 
        'email', 
        'address'
    ]
    readonly_fields = [
        'created_at', 
        'updated_at', 
        'average_rating'
    ]
    fieldsets = (
        (_('Basic Information'), {
            'fields': (
                'restaurant_name', 
                'restaurant_id_image', 
                'restaurant_license', 
                'restaurant_description'
            )
        }),
        (_('Contact & Location'), {
            'fields': (
                'phone', 
                'email', 
                'address', 
                'latitude', 
                'longitude'
            )
        }),
        (_('Restaurant Details'), {
            'fields': (
                'provider',
                'is_verified', 
                'average_rating', 
                'menu_link'
            )
        }),
        (_('Timestamps'), {
            'fields': (
                'created_at', 
                'updated_at'
            ),
            'classes': ('collapse',)
        }),
    )
    ordering = ['-created_at']
    list_editable = ['is_verified']
    list_per_page = 25

    def working_days_count(self, obj):
        count = obj.working_days.count()
        return f"{count} days"
    working_days_count.short_description = _('Working Days')
    working_days_count.admin_order_field = 'working_days__count'


@admin.register(WorkingDay)
class WorkingDayAdmin(admin.ModelAdmin):
    list_display = [
        'restaurant_name',
        'day_of_week_display', 
        'opening_time', 
        'closing_time',
        'duration_display'
    ]
    list_filter = [
        'day_of_week',
        'restaurant',
        'opening_time',
        'closing_time'
    ]
    search_fields = [
        'restaurant__restaurant_name',
        'day_of_week'
    ]
    ordering = ['restaurant__restaurant_name', 'day_of_week']
    list_per_page = 25

    def restaurant_name(self, obj):
        return obj.restaurant.restaurant_name
    restaurant_name.short_description = _('Restaurant')
    restaurant_name.admin_order_field = 'restaurant__restaurant_name'

    def day_of_week_display(self, obj):
        return obj.get_day_of_week_display()
    day_of_week_display.short_description = _('Day')
    day_of_week_display.admin_order_field = 'day_of_week'

    def duration_display(self, obj):
        from datetime import datetime, timedelta
        try:
            open_time = datetime.strptime(str(obj.opening_time), '%H:%M:%S')
            close_time = datetime.strptime(str(obj.closing_time), '%H:%M:%S')
            
            # Handle case where closing time is next day
            if close_time < open_time:
                close_time += timedelta(days=1)
            
            duration = close_time - open_time
            hours = duration.total_seconds() / 3600
            return f"{hours:.1f} hours"
        except:
            return "-"
    duration_display.short_description = _('Duration')


# DriverProfileResource and Admin
    
@admin.register(CarAgency)
class CarAgencyAdmin(admin.ModelAdmin):
    list_display = ("provider_name", "brand", "model", "color", "price_per_hour", "available", "for_sale", "sale_price", "is_sold", "created_at")
    list_filter = ("provider", "brand", "color", "available", "for_sale", "is_sold", "created_at")
    list_editable = ("available", "for_sale", "sale_price")
    search_fields = ("provider__user__name", "brand", "model", "color")
    readonly_fields = ("created_at",)
    ordering = ("-created_at",)

    def provider_name(self, obj):
        return obj.provider.user.name if obj.provider else '-'
    provider_name.short_description = _('Provider Name')
    provider_name.admin_order_field = 'provider__user__name'

class CarSaleImageInline(admin.TabularInline):
    model = CarSaleImage
    extra = 0
    readonly_fields = ['image_preview']
    fields = ['image', 'image_preview']

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="100" height="60" style="object-fit:cover;" />', obj.image.url)
        return "-"
    image_preview.short_description = "Preview"

@admin.register(CarSaleListing)
class CarSaleListingAdmin(admin.ModelAdmin):
    list_display = ("provider_name", "title", "brand", "model", "year", "mileage_km", "price", "is_active", "is_sold", "created_at")
    list_filter = ("brand", "model", "fuel_type", "transmission", "is_active", "is_sold", "created_at")
    search_fields = ("title", "brand", "model", "provider__user__name")
    list_editable = ("is_active",)
    readonly_fields = ("created_at",)
    inlines = [CarSaleImageInline]

    def provider_name(self, obj):
        return obj.provider.user.name if obj.provider else '-'
    provider_name.short_description = _('Provider')

@admin.register(CarAvailability)
class CarAvailabilityAdmin(admin.ModelAdmin):
    list_display = ("car", "car_brand", "car_model", "start_time", "end_time")
    list_filter = ("car__brand", "car__model", "start_time", "end_time")
    search_fields = ("car__brand", "car__model")
    ordering = ("-start_time",)

    def car_brand(self, obj):
        return obj.car.brand
    car_brand.short_description = _('Brand')
    def car_model(self, obj):
        return obj.car.model
    car_model.short_description = _('Model')

@admin.register(CarPurchase)
class CarPurchaseAdmin(admin.ModelAdmin):
    list_display = ("customer_name", "listing_display", "price", "status_colored", "created_at")
    list_filter = ("status", "created_at", "listing__provider")
    search_fields = ("customer__user__name", "listing__brand", "listing__model")
    readonly_fields = ("price", "created_at")
    ordering = ("-created_at",)

    def customer_name(self, obj):
        return obj.customer.user.name
    customer_name.short_description = _('Customer Name')

    def listing_display(self, obj):
        return f"{obj.listing.brand} {obj.listing.model} ({obj.listing.color})"
    listing_display.short_description = _('Listing')

    def status_colored(self, obj):
        colors = {
            'pending': 'orange',
            'confirmed': 'blue',
            'completed': 'green',
            'cancelled': 'red',
        }
        color = colors.get(obj.status, 'black')
        return format_html('<span style="color: {};"></span> {}', color, obj.get_status_display())
    status_colored.short_description = _('Status')

@admin.register(CarRental)
class CarRentalAdmin(admin.ModelAdmin):
    list_display = ("customer_name", "car_brand", "car_model", "start_datetime", "end_datetime", "total_price", "status", "created_at")
    list_filter = ("car__brand", "car__model", "start_datetime", "end_datetime", "status")
    search_fields = ("customer__user__name", "car__brand", "car__model")
    readonly_fields = ("total_price", "created_at")
    ordering = ("-created_at",)

    def customer_name(self, obj):
        return obj.customer.user.name
    customer_name.short_description = _('Customer Name')
    def car_brand(self, obj):
        return obj.car.brand
    car_brand.short_description = _('Brand')
    def car_model(self, obj):
        return obj.car.model
    car_model.short_description = _('Model')

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
    list_display = ('service_name', 'sub_service', 'zone_name', 'base_fare', 'price_per_km', 'price_per_minute', 'platform_fee', 'is_active', 'created_at')
    list_filter = ('service', 'zone', 'is_active', 'created_at')
    search_fields = ('service__name', 'sub_service', 'zone__name')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        (_('Basic Information'), {
            'fields': ('service', 'sub_service', 'zone', 'is_active')
        }),
        (_('Application Fees'), {
            'fields': ('platform_fee', 'service_fee', 'booking_fee'),
            'description': _('Fixed fees charged by the platform and service providers')
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
    
    def service_name(self, obj):
        return obj.service.name
    service_name.short_description = _('Service')
    
    def zone_name(self, obj):
        return obj.zone.name if obj.zone else _('Default Zone')
    zone_name.short_description = _('Zone')

@admin.register(WhatsAppAPISettings)
class WhatsAppAPISettingsAdmin(admin.ModelAdmin):
    list_display = ['instance_id', 'token']

from import_export import resources, fields
from import_export.admin import ImportExportModelAdmin

# DriverCarResource and Admin
class DriverCarResource(resources.ModelResource):
    driver_name = fields.Field(attribute='driver_profile__provider__user__name', column_name='Driver Name')
    driver_phone = fields.Field(attribute='driver_profile__provider__user__phone', column_name='Driver Phone')
    type = fields.Field(attribute='type', column_name='Car Type')
    model = fields.Field(attribute='model', column_name='Car Model')
    number = fields.Field(attribute='number', column_name='Car Number')
    color = fields.Field(attribute='color', column_name='Car Color')

    class Meta:
        model = DriverCar
        fields = (
            'driver_name',
            'driver_phone',
            'type',
            'model',
            'number',
            'color',
        )
        export_order = fields

class DriverCarImageInline(admin.TabularInline):
    model = DriverCarImage
    extra = 0
    readonly_fields = ['image_preview']
    fields = ['image', 'image_preview']

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="100" height="60" style="object-fit:cover;" />', obj.image.url)
        return "-"
    image_preview.short_description = "Preview"
    
@admin.register(DriverCar)
class DriverCarAdmin(ExportMixin, admin.ModelAdmin):
    resource_class = DriverCarResource
    list_display = ('driver_name', 'driver_phone', 'type', 'model', 'number', 'color')
    search_fields = ('driver_profile__provider__user__name', 'driver_profile__provider__user__phone', 'type', 'model', 'number', 'color')
    actions = ['export_as_pdf']
    inlines = [DriverCarImageInline]

    def driver_name(self, obj):
        return obj.driver_profile.provider.user.name
    driver_name.short_description = _('Driver Name')
    driver_name.admin_order_field = 'driver_profile__provider__user__name'

    def driver_phone(self, obj):
        return obj.driver_profile.provider.user.phone
    driver_phone.short_description = _('Driver Phone')
    driver_phone.admin_order_field = 'driver_profile__provider__user__phone'

    def export_as_pdf(self, request, queryset):
        headers = ['Driver Name', 'Driver Phone', 'Car Type', 'Car Model', 'Car Number', 'Car Color']
        title = "Driver Cars Export"
        rows = []
        for obj in queryset:
            rows.append([
                obj.driver_profile.provider.user.name,
                obj.driver_profile.provider.user.phone,
                obj.type,
                obj.model,
                obj.number,
                obj.color,
            ])
        buffer = export_pdf(title, headers, rows, filename="driver_cars.pdf", is_arabic=False)
        return HttpResponse(buffer, content_type='application/pdf', headers={
            'Content-Disposition': 'attachment; filename=driver_cars.pdf'
        })
    export_as_pdf.short_description = 'Export selected driver cars as PDF'


class DriverDateFilter(admin.SimpleListFilter):
    title = _('Date Joined Range')
    parameter_name = 'date_joined_range'

    # 👇 يتم تعيين المسار الصحيح لحقل التاريخ في الـ Admin class
    date_field_path = 'provider__user__date_joined'

    def lookups(self, request, model_admin):
        return (
            ('today', _('Today')),
            ('yesterday', _('Yesterday')),
            ('this_week', _('This week')),
            ('last_week', _('Last week')),
            ('this_month', _('This month')),
            ('last_month', _('Last month')),
            ('this_year', _('This year')),
        )

    def queryset(self, request, queryset):
        value = self.value()
        if not value:
            return queryset

        now = timezone.localtime()
        field = self.date_field_path
        today_start = datetime.combine(now.date(), datetime.min.time(), tzinfo=now.tzinfo)
        today_end = datetime.combine(now.date(), datetime.max.time(), tzinfo=now.tzinfo)

        filters = {
            'today':   {f"{field}__range": (today_start, today_end)},
            'yesterday': {
                f"{field}__range": (
                    datetime.combine((now - timedelta(days=1)).date(), datetime.min.time(), tzinfo=now.tzinfo),
                    datetime.combine((now - timedelta(days=1)).date(), datetime.max.time(), tzinfo=now.tzinfo),
                )
            },
            'this_week': {
                f"{field}__gte": datetime.combine((now - timedelta(days=now.weekday())).date(), datetime.min.time(), tzinfo=now.tzinfo)
            },
            'last_week': {
                f"{field}__range": (
                    datetime.combine((now - timedelta(days=now.weekday() + 7)).date(), datetime.min.time(), tzinfo=now.tzinfo),
                    datetime.combine((now - timedelta(days=now.weekday() + 1)).date(), datetime.max.time(), tzinfo=now.tzinfo),
                )
            },
            'this_month': {
                f"{field}__gte": datetime(now.year, now.month, 1, tzinfo=now.tzinfo)
            },
            'last_month': {
                f"{field}__gte": datetime(now.year if now.month > 1 else now.year - 1,
                                          now.month - 1 if now.month > 1 else 12, 1, tzinfo=now.tzinfo),
                f"{field}__lt": datetime(now.year, now.month, 1, tzinfo=now.tzinfo)
            },
            'this_year': {
                f"{field}__gte": datetime(now.year, 1, 1, tzinfo=now.tzinfo)
            }
        }

        return queryset.filter(**filters.get(value, {}))
    
# CustomerResource and Admin
class CustomerResource(resources.ModelResource):
    customer_name = fields.Field(attribute='user__name', column_name='Customer Name')
    phone = fields.Field(attribute='user__phone', column_name='Phone Number')
    email = fields.Field(attribute='user__email', column_name='Email')
    in_ride = fields.Field(attribute='in_ride', column_name='In Ride')
    date_joined = fields.Field(attribute='user__date_joined', column_name='Date Joined')

    def dehydrate_in_ride(self, obj):
        return 'Yes' if obj.in_ride else 'No'

    class Meta:
        model = Customer
        fields = (
            'customer_name',
            'phone',
            'email',
            'in_ride',
            'date_joined',
        )
        export_order = fields


from datetime import datetime, timedelta
class CustomDateFilter(admin.SimpleListFilter):
    title = _('Date Joined Range')
    parameter_name = 'date_joined_range'

    def lookups(self, request, model_admin):
        return (
            ('today', _('Today')),
            ('yesterday', _('Yesterday')),
            ('this_week', _('This week')),
            ('last_week', _('Last week')),
            ('this_month', _('This month')),
            ('last_month', _('Last month')),
            ('this_year', _('This year')),
        )

    def queryset(self, request, queryset):
        value = self.value()
        if not value:
            return queryset

        now = timezone.localtime()  # Ensure local timezone (EEST)
        today_start = datetime.combine(now.date(), datetime.min.time(), tzinfo=now.tzinfo)
        today_end = datetime.combine(now.date(), datetime.max.time(), tzinfo=now.tzinfo)

        if value == 'today':
            return queryset.filter(user__date_joined__range=(today_start, today_end))
        elif value == 'yesterday':
            yesterday = now - timedelta(days=1)
            start = datetime.combine(yesterday.date(), datetime.min.time(), tzinfo=now.tzinfo)
            end = datetime.combine(yesterday.date(), datetime.max.time(), tzinfo=now.tzinfo)
            return queryset.filter(user__date_joined__range=(start, end))
        elif value == 'this_week':
            start = now - timedelta(days=now.weekday())
            start = datetime.combine(start.date(), datetime.min.time(), tzinfo=now.tzinfo)
            return queryset.filter(user__date_joined__gte=start)
        elif value == 'last_week':
            start = now - timedelta(days=now.weekday() + 7)
            end = start + timedelta(days=6)
            start = datetime.combine(start.date(), datetime.min.time(), tzinfo=now.tzinfo)
            end = datetime.combine(end.date(), datetime.max.time(), tzinfo=now.tzinfo)
            return queryset.filter(user__date_joined__range=(start, end))
        elif value == 'this_month':
            start = datetime(now.year, now.month, 1, tzinfo=now.tzinfo)
            return queryset.filter(user__date_joined__gte=start)
        elif value == 'last_month':
            if now.month == 1:
                year = now.year - 1
                month = 12
            else:
                year = now.year
                month = now.month - 1
            start = datetime(year, month, 1, tzinfo=now.tzinfo)
            if month == 12:
                end = datetime(year + 1, 1, 1, tzinfo=now.tzinfo)
            else:
                end = datetime(year, month + 1, 1, tzinfo=now.tzinfo)
            return queryset.filter(user__date_joined__gte=start, user__date_joined__lt=end)
        elif value == 'this_year':
            start = datetime(now.year, 1, 1, tzinfo=now.tzinfo)
            return queryset.filter(user__date_joined__gte=start)
        return queryset

    def choices(self, changelist):
        for lookup, title in self.lookups(None, None):
            yield {
                'selected': self.value() == lookup,
                'query_string': changelist.get_query_string({
                    self.parameter_name: lookup,
                }, ['date_joined_start', 'date_joined_end']),
                'display': title,
            }

    def expected_parameters(self):
        return [self.parameter_name, 'date_joined_start', 'date_joined_end']

@admin.register(Customer)
class CustomerAdmin(ExportMixin, admin.ModelAdmin):
    resource_class = CustomerResource
    list_display = ('customer_name', 'phone', 'email', 'in_ride', 'user_is_active', 'date_joined')
    list_filter = (
        'in_ride',
        ('user__is_active', admin.BooleanFieldListFilter),
        'user__role',
        ('user__date_joined', DateFieldListFilter),
        CustomDateFilter,
    )
    search_fields = ('user__name', 'user__phone', 'user__email')
    ordering = ('-user__date_joined',)
    readonly_fields = ('user',)
    actions = ['export_as_pdf', 'mark_in_ride', 'mark_not_in_ride', 'view_map_all_users_and_drivers']

    def customer_name(self, obj):
        return obj.user.name
    customer_name.short_description = 'Customer Name'
    customer_name.admin_order_field = 'user__name'

    def user_is_active(self, obj):
        return format_html(
            '<span style="color: green;">✓</span> Active' if obj.user.is_active else '<span style="color: red;">✗</span> Inactive'
        )
    user_is_active.short_description = 'Status'
    user_is_active.admin_order_field = 'user__is_active'

    def phone(self, obj):
        return obj.user.phone
    phone.short_description = 'Phone Number'
    phone.admin_order_field = 'user__phone'

    def email(self, obj):
        return obj.user.email
    email.short_description = 'Email'
    email.admin_order_field = 'user__email'

    def date_joined(self, obj):
        local_dt = timezone.localtime(obj.user.date_joined)
        return local_dt.strftime('%Y-%m-%d %H:%M')
    date_joined.short_description = 'Date Joined'
    date_joined.admin_order_field = 'user__date_joined'

    def export_as_pdf(self, request, queryset):
        from .utils import export_pdf  # Ensure this is your custom utility
        headers = ['Customer Name', 'Phone Number', 'Email', 'In Ride', 'Date Joined']
        title = "Customers Export"
        rows = []
        for obj in queryset:
            local_dt = timezone.localtime(obj.user.date_joined)
            rows.append([
                obj.user.name,
                obj.user.phone,
                obj.user.email,
                'Yes' if obj.in_ride else 'No',
                local_dt.strftime('%Y-%m-%d %H:%M'),
            ])
        buffer = export_pdf(title, headers, rows, filename="customers.pdf", is_arabic=False)
        return HttpResponse(buffer, content_type='application/pdf', headers={
            'Content-Disposition': 'attachment; filename=customers.pdf'
        })
    export_as_pdf.short_description = 'Export selected customers as PDF'

    def mark_in_ride(self, request, queryset):
        updated = queryset.update(in_ride=True)
        self.message_user(request, f'{updated} customers marked as in ride.')
    mark_in_ride.short_description = "Mark selected customers as in ride"

    def mark_not_in_ride(self, request, queryset):
        updated = queryset.update(in_ride=False)
        self.message_user(request, f'{updated} customers marked as not in ride.')
    mark_not_in_ride.short_description = "Mark selected customers as not in ride"

    def view_map_all_users_and_drivers(self, request, queryset=None):
        return HttpResponseRedirect(reverse('admin:customer-map-view'))

    view_map_all_users_and_drivers.short_description = "🗺 View Customers And Drivers Map"

    def full_map_view(self, request):
        drivers = DriverProfile.objects.select_related('provider__user').filter(
            provider__user__location2_lat__isnull=False,
            provider__user__location2_lng__isnull=False
        )
        customers = Customer.objects.select_related('user').filter(
            user__location2_lat__isnull=False,
            user__location2_lng__isnull=False
        )

        driver_data = [
            {
                'name': escape(d.provider.user.name),
                'lat': float(d.provider.user.location2_lat),
                'lng': float(d.provider.user.location2_lng),
                'status': d.status,
            }
            for d in drivers
        ]

        customer_data = [
            {
                'name': escape(c.user.name),
                'lat': float(c.user.location2_lat),
                'lng': float(c.user.location2_lng),
            }
            for c in customers
        ]

        html = f"""
        <html lang="ar">
        <head>
            <title>Customers and Drivers Map</title>
            <meta charset="utf-8" />
            <meta name="viewport" content="initial-scale=1.0, width=device-width" />
            <style>
                body {{
                    margin: 0;
                    font-family: sans-serif;
                }}
                #map {{
                    height: 85vh;
                    width: 100%;
                }}
                .summary {{
                    padding: 10px;
                    text-align: center;
                    font-size: 18px;
                    background-color: #f1f1f1;
                    direction: rtl;
                }}
            </style>
            <script src="https://maps.googleapis.com/maps/api/js?key=AIzaSyDXSvQvWo_ay-Tgq7qIlXIgdn-vNNxOAFA"></script>
            <script>
                const drivers = {json.dumps(driver_data)};
                const customers = {json.dumps(customer_data)};

                function initMap() {{
                    const map = new google.maps.Map(document.getElementById("map"), {{
                        zoom: 6,
                        center: {{ lat: 30.0444, lng: 31.2357 }}
                    }});

                    const bounds = new google.maps.LatLngBounds();

                    drivers.forEach(d => {{
                        const pos = {{ lat: d.lat, lng: d.lng }};
                        new google.maps.Marker({{
                            position: pos,
                            map,
                            title: `${{d.name}} - ${{d.status}}`,
                            icon: d.status === 'available'
                                ? 'http://maps.google.com/mapfiles/ms/icons/green-dot.png'
                                : 'http://maps.google.com/mapfiles/ms/icons/red-dot.png'
                        }});
                        bounds.extend(pos);
                    }});

                    customers.forEach(c => {{
                        const pos = {{ lat: c.lat, lng: c.lng }};
                        new google.maps.Marker({{
                            position: pos,
                            map,
                            title: `${{c.name}}`,
                            icon: 'http://maps.google.com/mapfiles/ms/icons/blue-dot.png'
                        }});
                        bounds.extend(pos);
                    }});

                    if (!bounds.isEmpty()) {{
                        map.fitBounds(bounds);
                    }}
                }}

                window.onload = initMap;
            </script>
        </head>
        <body>
            <div class="summary">
                🚗 Drivers Number: {len(driver_data)} |
                🟢 Avaliable: {len([d for d in driver_data if d['status'] == 'available'])} |
                👤 Customers Number: {len(customer_data)}
            </div>
            <div id="map"></div>
        </body>
        </html>
        """

        return HttpResponse(html)
        

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('full-map/', self.admin_site.admin_view(self.full_map_view), name='customer-map-view'),
        ]
        return custom_urls + urls

    def _normalize_datetime_filters(self, request):
        get = request.GET.copy()
        local_tz = pytz.timezone(settings.TIME_ZONE)
        for param in ['user__date_joined__gte', 'user__date_joined__lte']:
            if param in get:
                try:
                    dt_str = urllib.parse.unquote(get[param])
                    if '+' in dt_str:
                        parts = dt_str.split('+', 1)
                        dt_str = parts[0].replace(' ', 'T') + '+' + parts[1]
                    else:
                        dt_str = dt_str.replace(' ', 'T')
                    dt = datetime.fromisoformat(dt_str)
                    dt_components = datetime(
                        dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second, dt.microsecond
                    )
                    dt_converted = local_tz.localize(dt_components)
                    get[param] = dt_converted.isoformat()
                except ValueError:
                    continue
        request.GET = get

    def changelist_view(self, request, extra_context=None):
        self._normalize_datetime_filters(request)
        return super().changelist_view(request, extra_context)


@admin.register(PlatformSettings)
class DashboardSettingsAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        # Prevent adding more than one instance
        return not PlatformSettings.objects.exists()


class ProviderResource(resources.ModelResource):
    provider_name = fields.Field(attribute='user__name', column_name='Provider Name')
    phone = fields.Field(attribute='user__phone', column_name='Phone Number')
    email = fields.Field(attribute='user__email', column_name='Email')
    is_verified = fields.Field(attribute='is_verified', column_name='Verified')
    in_ride = fields.Field(attribute='in_ride', column_name='In Ride')
    sub_service = fields.Field(attribute='sub_service', column_name='Sub Service')
    services = fields.Field(column_name='Services')
    date_joined = fields.Field(attribute='user__date_joined', column_name='Date Joined')

    def dehydrate_services(self, obj):
        return ', '.join([s.name for s in obj.services.all()])

    def dehydrate_is_verified(self, obj):
        return 'Yes' if obj.is_verified else 'No'

    def dehydrate_in_ride(self, obj):
        return 'Yes' if obj.in_ride else 'No'

    class Meta:
        model = Provider
        fields = (
            'provider_name',
            'phone',
            'email',
            'is_verified',
            'in_ride',
            'sub_service',
            'services',
            'date_joined',
        )
        export_order = fields

@admin.register(Provider)
class ProviderAdmin(ExportMixin, admin.ModelAdmin):
    resource_class = ProviderResource
    list_display = ['provider_name', 'provider_phone', 'is_verified', 'in_ride', 'sub_service', 'services_list', 'date_joined']
    list_filter = ['is_verified', 'in_ride', 'sub_service', ('user__date_joined', admin.DateFieldListFilter),
        CustomDateFilter,  # ✅ added here
    ]
    search_fields = ['user__name', 'user__phone', 'sub_service', 'services__name']
    filter_horizontal = ['services']
    ordering = ['-user__date_joined']
    actions = ['export_as_pdf']

    def provider_name(self, obj):
        return obj.user.name
    provider_name.short_description = _('Provider Name')
    provider_name.admin_order_field = 'user__name'

    def provider_phone(self, obj):
        return obj.user.phone
    provider_phone.short_description = _('Phone Number')
    provider_phone.admin_order_field = 'user__phone'

    def services_list(self, obj):
        return ", ".join([s.name for s in obj.services.all()])
    services_list.short_description = _('Services')

    def date_joined(self, obj):
        return obj.user.date_joined.strftime('%Y-%m-%d %H:%M')
    date_joined.short_description = _('Date Joined')
    date_joined.admin_order_field = 'user__date_joined'

    def export_as_pdf(self, request, queryset):
        headers = [
            "Provider Name", "Phone Number", "Email", "Verified", "In Ride",
            "Sub Service", "Services", "Date Joined"
        ]
        title = "Providers Export"
        rows = []
        for obj in queryset:
            rows.append([
                obj.user.name,
                obj.user.phone,
                obj.user.email,
                'Yes' if obj.is_verified else 'No',
                'Yes' if obj.in_ride else 'No',
                obj.sub_service or '',
                ', '.join([s.name for s in obj.services.all()]),
                obj.user.date_joined.strftime('%Y-%m-%d %H:%M'),
            ])
        buffer = export_pdf(title, headers, rows, filename="providers.pdf", is_arabic=False)
        return HttpResponse(buffer, content_type='application/pdf', headers={
            'Content-Disposition': 'attachment; filename=providers.pdf'
        })
    export_as_pdf.short_description = _('Export selected providers as PDF')
    
    def _normalize_datetime_filters(self, request):
        """Force datetime filters to use local timezone (EEST) without altering date/time."""
        get = request.GET.copy()
        local_tz = pytz.timezone(settings.TIME_ZONE)  # E.g., 'Europe/Helsinki' for EEST

        for param in ['user__date_joined__gte', 'user__date_joined__lte']:
            if param in get:
                try:
                    # Decode URL-encoded parameter
                    dt_str = urllib.parse.unquote(get[param])
                    # Replace first '+' with 'T' for ISO format, preserving timezone offset
                    if '+' in dt_str:
                        parts = dt_str.split('+', 1)
                        dt_str = parts[0].replace(' ', 'T') + '+' + parts[1]
                    else:
                        dt_str = dt_str.replace(' ', 'T')
                    # Parse the datetime string
                    dt = datetime.fromisoformat(dt_str)
                    # Extract date and time components
                    dt_components = datetime(
                        dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second, dt.microsecond
                    )
                    # Apply local timezone (EEST, +03:00) without changing date/time
                    dt_converted = local_tz.localize(dt_components)
                    # Format back to ISO string for URL
                    get[param] = dt_converted.isoformat()
                    print(f"{param}: {dt_str} → {dt_converted.isoformat()}")
                except ValueError as e:
                    print(f"Failed to parse {param}: {e}")
                    continue  # Skip invalid datetime values
        request.GET = get
        
    def changelist_view(self, request, extra_context=None):
        self._normalize_datetime_filters(request)
        return super().changelist_view(request, extra_context)


class DriverProfileResource(resources.ModelResource):
    driver_name = fields.Field(attribute='provider__user__name', column_name='Driver Name')
    phone = fields.Field(attribute='provider__user__phone', column_name='Phone Number')
    license = fields.Field(attribute='license', column_name='License Number')
    status = fields.Field(attribute='status', column_name='Status')
    email = fields.Field(attribute='provider__user__email', column_name='Email')
    date_joined = fields.Field(attribute='provider__user__date_joined', column_name='Date Joined')
    verified = fields.Field(column_name='Verified')

    def dehydrate_verified(self, obj):
        return 'Yes' if obj.provider.is_verified else 'No'

    class Meta:
        model = DriverProfile
        fields = (
            'driver_name',
            'phone',
            'license',
            'status',
            'verified',
            'email',
            'date_joined',
        )
        export_order = fields

@admin.register(DriverProfile)
class DriverProfileAdmin(ExportMixin, admin.ModelAdmin):
    resource_class = DriverProfileResource
    list_display = ('user_name', 'user_phone', 'license', 'status', 'provider_verified', 'documents_link')
    list_filter = ('status', 'provider__is_verified', ('provider__user__date_joined', admin.DateFieldListFilter),
        DriverDateFilter,
    )
    search_fields = ('provider__user__name', 'provider__user__phone', 'license')
    ordering = ('-provider__user__date_joined',)
    actions = ['export_as_pdf', 'view_drivers_on_map']
    readonly_fields = ('is_verified',)
    def user_name(self, obj):
        return obj.provider.user.name
    user_name.short_description = _('Driver Name')
    user_name.admin_order_field = 'provider__user__name'

    def user_phone(self, obj):
        return obj.provider.user.phone
    user_phone.short_description = _('Phone Number')
    user_phone.admin_order_field = 'provider__user__phone'

    def provider_verified(self, obj):
        return 'Yes' if obj.provider.is_verified else 'No'
    provider_verified.short_description = _('Verified')
    provider_verified.admin_order_field = 'provider__is_verified'

    def documents_link(self, obj):
        if obj.documents:
            return format_html('<a href="{}" target="_blank">Download</a>', obj.documents.url)
        return '-'
    documents_link.short_description = _('Documents')

    def export_as_pdf(self, request, queryset):
        headers = ['Driver Name', 'Phone Number', 'License Number', 'Status', 'Verified', 'Email', 'Date Joined']
        title = "Driver Profiles Export"
        rows = []
        for obj in queryset:
            rows.append([
                obj.provider.user.name,
                obj.provider.user.phone,
                obj.license,
                obj.status,
                'Yes' if obj.provider.is_verified else 'No',
                obj.provider.user.email,
                obj.provider.user.date_joined.strftime('%Y-%m-%d %H:%M'),
            ])
        buffer = export_pdf(title, headers, rows, filename="driver_profiles.pdf", is_arabic=False)
        return HttpResponse(buffer, content_type='application/pdf', headers={
            'Content-Disposition': 'attachment; filename=driver_profiles.pdf'
        })
    export_as_pdf.short_description = 'Export selected drivers as PDF'
    
    # Add custom URL for map view
    def view_drivers_on_map(self, request, queryset):
        # If any driver is selected, filter by selected IDs
        if queryset.exists():
            ids = queryset.values_list('id', flat=True)
            query_string = '&'.join([f'id={i}' for i in ids])
            map_url = f"{reverse('admin:driverprofile-map')}?{query_string}"
        else:
            # No selection: show all drivers
            map_url = reverse('admin:driverprofile-map')
        return HttpResponseRedirect(map_url)

    view_drivers_on_map.short_description = _('View Drivers on Map')

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('map/', self.admin_site.admin_view(self.map_view), name='driverprofile-map'),
        ]
        return custom_urls + urls

    def map_view(self, request):
        ids = request.GET.getlist('id')
        # Start with all drivers, optimized with select_related
        queryset = DriverProfile.objects.select_related('provider__user')

        # Apply ID filter only if IDs are provided
        if ids:
            queryset = queryset.filter(id__in=ids)

        # Filter for drivers with valid location coordinates
        queryset = queryset.filter(
            provider__user__location2_lat__isnull=False,
            provider__user__location2_lng__isnull=False
        )

        driver_data = []
        for driver in queryset:
            total_rides = RideStatus.objects.filter(provider=driver.provider.user).count()
            completed_rides = RideStatus.objects.filter(
                provider=driver.provider.user, status='finished'
            ).count()
            activity_percentage = (completed_rides / total_rides * 100) if total_rides > 0 else 0
            driver_data.append({
                'name': driver.provider.user.name,
                'lat': driver.provider.user.location2_lat,
                'lng': driver.provider.user.location2_lng,
                'status': driver.status,
                'activity_percentage': round(activity_percentage, 2),
            })

        context = {
            'driver_data': json.dumps(driver_data),
            'google_maps_api_key': 'AIzaSyDXSvQvWo_ay-Tgq7qIlXIgdn-vNNxOAFA',
        }
        return TemplateResponse(request, 'admin/driverprofile_map.html', context)
    
    def _normalize_datetime_filters(self, request):
        """Force datetime filters to use local timezone (EEST) without altering date/time."""
        get = request.GET.copy()
        local_tz = pytz.timezone(settings.TIME_ZONE)  # E.g., 'Europe/Cairo' or 'Asia/Riyadh'

        # ✅ استخدم المسار الصحيح لعلاقة DriverProfile → Provider → User → date_joined
        for param in ['provider__user__date_joined__gte', 'provider__user__date_joined__lte']:
            if param in get:
                try:
                    # فك تشفير قيمة التاريخ
                    dt_str = urllib.parse.unquote(get[param])

                    # استبدال المسافة بـ T لصيغة ISO، مع الحفاظ على + إن وُجد
                    if '+' in dt_str:
                        parts = dt_str.split('+', 1)
                        dt_str = parts[0].replace(' ', 'T') + '+' + parts[1]
                    else:
                        dt_str = dt_str.replace(' ', 'T')

                    # تحويل السلسلة إلى datetime
                    dt = datetime.fromisoformat(dt_str)

                    # إنشاء datetime بدون تغيير الزمن
                    dt_components = datetime(
                        dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second, dt.microsecond
                    )

                    # تطبيق timezone المحلي بدون تعديل الوقت
                    dt_converted = local_tz.localize(dt_components)

                    # إعادة التنسيق لسلسلة ISO
                    get[param] = dt_converted.isoformat()

                    print(f"{param}: {dt_str} → {dt_converted.isoformat()}")
                except ValueError as e:
                    print(f"Failed to parse {param}: {e}")
                    continue  # تجاهل الأخطاء
        request.GET = get

        
    def changelist_view(self, request, extra_context=None):
        self._normalize_datetime_filters(request)
        return super().changelist_view(request, extra_context)

    
@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ('code', 'discount_percentage', 'active', 'valid_from', 'valid_to')
    list_filter = ('active', 'valid_from', 'valid_to')
    search_fields = ('code',)
    ordering = ('-valid_from',)
    fieldsets = (
        (_('Coupon Information'), {
            'fields': ('code', 'discount_percentage', 'active', 'valid_from', 'valid_to')
        }),
    )


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'notification_type', 'is_read', 'created_at')
    list_filter = ('notification_type', 'is_read', 'created_at')
    search_fields = ('title', 'message', 'user__name')
    readonly_fields = ('created_at',)

    def has_add_permission(self, request):
        return False  # ✅ إذا كنت لا تريد إضافة إشعارات يدوياً من لوحة التحكم


def print_invoice_view(request, invoice_id):
    try:
        invoice = Invoice.objects.select_related('ride__client', 'ride__provider').get(id=invoice_id)
    except Invoice.DoesNotExist:
        return HttpResponse("Invoice not found", status=404)

    client_name = escape(invoice.ride.client.name)
    provider_name = escape(invoice.ride.provider.name) if invoice.ride.provider else "N/A"
    ride_id = invoice.ride.id

    html = f"""
    <html>
    <head>
        <title>Invoice #{invoice.id}</title>
        <meta charset="utf-8">
        <style>
            body {{
                font-family: Arial, sans-serif;
                padding: 40px;
                background: #f9f9f9;
            }}
            .invoice-box {{
                max-width: 800px;
                margin: auto;
                padding: 30px;
                border: 1px solid #eee;
                background: #fff;
                box-shadow: 0 0 10px rgba(0, 0, 0, 0.15);
            }}
            .invoice-box h2 {{
                text-align: center;
            }}
            table {{
                width: 100%;
                line-height: inherit;
                text-align: left;
            }}
            table td {{
                padding: 5px;
                vertical-align: top;
            }}
            .details td {{
                padding-bottom: 10px;
            }}
            .total {{
                font-weight: bold;
            }}
        </style>
    </head>
    <body>
        <div class="invoice-box">
            <h2>🧾 Invoice #{invoice.id}</h2>
            <table>
                <tr class="details">
                    <td><strong>Client:</strong> {client_name}</td>
                    <td><strong>Provider:</strong> {provider_name}</td>
                </tr>
                <tr class="details">
                    <td><strong>Ride ID:</strong> #{ride_id}</td>
                    <td><strong>Date:</strong> {invoice.issued_at.strftime('%Y-%m-%d %H:%M')}</td>
                </tr>
            </table>
            <hr/>
            <table>
                <tr>
                    <td>Total:</td>
                    <td>{invoice.total_amount:.2f} EGP</td>
                </tr>
                <tr>
                    <td>Tax (10%):</td>
                    <td>{invoice.tax:.2f} EGP</td>
                </tr>
                <tr>
                    <td>Discount:</td>
                    <td>{invoice.discount:.2f} EGP</td>
                </tr>
                <tr class="total">
                    <td>Final Amount:</td>
                    <td>{invoice.final_amount:.2f} EGP</td>
                </tr>
                <tr>
                    <td>Status:</td>
                    <td>{invoice.get_status_display()}</td>
                </tr>
            </table>
            <br/>
            <p>{invoice.notes or ''}</p>
        </div>
    </body>
    </html>
    """
    return HttpResponse(html)

# === Restaurant: Categories, Products, Images ===

@admin.register(CouponRestaurant)
class CouponRestaurantAdmin(admin.ModelAdmin):
    list_display = ['code', 'discount_percentage', 'is_active', 'created_at', 'updated_at']
    search_fields = ['code']
    list_filter = ['is_active', 'created_at', 'updated_at']
    ordering = ['-created_at']

@admin.register(ProductCategory)
class ProductCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'restaurant']
    search_fields = ['name', 'restaurant__restaurant_name']
    list_filter = ['restaurant']

@admin.register(ProductRestaurant)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'display_price', 'stock', 'is_offer', 'is_active', 'created_at']
    search_fields = ['name', 'category__name', 'category__restaurant__restaurant_name']
    list_filter = ['is_active', 'is_offer', 'category', 'created_at']
    list_editable = ['is_active']
    ordering = ['-created_at']

@admin.register(ProductImageRestaurant)
class ProductImageAdmin(admin.ModelAdmin):
    # Match fields defined on authentication.models.ProductImage
    list_display = ['product', 'image']
    list_filter = ['product__category']
    search_fields = ['product__name', 'product__category__restaurant__restaurant_name']
    # No created_at on ProductImage model

# === Cart, Orders ===
@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ['id', 'customer', 'created_at']
    search_fields = ['customer__name', 'customer__phone']
    ordering = ['-created_at']

@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ['cart', 'product', 'quantity']
    search_fields = ['cart__customer__name', 'product__name']

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'customer', 'restaurant', 'driver', 'total_price', 'final_price', 'status', 'payment_method', 'created_at']
    list_filter = ['status', 'payment_method', 'restaurant']
    search_fields = ['customer__name', 'restaurant__restaurant_name', 'driver__user__name']
    ordering = ['-created_at']

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ['order', 'product', 'quantity', 'price']
    search_fields = ['order__customer__name', 'product__name']



@admin.register(ReviewRestaurant)
class ReviewRestaurantAdmin(admin.ModelAdmin):
    list_display = ['customer', 'restaurant', 'rating', 'created_at']
    list_filter = ['rating', 'restaurant']
    search_fields = ['customer__name', 'restaurant__restaurant_name']
    ordering = ['-created_at']

@admin.register(OfferRestaurant)
class OfferRestaurantAdmin(admin.ModelAdmin):
    list_display = ['restaurant', 'title', 'discount_percentage', 'active', 'valid_from', 'valid_to']
    list_filter = ['active', 'restaurant']
    search_fields = ['title', 'restaurant__restaurant_name']

# === Addresses ===
@admin.register(DeliveryAddress)
class DeliveryAddressAdmin(admin.ModelAdmin):
    list_display = ['customer', 'address', 'latitude', 'longitude', 'is_default']
    list_filter = ['is_default']
    search_fields = ['customer__name', 'address']

# Reports are API views; no direct Model to register in admin.

