from authentication.choices import ROLE_CHOICES
from authentication.managers import UserManager
from django.contrib.auth.models import AbstractUser
from django.db import models
from location_field.models.plain import PlainLocationField
#from django.contrib.gis.db import models as gis_models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.contrib.postgres.fields import JSONField
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from datetime import timedelta


class WhatsAppAPISettings(models.Model):
    instance_id = models.CharField(_('Instance ID'), max_length=100)
    token = models.CharField(_('Token'), max_length=255)

    def __str__(self):
        return f"WhatsApp API Settings"
    
    class Meta:
        verbose_name = _("WhatsApp API Settings")
        verbose_name_plural = _("WhatsApp API Settings")
        
        
class PricingZone(models.Model):
    """
    Defines geographical zones for pricing
    """
    name = models.CharField(_("Zone Name"), max_length=100)
    description = models.TextField(_("Description"), blank=True)
    # Define zone boundaries using coordinates
    # Format: [{"lat": 30.0444, "lng": 31.2357}, {"lat": 30.0500, "lng": 31.2400}, ...]
    boundaries = models.JSONField(_("Zone Boundaries"), help_text=_("Array of coordinate points defining the zone"))
    is_active = models.BooleanField(_("Is Active"), default=True)
    created_at = models.DateTimeField(_("Created At"), auto_now_add=True)
    
    class Meta:
        verbose_name = _("Pricing Zone")
        verbose_name_plural = _("Pricing Zones")
    
    def __str__(self):
        return self.name
    
    def contains_point(self, lat, lng):
        """
        Check if a point (lat, lng) is within this zone using ray casting algorithm
        """
        if not self.boundaries or len(self.boundaries) < 3:
            return False
        
        x, y = lng, lat
        n = len(self.boundaries)
        inside = False
        
        p1x, p1y = self.boundaries[0]['lng'], self.boundaries[0]['lat']
        for i in range(1, n + 1):
            p2x, p2y = self.boundaries[i % n]['lng'], self.boundaries[i % n]['lat']
            if y > min(p1y, p2y):
                if y <= max(p1y, p2y):
                    if x <= max(p1x, p2x):
                        if p1y != p2y:
                            xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                        if p1x == p2x or x <= xinters:
                            inside = not inside
            p1x, p1y = p2x, p2y
        
        return inside
class User(AbstractUser):
    name = models.CharField(_("Name"), max_length=30)
    phone = models.CharField(_("Phone"),max_length=20, unique=True)
    image = models.ImageField(_("Image"),upload_to="user/images/", null=True, blank=True)
    role = models.CharField(_("Role"), max_length=2, choices=ROLE_CHOICES)
    location = PlainLocationField(based_fields=["cairo"], verbose_name=_("Location"), null= True, blank=True)
    location2_lat = models.FloatField(null=True, blank=True, verbose_name=_("Location2 Latitude"))
    location2_lng = models.FloatField(null=True, blank=True, verbose_name=_("Location2 Longitude"))
    average_rating = models.DecimalField(
        _("Average Rating"),
        max_digits=3,
        decimal_places=2,
        null=True,
        blank=True,
    )

    fcm_registration_id = models.CharField(
        max_length=255, null=True, blank=True, verbose_name=_("FCM Registration ID")
    )

    device_type = models.CharField(max_length=10, choices=[("android", "Android"), ("ios", "iOS")], null=True, blank=True)


    # inherited attributes
    username = None
    first_name = None
    last_name = None
    # groups = None  # REMOVED - Using property instead to fix Django admin compatibility
    user_permissions = None
    REQUIRED_FIELDS = []
    is_active = models.BooleanField(_("Is Active"), default=False)

    objects = UserManager()
    USERNAME_FIELD = "phone"

    def __str__(self):
        return f"{self.name} -> {self.phone}"
    
    @property
    def groups(self):
        """Return a manager-like object for groups to fix Django admin compatibility"""
        from django.db import connection
        from django.contrib.auth.models import Group
        
        class GroupsProxy:
            def __init__(self, user):
                self.user = user
                self._cache = None
            
            def _get_groups(self):
                if self._cache is None:
                    try:
                        if not hasattr(self.user, 'id') or self.user.id is None:
                            self._cache = Group.objects.none()
                        else:
                            with connection.cursor() as cursor:
                                cursor.execute(
                                    """
                                    SELECT g.id FROM auth_group g
                                    INNER JOIN auth_user_groups ug ON g.id = ug.group_id
                                    WHERE ug.user_id = %s
                                    """,
                                    [self.user.id]
                                )
                                group_ids = [row[0] for row in cursor.fetchall()]
                            if group_ids:
                                self._cache = Group.objects.filter(id__in=group_ids)
                            else:
                                self._cache = Group.objects.none()
                    except Exception as e:
                        # Log error in production but return empty queryset
                        import logging
                        logger = logging.getLogger(__name__)
                        logger.error(f"Error getting groups for user {getattr(self.user, 'id', 'unknown')}: {e}")
                        self._cache = Group.objects.none()
                return self._cache if self._cache is not None else Group.objects.none()
            
            def all(self):
                """Return all groups for this user"""
                result = self._get_groups()
                # Return empty queryset if None to prevent AttributeError
                if result is None:
                    from django.contrib.auth.models import Group
                    return Group.objects.none()
                return result
            
            def filter(self, **kwargs):
                return self._get_groups().filter(**kwargs)
            
            def values_list(self, *fields, **kwargs):
                return self._get_groups().values_list(*fields, **kwargs)
            
            def exists(self):
                return self._get_groups().exists()
            
            def count(self):
                return self._get_groups().count()
            
            def add(self, *groups):
                """Add user to groups"""
                from django.db import connection
                try:
                    with connection.cursor() as cursor:
                        for group in groups:
                            group_id = group.id if hasattr(group, 'id') else group
                            cursor.execute(
                                "SELECT COUNT(*) FROM auth_user_groups WHERE user_id = %s AND group_id = %s",
                                [self.user.id, group_id]
                            )
                            if cursor.fetchone()[0] == 0:
                                cursor.execute(
                                    "INSERT INTO auth_user_groups (user_id, group_id) VALUES (%s, %s)",
                                    [self.user.id, group_id]
                                )
                        connection.commit()
                    self._cache = None  # Clear cache
                except Exception as e:
                    raise
            
            def remove(self, *groups):
                """Remove user from groups"""
                from django.db import connection
                try:
                    with connection.cursor() as cursor:
                        for group in groups:
                            group_id = group.id if hasattr(group, 'id') else group
                            cursor.execute(
                                "DELETE FROM auth_user_groups WHERE user_id = %s AND group_id = %s",
                                [self.user.id, group_id]
                            )
                        connection.commit()
                    self._cache = None  # Clear cache
                except Exception as e:
                    raise
        
        return GroupsProxy(self)
    
    class Meta:
        verbose_name = _("User")
        verbose_name_plural = _("Users")


