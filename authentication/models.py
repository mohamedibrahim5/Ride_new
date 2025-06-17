from authentication.choices import ROLE_CHOICES
from authentication.managers import UserManager
from django.contrib.auth.models import AbstractUser
from django.db import models
from location_field.models.plain import PlainLocationField
from django.contrib.gis.db import models as gis_models
from django.utils.translation import gettext_lazy as _



class User(AbstractUser):
    name = models.CharField(_("Name"), max_length=30)
    phone = models.CharField(_("Phone"),max_length=20, unique=True)
    image = models.ImageField(_("Image"),upload_to="user/images/")
    role = models.CharField(_("Role"), max_length=2, choices=ROLE_CHOICES)
    location = PlainLocationField(based_fields=["cairo"], verbose_name=_("Location"))
    location2 = gis_models.PointField(srid=4326, null=True, blank=True, verbose_name=_("Location2"))


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
    points_price = models.PositiveIntegerField(_("Points Price"))
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
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="purchases", verbose_name=_("Customer"))
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="purchases", verbose_name=_("Product"))
    points_spent = models.PositiveIntegerField(_("Points Spent"))
    quantity = models.PositiveIntegerField(_("Quantity"), default=1)
    created_at = models.DateTimeField(_("Created At"), auto_now_add=True)

    def __str__(self):
        return f"{self.customer.user.name} - {self.product.name}"
    
    class Meta:
        verbose_name = _("Purchase")
        verbose_name_plural = _("Purchases")