from authentication.choices import ROLE_CHOICES
from authentication.managers import UserManager
from django.contrib.auth.models import AbstractUser
from django.db import models
from location_field.models.plain import PlainLocationField
#from django.contrib.gis.db import models as gis_models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone


class User(AbstractUser):
    name = models.CharField(_("Name"), max_length=30)
    phone = models.CharField(_("Phone"),max_length=20, unique=True)
    image = models.ImageField(_("Image"),upload_to="user/images/")
    role = models.CharField(_("Role"), max_length=2, choices=ROLE_CHOICES)
    location = PlainLocationField(based_fields=["cairo"], verbose_name=_("Location"))
    location2_lat = models.FloatField(null=True, blank=True, verbose_name=_("Location2 Latitude"))
    location2_lng = models.FloatField(null=True, blank=True, verbose_name=_("Location2 Longitude"))


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
    service = models.ForeignKey(Service, on_delete=models.CASCADE, verbose_name=_("Service"))
    is_verified = models.BooleanField(_("Is Verified"), default=False)
    # created_at = models.DateTimeField(_("Created At"), auto_now_add=True,null=True, blank=True)

    def __str__(self):
        return self.user.name
    
    class Meta:
        verbose_name = _("Provider")
        verbose_name_plural = _("Providers")


class Driver(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, verbose_name=_("User"))
    license = models.CharField(_("License"), max_length=20, unique=True)
    in_ride = models.BooleanField(_("In Ride"), default=False)
    is_verified = models.BooleanField(_("Is Verified"), default=False)

    def __str__(self):
        return self.user.name
    
    class Meta:
        verbose_name = _("Driver")
        verbose_name_plural = _("Drivers")


class DriverCar(models.Model):
    driver = models.ForeignKey(Driver, on_delete=models.CASCADE, verbose_name=_("Driver"))
    type = models.CharField(_("Type"), max_length=20)
    model = models.CharField(_("Model"), max_length=20)
    number = models.CharField(_("Number"), max_length=20)
    color = models.CharField(_("Color"), max_length=20)
    image = models.ImageField(_("Image"), upload_to="car/images/")
    license = models.CharField(_("License"), max_length=20, unique=True)

    def __str__(self):
        return self.type

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
    
    class Meta:
        verbose_name = _("Product")
        verbose_name_plural = _("Products")

class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="images", verbose_name=_("Product"))
    image = models.ImageField(_("Image"), upload_to="product/images/")

    def __str__(self):
        return f"Image for {self.product.name}"
    
    class Meta:
        verbose_name = _("Product Image")
        verbose_name_plural = _("Product Images")


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
                end_datetime__gt=slot.start_time
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
    car = models.ForeignKey(CarAgency, on_delete=models.CASCADE, related_name='availability_slots')
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
        (STATUS_PENDING, "Pending"),
        (STATUS_CONFIRMED, "Confirmed"),
        (STATUS_IN_PROGRESS, "In Progress"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_CANCELLED, "Cancelled"),
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

    