class UserOtp(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, verbose_name=_("User"))
    otp = models.CharField(_("OTP"), max_length=20)

    def __str__(self):
        return self.user.name
    
    class Meta:
        verbose_name = _("User OTP")
        verbose_name_plural = _("User OTPs")


class Service(models.Model):
    name = models.CharField(_("Name"), max_length=20, unique=True)
    created_at = models.DateTimeField(_("Created At"), auto_now_add=True, null=True, blank=True)

    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = _("Service")
        verbose_name_plural = _("Services")

class SubService(models.Model):
    name = models.CharField(_("Name"), max_length=20, unique=True)
    created_at = models.DateTimeField(_("Created At"), auto_now_add=True, null=True, blank=True)

    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = _("Sub Service")
        verbose_name_plural = _("Sub Services")

class NameOfCar(models.Model):
    name = models.CharField(_("Name"), max_length=20, unique=True)
    created_at = models.DateTimeField(_("Created At"), auto_now_add=True, null=True, blank=True)

    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = _("Name Of Car")
        verbose_name_plural = _("Names Of Cars")


class ServiceImage(models.Model):
    service = models.ForeignKey(
        Service,
        on_delete=models.CASCADE,
        related_name="images",
        verbose_name=_("Service"),
    )
    image = models.ImageField(_("Image"), upload_to="service/images/")

    def __str__(self):
        return self.service.name
    
    class Meta:
        verbose_name = _("Service Image")
        verbose_name_plural = _("Service Images")


