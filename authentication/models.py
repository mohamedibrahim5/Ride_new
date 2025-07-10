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


class User(AbstractUser):
    name = models.CharField(_("Name"), max_length=30)
    phone = models.CharField(_("Phone"),max_length=20, unique=True)
    image = models.ImageField(_("Image"),upload_to="user/images/")
    role = models.CharField(_("Role"), max_length=2, choices=ROLE_CHOICES)
    location = PlainLocationField(based_fields=["cairo"], verbose_name=_("Location"))
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
    groups = None
    user_permissions = None
    REQUIRED_FIELDS = []
    is_active = models.BooleanField(_("Is Active"), default=False)

    objects = UserManager()
    USERNAME_FIELD = "phone"

    def __str__(self):
        return str(self.phone)
    
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


class Provider(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, verbose_name=_("User"))
    services = models.ManyToManyField(Service, verbose_name=_("Services"))
    sub_service = models.CharField(_("Sub Service"), max_length=50, blank=True, null=True)
    is_verified = models.BooleanField(_("Is Verified"), default=False)
    in_ride = models.BooleanField(_("In Ride"), default=False)

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
    license = models.CharField(_("License"), max_length=20, unique=True)
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
    image = models.ImageField(_("Image"), upload_to="car/images/")
    # license field removed

    def __str__(self):
        return f"{self.type} - {self.model} - {self.number}"

    class Meta:
        verbose_name = _("Driver Car")
        verbose_name_plural = _("Driver Cars")


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

    pickup_lat = models.FloatField(_("Pickup Latitude"), null=True, blank=True)
    pickup_lng = models.FloatField(_("Pickup Longitude"), null=True, blank=True)
    drop_lat = models.FloatField(_("Drop Latitude"), null=True, blank=True)
    drop_lng = models.FloatField(_("Drop Longitude"), null=True, blank=True)

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
    provider = models.ForeignKey(Provider, on_delete=models.CASCADE, related_name="products", verbose_name=_("Provider"))
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

    

class ProductImage(models.Model):
    product = models.ForeignKey('Product', related_name='images', on_delete=models.CASCADE, verbose_name=_("Product"))
    image = models.ImageField(upload_to='product_images/', verbose_name=_("Image"))

    
    def __str__(self):
        return _("Image for %(product_name)s") % {"product_name": self.product.name}

    class Meta:
        verbose_name = _("Product Image")
        verbose_name_plural = _("Product Images")


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

class ProviderServicePricing(models.Model):
    provider = models.ForeignKey(Provider, on_delete=models.CASCADE, related_name="service_pricings")
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name="provider_pricings")
    sub_service = models.CharField(_("Sub Service"), max_length=50, blank=True, null=True)
    application_fee = models.DecimalField(_("Application Fee"), max_digits=10, decimal_places=2, default=0)
    service_price = models.DecimalField(_("Service Price"), max_digits=10, decimal_places=2, default=0)
    delivery_fee_per_km = models.DecimalField(_("Delivery Fee per KM"), max_digits=10, decimal_places=2, default=0)

    class Meta:
        unique_together = ('provider', 'service', 'sub_service')
        verbose_name = _("Provider Service Pricing")
        verbose_name_plural = _("Provider Service Pricings")

    def __str__(self):
        return f"{self.provider.user.name} - {self.service.name} - {self.sub_service or ''}"

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
        if self.service.name.lower() != "maintenance service" and self.sub_service:
            from django.core.exceptions import ValidationError
            raise ValidationError({
                'sub_service': _(f"Sub Service should only be set for maintenance service pricing.")
            })
        super().clean()

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs) 