class RestaurantModel(models.Model):
    provider = models.ForeignKey('Provider', on_delete=models.CASCADE, verbose_name=_("Provider"), related_name='restaurants', blank=True, null=True)
    restaurant_name = models.CharField(_("Restaurant Name"), max_length=200)
    restaurant_id_image = models.ImageField(_("Restaurant Logo"), upload_to="restaurant/logo/")
    restaurant_license = models.FileField(_("Restaurant License"), upload_to="restaurant/license/")
    restaurant_description = models.TextField(_("Restaurant Description"), blank=True, null=True)
    
    # Contact & Location
    phone = models.CharField(_("Phone"), max_length=20, blank=True, null=True)
    email = models.EmailField(_("Email"), blank=True, null=True)
    address = models.CharField(_("Address"), max_length=255, blank=True, null=True)
    latitude = models.FloatField(_("Latitude"), blank=True, null=True)
    longitude = models.FloatField(_("Longitude"), blank=True, null=True)
    
    # Restaurant Details
    is_verified = models.BooleanField(_("Is Verified"), default=False)
    
    average_rating = models.DecimalField(
        _("Average Rating"),
        max_digits=3,
        decimal_places=2,
        default=0.0
    )
    menu_link = models.URLField(_("Menu Link"), blank=True, null=True)
    
    created_at = models.DateTimeField(_("Created At"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated At"), auto_now=True)

    def __str__(self):
        return self.restaurant_name
    
    class Meta:
        verbose_name = _("Restaurant")
        verbose_name_plural = _("Restaurants")

class WorkingDay(models.Model):
    DAYS_OF_WEEK = [
        (2, _("Monday")),
        (3, _("Tuesday")),
        (4, _("Wednesday")),
        (5, _("Thursday")),
        (6, _("Friday")),
        (0, _("Saturday")),
        (1, _("Sunday")),
    ]
    
    restaurant = models.ForeignKey(RestaurantModel, on_delete=models.CASCADE, related_name="working_days")
    day_of_week = models.IntegerField(_("Day of Week"), choices=DAYS_OF_WEEK)
    opening_time = models.TimeField(_("Opening Time"))
    closing_time = models.TimeField(_("Closing Time"))

    class Meta:
        verbose_name = _("Working Day")
        verbose_name_plural = _("Working Days")
        unique_together = ("restaurant", "day_of_week")  # Prevent duplicate days for the same restaurant
        ordering = ["day_of_week"]

    def __str__(self):
        return f"{self.get_day_of_week_display()} - {self.restaurant.restaurant_name}"

class ProductCategory(models.Model):
    """
    A logical menu/category per restaurant.
    Example: 'Starters', 'Main Dishes', 'Drinks', etc.
    """
    restaurant = models.ForeignKey(
        'RestaurantModel',
        on_delete=models.CASCADE,
        related_name='categories',
        verbose_name=_("Restaurant")
    )
    name = models.CharField(_("Category Name"), max_length=100)

    class Meta:
        verbose_name = _("Product Category")
        verbose_name_plural = _("Product Categories")
        unique_together = ("restaurant", "name")
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.restaurant.restaurant_name})"




    
class ProductRestaurant(models.Model):
    category = models.ForeignKey(ProductCategory, on_delete=models.CASCADE, related_name="products_restaurant", verbose_name=_("Category"))
    name = models.CharField(_("Name"), max_length=100)
    description = models.TextField(_("Description"))
    display_price = models.PositiveIntegerField(_("Display Price"), default=0)
    stock = models.PositiveIntegerField(_("Stock"), default=0)
    is_offer = models.BooleanField(_("Is Offer"), default=False)
    is_active = models.BooleanField(_("Is Active"), default=True)
    # Primary image stored directly on the product (additional images can still use related model)
    created_at = models.DateTimeField(_("Created At"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated At"), auto_now=True)
    # Use JSONField for cross-database compatibility (SQLite doesn't support ArrayField)
    images = models.JSONField(_("Images"), default=list, blank=True)
    
    
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = _("Product Restaurant")
        verbose_name_plural = _("Product Restaurants")
        ordering = ["name"]


class ProductImageRestaurant(models.Model):
    product = models.ForeignKey(ProductRestaurant, on_delete=models.CASCADE, related_name="images_restaurant", verbose_name=_("Product"))
    image = models.ImageField(_("Image"), upload_to="product/images/")
    alt_text = models.CharField(_("Alt Text"), max_length=255)
    is_primary = models.BooleanField(_("Is Primary"), default=False)
    created_at = models.DateTimeField(_("Created At"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated At"), auto_now=True)

    class Meta:
        verbose_name = _("Product Image Restaurant")
        verbose_name_plural = _("Product Images Restaurant")
        unique_together = ("product", "image")
        ordering = ["created_at"]
        

# class Product(models.Model):
#     # provider type -> online store
#     category = models.ForeignKey(
#         ProductCategory,
#         on_delete=models.SET_NULL,
#         null=True,
#         blank=True,
#         related_name="products",
#         verbose_name=_("Category")
#     )
#     name = models.CharField(_("Name"), max_length=100)
#     description = models.TextField(_("Description"))
#     display_price = models.PositiveIntegerField(_("Display Price"), default=0)
#     stock = models.PositiveIntegerField(_("Stock"), default=0)
#     is_offer = models.BooleanField(_("Is Offer"), default=False)
#     is_active = models.BooleanField(_("Is Active"), default=True)
#     created_at = models.DateTimeField(_("Created At"), auto_now_add=True)
#     updated_at = models.DateTimeField(_("Updated At"), auto_now=True)

#     def __str__(self):
#         return self.name
    
#     def save(self, *args, **kwargs):
#         if self.stock <= 0:
#             self.is_active = False
#         super().save(*args, **kwargs)

#     class Meta:
#         verbose_name = _("Product")
#         verbose_name_plural = _("Products")


# class ProductImage(models.Model):
#     product = models.ForeignKey(
#         Product, 
#         on_delete=models.CASCADE, 
#         related_name='images'
#     )
#     image = models.ImageField(_("Image"), upload_to="product/images/")
#     alt_text = models.CharField(
#         _('Alt Text'),
#         max_length=255,
#         blank=True,
#         help_text=_('Alternative text for accessibility')
#     )
#     is_primary = models.BooleanField(
#         _('Primary Image'),
#         default=False,
#         help_text=_('Use as main image for this service')
#     )
#     created_at = models.DateTimeField(_('created at'), auto_now_add=True)

#     class Meta:
#         verbose_name = _("Product Image")
#         verbose_name_plural = _("Product Images")
#         ordering = ['-created_at']

#     def __str__(self):
#         return f"Image for {self.product.name}"

class Cart(models.Model):
    customer = models.ForeignKey(
        'User',
        on_delete=models.CASCADE,
        related_name='carts',
        verbose_name=_("Customer")
    )
    created_at = models.DateTimeField(_("Created At"), auto_now_add=True)

    def __str__(self):
        return f"Cart #{self.id} - {self.customer.name}"

    def total_price(self):
        return sum([item.get_total_price() for item in self.items.all()])

class CartItem(models.Model):
    cart = models.ForeignKey(
        Cart, 
        on_delete=models.CASCADE,
        related_name='items'
    )
    product = models.ForeignKey(ProductRestaurant, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(_("Quantity"), default=1)

    def get_total_price(self):
        return self.product.display_price * self.quantity

    def __str__(self):
        return f"{self.quantity}x {self.product.name}"
    
class Order(models.Model):
    STATUS_CHOICES = [
        ("pending", _("Pending")),
        ("preparing", _("Preparing")),
        ("on_the_way", _("On The Way")),
        ("delivered", _("Delivered")),
        ("cancelled", _("Cancelled")),
    ]
    PAYMENT_CHOICES = [
        ("cash", _("Cash on Delivery")),
        ("card", _("Credit/Debit Card")),
        ("wallet", _("Wallet")),
    ]

    customer = models.ForeignKey(
        'User',
        on_delete=models.CASCADE,
        related_name='orders',
        verbose_name=_("Customer")
    )
    restaurant = models.ForeignKey(
        'RestaurantModel',
        on_delete=models.CASCADE,
        related_name='orders',
        verbose_name=_("Restaurant")
    )
    driver = models.ForeignKey(
        'Provider',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='deliveries',
        verbose_name=_("Driver")
    )
    
    total_price = models.DecimalField(_("Total Price"), max_digits=10, decimal_places=2, default=0)
    discount = models.DecimalField(_("Discount"), max_digits=10, decimal_places=2, default=0)
    final_price = models.DecimalField(_("Final Price"), max_digits=10, decimal_places=2, default=0)
    status = models.CharField(_("Status"), max_length=20, choices=STATUS_CHOICES, default="pending")
    payment_method = models.CharField(_("Payment Method"), max_length=10, choices=PAYMENT_CHOICES, default="cash")  # 👈 جديد
    expected_order_time = models.DurationField(
        _("Expected Order Time"),
        help_text=_("Expected preparation/delivery time (e.g., 00:30:00 for 30 minutes)."),
        default=timedelta(minutes=30)
    )
    created_at = models.DateTimeField(_("Created At"), auto_now_add=True)

    def __str__(self):
        return f"Order #{self.id} - {self.customer.name}"
    
    def recalc_prices(self):
        """Recalculate total and final prices based on items and discount."""
        total = sum([item.quantity * item.price for item in self.items.all()])
        self.total_price = total
        self.final_price = max(total - self.discount, 0)
        self.save(update_fields=["total_price", "final_price", "discount"])


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items'
    )
    product = models.ForeignKey(ProductRestaurant, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(_("Quantity"), default=1)
    price = models.DecimalField(_("Price"), max_digits=10, decimal_places=2)  # snapshot at order time

    def __str__(self):
        return f"{self.quantity}x {self.product.name}"
    

def default_coupon_valid_to():
    return timezone.now() + timedelta(days=365)


class Coupon(models.Model):
    code = models.CharField(_("Code"), max_length=20, unique=True)
    discount_percentage = models.PositiveIntegerField(_("Discount Percentage"), default=0)
    valid_from = models.DateTimeField(_("Valid From"), default=timezone.now)
    valid_to = models.DateTimeField(_("Valid To"), default=default_coupon_valid_to)
    active = models.BooleanField(_("Active"), default=True)

    def is_valid(self):
        now = timezone.now()
        return self.active and self.valid_from <= now <= self.valid_to

    def __str__(self):
        return self.code
    
class ReviewRestaurant(models.Model):
    customer = models.ForeignKey(
        'User',
        on_delete=models.CASCADE,
        related_name='reviews'
    )
    restaurant = models.ForeignKey(
        'RestaurantModel',
        on_delete=models.CASCADE,
        related_name='reviews'
    )
    rating = models.PositiveIntegerField(_("Rating"), default=5)
    comment = models.TextField(_("Comment"), blank=True, null=True)
    created_at = models.DateTimeField(_("Created At"), auto_now_add=True)

    def __str__(self):
        return f"{self.customer.name} -> {self.restaurant.restaurant_name} ({self.rating})"

class OfferRestaurant(models.Model):
    restaurant = models.ForeignKey(
        'RestaurantModel',
        on_delete=models.CASCADE,
        related_name='offers',
        verbose_name=_("Restaurant")
    )
    title = models.CharField(_("Title"), max_length=100)
    description = models.TextField(_("Description"))
    discount_percentage = models.PositiveIntegerField(_("Discount Percentage"), default=0)
    valid_from = models.DateTimeField(_("Valid From"))
    valid_to = models.DateTimeField(_("Valid To"))
    active = models.BooleanField(_("Active"), default=True)

    def __str__(self):
        return f"{self.title} - {self.restaurant.restaurant_name}"

class DeliveryAddress(models.Model):
    customer = models.ForeignKey('User', on_delete=models.CASCADE, related_name="addresses")
    address = models.CharField(max_length=255)
    latitude = models.FloatField()
    longitude = models.FloatField()
    is_default = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.address} ({getattr(self.customer,'username',self.customer.id)})"


class Provider(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, verbose_name=_("User"))
    services = models.ManyToManyField(Service, verbose_name=_("Services"))
    sub_services = models.ManyToManyField(SubService, verbose_name=_("Sub Services"), blank=True)
    name_of_car = models.ForeignKey(NameOfCar, on_delete=models.CASCADE, verbose_name=_("Name Of Car"),blank=True,null=True)
    sub_service = models.CharField(_("Sub Service"), max_length=50, blank=True, null=True)
    is_verified = models.BooleanField(_("Is Verified"), default=False)
    in_ride = models.BooleanField(_("In Ride"), default=False)
    onLine = models.BooleanField(_("On Line"), default=True,null=True,blank=True)
    # restaurant = models.ForeignKey(RestaurantModel, on_delete=models.CASCADE, verbose_name=_("Restaurant"),blank=True,null=True)

    def __str__(self):
        return self.user.name
    
    def has_maintenance_service(self):
        """Check if provider has maintenance service"""
        return self.services.filter(name__icontains='maintenance').exists()
    
    def clean(self):
        """Validate that sub_service is only set when maintenance service is assigned"""
        from django.core.exceptions import ValidationError
        super().clean()
        if self.sub_service and not self.has_maintenance_service():
            raise ValidationError({
                'sub_service': _('Sub service can only be set when maintenance service is assigned.')
            })
    
    class Meta:
        verbose_name = _("Provider")
        verbose_name_plural = _("Providers")


class DriverProfile(models.Model):
    provider = models.OneToOneField(Provider, on_delete=models.CASCADE, related_name="driver_profile", verbose_name=_("Provider"))
    license = models.CharField(_("License"), max_length=200, unique=True)
    status = models.CharField(_("Status"), max_length=20, choices=[("available", _("Available")), ("in_ride", _("In Ride"))], default="available")
    is_verified = models.BooleanField(_("Is Verified"), default=False)
    documents = models.FileField(_("Documents"), upload_to="driver/documents/", null=True, blank=True)
    # Add any other driver-specific fields as needed

    def __str__(self):
        return f"{self.provider.user.name} - {self.license}"

    class Meta:
        verbose_name = _("Driver Profile")
        verbose_name_plural = _("Driver Profiles")


class DriverCar(models.Model):
    driver_profile = models.OneToOneField(DriverProfile, on_delete=models.CASCADE, related_name="car", null=True, blank=True, verbose_name=_("Driver Profile"))
    type = models.CharField(_("Type"), max_length=20)
    model = models.CharField(_("Model"), max_length=20)
    number = models.CharField(_("Number"), max_length=20)
    color = models.CharField(_("Color"), max_length=20)
    # license field removed

    def __str__(self):
        return f"{self.type} - {self.model} - {self.number}"

    class Meta:
        verbose_name = _("Driver Car")
        verbose_name_plural = _("Driver Cars")
        
class DriverCarImage(models.Model):
    car = models.ForeignKey(
        DriverCar, on_delete=models.CASCADE,
        related_name="images"
    )
    image = models.ImageField(_("Image"), upload_to="car/images/")

    def __str__(self):
        return f"Image for {self.car}"


class Customer(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, verbose_name=_("User"))
    in_ride = models.BooleanField(_("In Ride"), default=False)

    def __str__(self):
        return self.user.name
    
    class Meta:
        verbose_name = _("Customer")
        verbose_name_plural = _("Customers")


class CustomerPlace(models.Model):
    customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name="places", verbose_name=_("Customer"))
    location = PlainLocationField(based_fields=["cairo"], zoom=7, verbose_name=_("Location"))

    def __str__(self):
        return self.customer.name
    
    class Meta:
        verbose_name = _("Customer Place")
        verbose_name_plural = _("Customer Places")



class RideStatus(models.Model):
    STATUS_CHOICES = [
        ("pending", _("Pending")),
        ("accepted", _("Accepted")),
        ("starting", _("Starting")),
        ("arriving", _("Arriving")),
        ("finished", _("Finished")),
        ("cancelled", _("Cancelled")),
    ]

    client = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name="rides_as_client",
        verbose_name=_("Client")
    )
    provider = models.ForeignKey(
        User, on_delete=models.CASCADE,
        null=True, blank=True,
        related_name="rides_as_provider",
        verbose_name=_("Provider")
    )
    service = models.ForeignKey(
        Service, on_delete=models.SET_NULL,
        null=True,
        verbose_name=_("Service")
    )
    status = models.CharField(
        _("Status"),
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending"
    )
    name_of_car_id = models.ForeignKey(
        NameOfCar,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("Name of Car")
    )

    pickup_lat = models.FloatField(_("Pickup Latitude"), null=True, blank=True)
    pickup_lng = models.FloatField(_("Pickup Longitude"), null=True, blank=True)
    drop_lat = models.FloatField(_("Drop Latitude"), null=True, blank=True)
    drop_lng = models.FloatField(_("Drop Longitude"), null=True, blank=True)
    total_price = models.FloatField(_("Total Price"), null=True, blank=True)
    distance_km = models.FloatField(_("Distance (km)"), null=True, blank=True)
    duration_minutes = models.FloatField(_("Duration (minutes)"), null=True, blank=True)
    total_price_before_discount = models.FloatField(
        _("Total Price Before Discount"),
        null=True,
        blank=True,
        help_text=_("Total price before applying any discounts or coupons")
    )
    # Add any other ride-specific fields as needed

    created_at = models.DateTimeField(_("Created At"), auto_now_add=True)

    def can_be_rated_by(self, user):
        """Check if the user can rate this ride"""
        if not self.status == 'finished':
            return False
        if user == self.client:
            return not self.rating.customer_rating if hasattr(self, 'rating') else True
        if user == self.provider:
            return not self.rating.driver_rating if hasattr(self, 'rating') else True
        return False

    def __str__(self):
        return f"{_('Ride')} #{self.pk} - {self.get_status_display()}"


class UserPoints(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, verbose_name=_("User"))
    points = models.PositiveIntegerField(_("Points"), default=0)

    def __str__(self):
        return f"{self.user.name} - {self.points} points"
    
    class Meta:
        verbose_name = _("User Points")
        verbose_name_plural = _("User Points")


class Product(models.Model):
    # provider type -> online store
    provider = models.ForeignKey(Provider, on_delete=models.CASCADE, related_name="products", verbose_name=_("Provider"), null=True, blank=True)
    name = models.CharField(_("Name"), max_length=100)
    description = models.TextField(_("Description"))
    display_price = models.PositiveIntegerField(_("Display Price"), default=0)
    stock = models.PositiveIntegerField(_("Stock"), default=0)
    is_active = models.BooleanField(_("Is Active"), default=True)
    created_at = models.DateTimeField(_("Created At"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated At"), auto_now=True)

    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if self.stock <= 0:
            self.is_active = False
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = _("Product")
        verbose_name_plural = _("Products")


class Purchase(models.Model):
    STATUS_PENDING = "pending"
    STATUS_CONFIRMED = "confirmed"
    STATUS_IN_PROGRESS = "in_progress"
    STATUS_COMPLETED = "completed"
    STATUS_CANCELLED = "cancelled"

    STATUS_CHOICES = [
        (STATUS_PENDING, _("Pending")),
        (STATUS_CONFIRMED, _("Confirmed")),
        (STATUS_IN_PROGRESS, _("In Progress")),
        (STATUS_COMPLETED, _("Completed")),
        (STATUS_CANCELLED, _("Cancelled")),
    ]
    
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="purchases", verbose_name=_("Customer"))
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="purchases", verbose_name=_("Product"))
    money_spent = models.PositiveIntegerField(_("Money Spent"), default=0)
    quantity = models.PositiveIntegerField(_("Quantity"), default=1)
    status = models.CharField(
        _("Status"),
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING
    )
    created_at = models.DateTimeField(_("Created At"), auto_now_add=True)

    def __str__(self):
        return f"{self.customer.user.name} - {self.product.name}"
    
    class Meta:
        verbose_name = _("Purchase")
        verbose_name_plural = _("Purchases")
        
        
class CarAgency(models.Model):
    provider = models.ForeignKey('Provider', on_delete=models.CASCADE, related_name='car_agencies', verbose_name=_('Provider'), null=True, blank=True)
    model = models.CharField(_("Model"), max_length=50, null=True, blank=True)
    brand = models.CharField(_("Brand"), max_length=50, null=True, blank=True)
    color = models.CharField(_("Color"), max_length=20, null=True, blank=True)
    price_per_hour = models.DecimalField(_("Price per Hour"), max_digits=10, decimal_places=2)
    available = models.BooleanField(_("Available"), default=False)
    image = models.ImageField(_("Image"), upload_to="car_agency/images/", null=True, blank=True)
    # Buying options
    for_sale = models.BooleanField(_("For Sale"), default=False)
    sale_price = models.DecimalField(_("Sale Price"), max_digits=12, decimal_places=2, null=True, blank=True)
    is_sold = models.BooleanField(_("Is Sold"), default=False)
    created_at = models.DateTimeField(_("Created At"), auto_now_add=True)
    
    def __str__(self):
        return f"{self.brand} {self.model} ({self.color})"
    
    def update_availability(self):
        """
        Automatically checks slots + rentals and updates the stored available field.
        """
        from django.utils import timezone
        now = timezone.now()
        slots = self.availability_slots.filter(end_time__gte=now)
        for slot in slots:
            overlapping_rentals = self.rentals.filter(
                start_datetime__lt=slot.end_time,
                end_datetime__gt=slot.start_time,
                status__in=["pending", "confirmed", "in_progress", "completed"]
            )
            cuts = [(slot.start_time, slot.end_time)]
            for rental in overlapping_rentals:
                new_cuts = []
                for cut_start, cut_end in cuts:
                    if rental.end_datetime <= cut_start or rental.start_datetime >= cut_end:
                        new_cuts.append((cut_start, cut_end))
                    else:
                        if rental.start_datetime > cut_start:
                            new_cuts.append((cut_start, rental.start_datetime))
                        if rental.end_datetime < cut_end:
                            new_cuts.append((rental.end_datetime, cut_end))
                cuts = new_cuts
            if cuts:
                self.available = True
                self.save(update_fields=['available'])
                return
        self.available = False
        self.save(update_fields=['available'])

class CarAvailability(models.Model):
    car = models.ForeignKey(CarAgency, on_delete=models.CASCADE, related_name='availability_slots', verbose_name=_("Car"))
    start_time = models.DateTimeField(_("Available From"))
    end_time = models.DateTimeField(_("Available Until"))

    def __str__(self):
        return f"{self.car.brand} {self.car.model} — {self.start_time} to {self.end_time}"

class CarRental(models.Model):
    
    STATUS_PENDING = "pending"
    STATUS_CONFIRMED = "confirmed"
    STATUS_IN_PROGRESS = "in_progress"
    STATUS_COMPLETED = "completed"
    STATUS_CANCELLED = "cancelled"

    STATUS_CHOICES = [
        (STATUS_PENDING, _("Pending")),
        (STATUS_CONFIRMED, _("Confirmed")),
        (STATUS_IN_PROGRESS, _("In Progress")),
        (STATUS_COMPLETED, _("Completed")),
        (STATUS_CANCELLED, _("Cancelled")),
    ]
    
    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name='car_rentals',
        verbose_name=_("Customer")
    )
    car = models.ForeignKey(
        CarAgency,
        on_delete=models.CASCADE,
        related_name='rentals',
        verbose_name=_("Car")
    )
    start_datetime = models.DateTimeField(_("Rental Start"))
    end_datetime = models.DateTimeField(_("Rental End"))
    
    total_price = models.DecimalField(
        _("Total Price"),
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )
    status = models.CharField(
        _("Status"),
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING
    )
    created_at = models.DateTimeField(_("Created At"), auto_now_add=True)

    def __str__(self):
        return f"{self.customer.user.name} rents {self.car.brand} {self.car.model} from {self.start_datetime} to {self.end_datetime}"

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        old_status = None

        if not is_new:
            old_status = CarRental.objects.get(pk=self.pk).status

        # Compute total price on create
        if not self.total_price:
            duration = self.end_datetime - self.start_datetime
            hours = duration.total_seconds() / 3600
            self.total_price = float(self.car.price_per_hour) * hours

        super().save(*args, **kwargs)

        # ✅ If newly created OR if status changed:
        if is_new or old_status != self.status:
            self.car.update_availability()

    class Meta:
        verbose_name = _("Car Rental")
        verbose_name_plural = _("Car Rentals")

class CarPurchase(models.Model):
    STATUS_PENDING = "pending"
    STATUS_CONFIRMED = "confirmed"
    STATUS_COMPLETED = "completed"
    STATUS_CANCELLED = "cancelled"

    STATUS_CHOICES = [
        (STATUS_PENDING, _("Pending")),
        (STATUS_CONFIRMED, _("Confirmed")),
        (STATUS_COMPLETED, _("Completed")),
        (STATUS_CANCELLED, _("Cancelled")),
    ]

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="car_purchases", verbose_name=_("Customer"))
    listing = models.ForeignKey('CarSaleListing', on_delete=models.CASCADE, related_name="purchases", verbose_name=_("Listing"), null=True, blank=True)
    price = models.DecimalField(_("Price"), max_digits=12, decimal_places=2)
    status = models.CharField(_("Status"), max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    created_at = models.DateTimeField(_("Created At"), auto_now_add=True)

    class Meta:
        verbose_name = _("Car Purchase")
        verbose_name_plural = _("Car Purchases")

    def __str__(self):
        return f"{self.customer.user.name} buys {self.listing.brand} {self.listing.model}"

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        old_status = None
        if not is_new:
            old_status = CarPurchase.objects.get(pk=self.pk).status
        # Auto-set price from listing if not provided
        if not self.price and getattr(self, 'listing', None):
            self.price = self.listing.price
        super().save(*args, **kwargs)
        if (is_new and self.status == self.STATUS_COMPLETED) or (not is_new and old_status != self.status and self.status == self.STATUS_COMPLETED):
            if not self.listing.is_sold:
                self.listing.is_sold = True
                self.listing.is_active = False
                self.listing.save(update_fields=["is_sold", "is_active"])

    

class ProductImage(models.Model):
    product = models.ForeignKey('Product', related_name='images', on_delete=models.CASCADE, verbose_name=_("Product"))
    image = models.ImageField(upload_to='product_images/', verbose_name=_("Image"))

    
    def __str__(self):
        return _("Image for %(product_name)s") % {"product_name": self.product.name}

    class Meta:
        verbose_name = _("Product Image")
        verbose_name_plural = _("Product Images")


class CarSaleListing(models.Model):
    TRANSMISSION_CHOICES = [
        ("manual", _("Manual")),
        ("automatic", _("Automatic")),
    ]
    FUEL_CHOICES = [
        ("gasoline", _("Gasoline")),
        ("diesel", _("Diesel")),
        ("hybrid", _("Hybrid")),
        ("electric", _("Electric")),
    ]

    provider = models.ForeignKey('Provider', on_delete=models.CASCADE, related_name='car_sale_listings', verbose_name=_('Provider'))
    title = models.CharField(_("Title"), max_length=120)
    brand = models.CharField(_("Brand"), max_length=50)
    model = models.CharField(_("Model"), max_length=50)
    year = models.PositiveIntegerField(_("Year"), null=True, blank=True)
    mileage_km = models.PositiveIntegerField(_("Mileage (km)"), null=True, blank=True)
    transmission = models.CharField(_("Transmission"), max_length=10, choices=TRANSMISSION_CHOICES, null=True, blank=True)
    fuel_type = models.CharField(_("Fuel Type"), max_length=10, choices=FUEL_CHOICES, null=True, blank=True)
    color = models.CharField(_("Color"), max_length=20, null=True, blank=True)
    price = models.DecimalField(_("Price"), max_digits=12, decimal_places=2)
    description = models.TextField(_("Description"), blank=True)
    is_active = models.BooleanField(_("Is Active"), default=True)
    is_sold = models.BooleanField(_("Is Sold"), default=False)
    created_at = models.DateTimeField(_("Created At"), auto_now_add=True)

    class Meta:
        verbose_name = _("Car Sale Listing")
        verbose_name_plural = _("Car Sale Listings")
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} - {self.brand} {self.model}"

    def save(self, *args, **kwargs):
        if self.is_sold:
            self.is_active = False
        super().save(*args, **kwargs)


class CarSaleImage(models.Model):
    listing = models.ForeignKey(CarSaleListing, related_name='images', on_delete=models.CASCADE, verbose_name=_('Listing'))
    image = models.ImageField(upload_to='car_sale/images/', verbose_name=_('Image'))

    class Meta:
        verbose_name = _("Car Sale Image")
        verbose_name_plural = _("Car Sale Images")


class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ('ride_request', _('Ride Request')),
        ('ride_accepted', _('Ride Accepted')),
        ('ride_status', _('Ride Status Update')),
        ('car_rental', _('Car Rental Update')),
        ('product_order', _('Product Order Update')),
        ('general', _('General Notification')),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name=_("User")
    )
    title = models.CharField(_("Title"), max_length=255)
    message = models.TextField(_("Message"))
    notification_type = models.CharField(
        _("Notification Type"),
        max_length=20,
        choices=NOTIFICATION_TYPES,
        default='general'
    )
    data = models.JSONField(_("Additional Data"), default=dict, blank=True)
    is_read = models.BooleanField(_("Is Read"), default=False)
    created_at = models.DateTimeField(_("Created At"), auto_now_add=True)

    class Meta:
        verbose_name = _("Notification")
        verbose_name_plural = _("Notifications")
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} - {self.user.name}"

    def mark_as_read(self):
        self.is_read = True
        self.save()

class Rating(models.Model):
    ride = models.OneToOneField(
        RideStatus,
        on_delete=models.CASCADE,
        related_name='rating',
        verbose_name=_("Ride")
    )
    driver_rating = models.PositiveSmallIntegerField(
        _("Driver Rating"),
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    customer_rating = models.PositiveSmallIntegerField(
        _("Customer Rating"),
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    driver_comment = models.TextField(_("Driver Comment"), blank=True)
    customer_comment = models.TextField(_("Customer Comment"), blank=True)
    created_at = models.DateTimeField(_("Created At"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated At"), auto_now=True)

    class Meta:
        verbose_name = _("Rating")
        verbose_name_plural = _("Ratings")

    def __str__(self):
        return f"Rating for Ride #{self.ride.id}"        


class ScheduledRide(models.Model):
    STATUS_PENDING = "pending"
    STATUS_ACCEPTED = "accepted"
    STATUS_STARTED = "started"
    STATUS_FINISHED = "finished"
    STATUS_CANCELLED = "cancelled"

    STATUS_CHOICES = [
        (STATUS_PENDING, _("Pending")),
        (STATUS_ACCEPTED, _("Accepted")),
        (STATUS_STARTED, _("Started")),
        (STATUS_FINISHED, _("Finished")),
        (STATUS_CANCELLED, _("Cancelled")),
    ]

    client = models.ForeignKey(User, on_delete=models.CASCADE, related_name="scheduled_as_client", verbose_name=_("Client"))
    provider = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name="scheduled_as_provider", verbose_name=_("Provider"))
    service = models.ForeignKey(Service, on_delete=models.CASCADE, verbose_name=_("Service"))
    sub_service = models.ForeignKey(SubService, on_delete=models.CASCADE, related_name="scheduled_rides", verbose_name=_("Sub Service"), null=True, blank=True)
    pickup_lat = models.FloatField(_("Pickup Latitude"))
    pickup_lng = models.FloatField(_("Pickup Longitude"))
    drop_lat = models.FloatField(_("Drop Latitude"), null=True, blank=True)
    drop_lng = models.FloatField(_("Drop Longitude"), null=True, blank=True)
    scheduled_time = models.DateTimeField(_("Scheduled Time"))
    status = models.CharField(_("Status"), max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    total_price = models.DecimalField(_("Total Price"), max_digits=10, decimal_places=2, null=True, blank=True)
    distance_km = models.FloatField(_("Distance (km)"), null=True, blank=True)
    duration_minutes = models.FloatField(_("Duration (minutes)"), null=True, blank=True)
    created_at = models.DateTimeField(_("Created At"), auto_now_add=True)

    class Meta:
        verbose_name = _("Scheduled Ride")
        verbose_name_plural = _("Scheduled Rides")
        ordering = ["-scheduled_time"]

    def __str__(self):
        return f"ScheduledRide #{self.id} at {self.scheduled_time}"


class ScheduledRideRating(models.Model):
    ride = models.OneToOneField(
        ScheduledRide,
        on_delete=models.CASCADE,
        related_name='rating',
        verbose_name=_("Scheduled Ride")
    )
    driver_rating = models.PositiveSmallIntegerField(
        _("Driver Rating"),
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    customer_rating = models.PositiveSmallIntegerField(
        _("Customer Rating"),
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    driver_comment = models.TextField(_("Driver Comment"), blank=True)
    customer_comment = models.TextField(_("Customer Comment"), blank=True)
    created_at = models.DateTimeField(_("Created At"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated At"), auto_now=True)

    class Meta:
        verbose_name = _("Scheduled Ride Rating")
        verbose_name_plural = _("Scheduled Ride Ratings")

    def __str__(self):
        return f"ScheduledRideRating for Ride #{self.ride.id}"


class ProviderServicePricing(models.Model):
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name="provider_pricings")
    sub_service = models.ForeignKey(SubService, on_delete=models.CASCADE, related_name="provider_pricings", verbose_name=_("Sub Service"), null=True, blank=True)
    zone = models.ForeignKey(PricingZone, on_delete=models.CASCADE, related_name="pricings", verbose_name=_("Pricing Zone"), null=True, blank=True)
    
    # Application fees
    platform_fee = models.DecimalField(_("Platform Fee"), max_digits=10, decimal_places=2, default=0, help_text=_("Fixed fee charged by the platform"))
    service_fee = models.DecimalField(_("Service Fee"), max_digits=10, decimal_places=2, default=0, help_text=_("Additional service fee"))
    booking_fee = models.DecimalField(_("Booking Fee"), max_digits=10, decimal_places=2, default=0, help_text=_("One-time booking fee"))
    
    # Zone-based pricing fields
    base_fare = models.DecimalField(_("Base Fare"), max_digits=10, decimal_places=2, default=0, help_text=_("Fixed starting price"))
    price_per_km = models.DecimalField(_("Price per KM"), max_digits=10, decimal_places=2, default=0)
    price_per_minute = models.DecimalField(_("Price per Minute"), max_digits=10, decimal_places=2, default=0)
    minimum_fare = models.DecimalField(_("Minimum Fare"), max_digits=10, decimal_places=2, default=0, help_text=_("Minimum total price for the ride"))
    
    # Time-based multipliers
    peak_hour_multiplier = models.DecimalField(_("Peak Hour Multiplier"), max_digits=4, decimal_places=2, default=1.0, help_text=_("Multiplier for peak hours (e.g., 1.5 for 50% increase)"))
    peak_hours_start = models.TimeField(_("Peak Hours Start"), null=True, blank=True)
    peak_hours_end = models.TimeField(_("Peak Hours End"), null=True, blank=True)
    
    # Additional settings
    is_active = models.BooleanField(_("Is Active"), default=True)
    created_at = models.DateTimeField(_("Created At"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated At"), auto_now=True)

    class Meta:
        unique_together = ('service', 'sub_service', 'zone')
        verbose_name = _("Provider Service Pricing")
        verbose_name_plural = _("Provider Service Pricings")

    def __str__(self):
        zone_name = f" - {self.zone.name}" if self.zone else ""
        return f"{self.service.name} - {self.sub_service or ''}{zone_name}"
    
    def calculate_price(self, distance_km=0, duration_minutes=0, pickup_time=None):
        """
        Calculate the total price based on distance, duration, and time
        """
        from django.utils import timezone
        
        # Calculate base price
        total_price = float(self.base_fare)
        total_price += float(self.price_per_km) * distance_km
        total_price += float(self.price_per_minute) * duration_minutes
        
        # Apply peak hour multiplier if applicable
        if pickup_time and self.peak_hours_start and self.peak_hours_end:
            pickup_time_only = pickup_time.time() if hasattr(pickup_time, 'time') else pickup_time
            if self.peak_hours_start <= pickup_time_only <= self.peak_hours_end:
                total_price *= float(self.peak_hour_multiplier)
        
        # Add application fees
        total_price += float(self.platform_fee or 0)
        total_price += float(self.service_fee or 0)
        total_price += float(self.booking_fee or 0)
        
        # Ensure minimum fare
        total_price = max(total_price, float(self.minimum_fare))
        
        return round(total_price, 2)
    
    @classmethod
    def get_pricing_for_location(cls, service, sub_service, lat, lng):
        """
        Get the appropriate pricing based on location
        """
        # First try to find zone-based pricing
        for zone in PricingZone.objects.filter(is_active=True):
            if zone.contains_point(lat, lng):
                pricing = cls.objects.filter(
                    service=service,
                    sub_service=sub_service,
                    zone=zone,
                    is_active=True
                ).first()
                if pricing:
                    return pricing
        
        # Fall back to default pricing (no zone)
        return cls.objects.filter(
            service=service,
            sub_service=sub_service,
            zone__isnull=True,
            is_active=True
        ).first()

    def clean(self):
        allowed_services = [
            "maintenance service",
            "delivery service",
            "car request",
            "food delivery"
        ]
        if self.service.name.lower() not in allowed_services:
            from django.core.exceptions import ValidationError
            raise ValidationError({
                'service': _(f"Pricing can only be set for maintenance service, delivery service, car request, or food delivery.")
            })
        # If service is maintenance, sub_service is required
        if self.service.name.lower() == "maintenance service" and not self.sub_service:
            from django.core.exceptions import ValidationError
            raise ValidationError({
                'sub_service': _(f"Sub Service is required for maintenance service pricing.")
            })
        # If service is not maintenance, sub_service must be blank
        # if self.service.name.lower() != "maintenance service" and self.sub_service:
        #     from django.core.exceptions import ValidationError
        #     raise ValidationError({
        #         'sub_service': _(f"Sub Service should only be set for maintenance service pricing.")
        #     })
        super().clean()

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs) 


class PlatformSettings(models.Model):
    platform_name = models.CharField(max_length=255, default="Riders Admin")
    platform_logo = models.ImageField(upload_to='dashboard_logos/', null=True, blank=True)

    def __str__(self):
        return "Platform Settings"

    class Meta:
        verbose_name = "Platform Settings"
        verbose_name_plural = "Platform Settings"


class Invoice(models.Model):
    INVOICE_STATUS = [
        ('paid', _('Paid')),
        ('unpaid', _('Unpaid')),
        ('cancelled', _('Cancelled')),
    ]

    ride = models.OneToOneField(
        'RideStatus',
        on_delete=models.CASCADE,
        related_name='invoice',
        verbose_name=_('Ride')
    )
    issued_at = models.DateTimeField(_('Issued At'), default=timezone.now)
    total_amount = models.DecimalField(_('Total Amount'), max_digits=10, decimal_places=2)
    tax = models.DecimalField(_('Tax'), max_digits=10, decimal_places=2, default=0)
    discount = models.DecimalField(_('Discount'), max_digits=10, decimal_places=2, default=0)
    final_amount = models.DecimalField(_('Final Amount'), max_digits=10, decimal_places=2)
    status = models.CharField(_('Status'), choices=INVOICE_STATUS, max_length=10, default='unpaid')
    notes = models.TextField(_('Notes'), blank=True)

    class Meta:
        verbose_name = _('Invoice')
        verbose_name_plural = _('Invoices')
        ordering = ['-issued_at']

    def __str__(self):
        return f"Invoice #{self.id} for Ride #{self.ride_id}"
    
class CouponRestaurant(models.Model):
    code = models.CharField(_("Code"), max_length=50, unique=True)
    discount_percentage = models.DecimalField(_("Discount Percentage"), max_digits=5, decimal_places=2, validators=[MinValueValidator(0), MaxValueValidator(100)])
    is_active = models.BooleanField(_("Is Active"), default=True)
    created_at = models.DateTimeField(_("Created At"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated At"), auto_now=True)

    def __str__(self):
        return self.code
    
    class Meta:
        verbose_name = _("Coupon")
        verbose_name_plural = _("Coupons")
    def clean(self):
        if self.discount_percentage < 0 or self.discount_percentage > 100:
            raise ValidationError(_("Discount percentage must be between 0 and 100."))
        super().clean()


# Proxy model to expose Restaurant Reports in Django admin (no database table)
class RestaurantReportsProxy(RestaurantModel):
    class Meta:
        proxy = True
        verbose_name = _("Restaurant Reports")
        verbose_name_plural = _("Restaurant Reports")

    def __str__(self):
        return _("Restaurant Reports")