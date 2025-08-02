from authentication.choices import (
    ROLE_CUSTOMER,
    ROLE_PROVIDER,
    ROLE_CHOICES,
    FCM_CHOICES,
)
from authentication.models import (
    User,
    UserOtp,
    Service,
    Provider,
    Customer,
    CustomerPlace,
    RideStatus,
    UserPoints,
    Product,
    Purchase,
    DriverProfile,
    DriverCar,
    Notification,
    Rating,
    ProviderServicePricing,
    PricingZone,
)
from authentication.utils import send_sms, extract_user_data, update_user_data
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework.authtoken.models import Token
from django.utils import timezone
from fcm_django.models import FCMDevice
from django.contrib.gis.geos import Point
from django.db.models import Avg
from .models import CarAgency, CarAvailability, CarRental, ProductImage
import math


class PricingZoneSerializer(serializers.ModelSerializer):
    class Meta:
        model = PricingZone
        fields = ['id', 'name', 'description', 'boundaries', 'is_active']


class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    role = serializers.ChoiceField(write_only=True, choices=ROLE_CHOICES)
    location2_lat = serializers.FloatField(required=False, allow_null=True)
    location2_lng = serializers.FloatField(required=False, allow_null=True)
    average_rating = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "name",
            "phone",
            "email",
            "password",
            "image",
            "role",
            "location",
            "location2_lat",
            "location2_lng",
            "average_rating",
        ]

    def get_average_rating(self, obj):
        """
        Calculate the average rating for the user based on their role.
        """
        if obj.role == ROLE_CUSTOMER and hasattr(obj, 'customer'):
            ratings = Rating.objects.filter(ride__client=obj).exclude(customer_rating__isnull=True)
            if ratings.exists():
                avg_rating = ratings.aggregate(Avg('customer_rating'))['customer_rating__avg']
                return round(avg_rating, 2) if avg_rating else None
        elif obj.role == ROLE_PROVIDER and hasattr(obj, 'provider'):
            ratings = Rating.objects.filter(ride__provider=obj).exclude(driver_rating__isnull=True)
            if ratings.exists():
                avg_rating = ratings.aggregate(Avg('driver_rating'))['driver_rating__avg']
                return round(avg_rating, 2) if avg_rating else None
        return None

    def validate(self, attrs):
        location_str = attrs.get("location", "")
        lat = attrs.get("location2_lat")
        lng = attrs.get("location2_lng")
        if lat is None or lng is None:
            if location_str:
                try:
                    lat_val, lng_val = map(float, location_str.split(","))
                    attrs["location2_lat"] = lat_val
                    attrs["location2_lng"] = lng_val
                except Exception:
                    raise serializers.ValidationError(_("Invalid location format."))
            else:
                raise serializers.ValidationError(_("Location is required."))
        return attrs

    def create(self, validated_data):
        print("Creating user with data:", validated_data)
        phone = validated_data.get("phone")
        otp = send_sms(phone)
        if otp:
            user = User.objects.create_user(**validated_data)
            UserOtp.objects.update_or_create(user=user, otp=otp)
            return user
        else:
            raise serializers.ValidationError(
                {"sms": _("the sms service is not working try again later")}
            )

    def update(self, instance, validated_data):
        if "phone" in validated_data:
            validated_data.pop("phone")
        if "password" in validated_data:
            validated_data.pop("password")
        if "role" in validated_data:
            validated_data.pop("role")
        return super().update(instance, validated_data)


class ServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = ["id", "name"]


class ProviderSerializer(serializers.ModelSerializer):
    service_ids = serializers.ListField(
        child=serializers.IntegerField(), write_only=True, required=False
    )
    user = UserSerializer(read_only=True)
    services = ServiceSerializer(many=True, read_only=True)

    class Meta:
        model = Provider
        fields = ["id", "user", "service_ids", "services", "sub_service"]

    def validate(self, attrs):
        service_ids = attrs.get("service_ids", None)
        sub_service = attrs.get('sub_service')
        
        if sub_service and service_ids:
            # Check if maintenance service is in the service_ids
            services = Service.objects.filter(pk__in=service_ids)
            print(f"Service IDs: {service_ids}")
            print(f"Found services: {[s.name for s in services]}")
            has_maintenance = any('maintenance' in service.name.lower() for service in services)
            print(f"Has maintenance: {has_maintenance}")
            
            if not has_maintenance:
                raise serializers.ValidationError({
                    "sub_service": _("Sub service can only be set when maintenance service is assigned.")
                })
        
        return attrs

    def create(self, validated_data):
        service_ids = validated_data.pop("service_ids", None)
        user_data = extract_user_data(self.initial_data)
        user_serializer = UserSerializer(data=user_data)
        user_serializer.is_valid(raise_exception=True)
        user = user_serializer.save()
        
        
        
        if service_ids:
            services = Service.objects.filter(pk__in=service_ids)
            if services is None or not services.exists():
                raise serializers.ValidationError({"service_ids": _("Invalid service IDs")})

            provider = Provider.objects.create(user=user, **validated_data)
            provider.services.set(services)

        # Handle driver profile creation if data is present (flat keys or nested)
        driver_profile_data = {}
        # Check for flat keys
        driver_profile_fields = ["license", "status", "is_verified", "documents"]
        for f in driver_profile_fields:
            val = self.initial_data.get(f"driver_profile.{f}")
            print(f"driver_profile.{f}: {val}")
            if val is not None:
                driver_profile_data[f] = val
        # Check for nested dict
        if not driver_profile_data and self.initial_data.get("driver_profile"):
            driver_profile_data = self.initial_data.get("driver_profile")
        if driver_profile_data:
            driver_profile = DriverProfile.objects.create(provider=provider, **driver_profile_data)
            # Handle car creation if data is present (flat keys or nested)
            car_data = {}
            car_fields = ["type", "model", "number", "color", "image"]
            for f in car_fields:
                val = self.initial_data.get(f"car.{f}")
                if val is not None:
                    car_data[f] = val
            if not car_data and self.initial_data.get("car"):
                car_data = self.initial_data.get("car")
            if car_data:
                DriverCar.objects.create(driver_profile=driver_profile, **car_data)

        return provider

    def update(self, instance, validated_data):
        user_data = update_user_data(instance, self.initial_data)
        user_serializer = UserSerializer(instance.user, data=user_data, partial=True)
        user_serializer.is_valid(raise_exception=True)
        user_serializer.save()
        services = validated_data.pop("services", None)
        if services is not None:
            instance.services.set(services)
        return super().update(instance, validated_data)


class DriverProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = DriverProfile
        fields = ["id", "license", "status", "is_verified", "documents"]


class DriverCarSerializer(serializers.ModelSerializer):
    class Meta:
        model = DriverCar
        fields = ["type", "model", "number", "color", "image"]


class CustomerSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = Customer
        fields = ["id", "user", "in_ride"]

    def create(self, validated_data):
        user_data = extract_user_data(self.initial_data)
        user_serializer = UserSerializer(data=user_data)
        user_serializer.is_valid(raise_exception=True)
        user = user_serializer.save()
        return Customer.objects.create(user=user, **validated_data)

    def update(self, instance, validated_data):
        user_data = update_user_data(instance, self.initial_data)
        user_serializer = UserSerializer(instance.user, data=user_data, partial=True)
        user_serializer.is_valid(raise_exception=True)
        user_serializer.save()
        return super().update(instance, validated_data)


class LoginSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=20, write_only=True)
    password = serializers.CharField(max_length=128, write_only=True)
    registration_id = serializers.CharField(max_length=255, write_only=True, required=False)
    device_type = serializers.ChoiceField(choices=["android", "ios"], required=False)
    token = serializers.CharField(max_length=128, read_only=True)
    is_verified = serializers.BooleanField(read_only=True)

    def validate(self, attrs):
        phone = attrs.get("phone")
        password = attrs.get("password")
        registration_id = attrs.get("registration_id")
        device_type = attrs.get("device_type")

        user = User.objects.filter(phone=phone).first()

        if not user:
            raise serializers.ValidationError({"phone": _("Invalid phone")})

        if not user.check_password(password):
            raise serializers.ValidationError({"password": _("Invalid password")})

        if not user.is_active:
            raise serializers.ValidationError({"active": _("User is not active")})

        is_verified = True

        if user.role == ROLE_PROVIDER:
            is_verified = user.provider.is_verified


        if is_verified:
            if registration_id:
                user.fcm_registration_id = registration_id

            if device_type:
                user.device_type = device_type
                
                    
            user.last_login = timezone.now()
            user.save()
            attrs["token"] = Token.objects.get(user=user).key
        else:
            raise serializers.ValidationError({"verified": _("User is not verified")})

        return attrs


class SendOtpSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=20, write_only=True)

    def validate(self, attrs):
        phone = attrs.get("phone")

        user = User.objects.filter(phone=phone).first()

        if not user:
            raise serializers.ValidationError({"phone": _("Invalid phone")})

        otp = send_sms(phone)

        if otp:
            UserOtp.objects.update_or_create(user=user, otp=otp)
        else:
            raise serializers.ValidationError(
                {"sms": _("the sms service is not working try again later")}
            )

        return attrs


class VerifyOtpSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=20, write_only=True)
    otp = serializers.CharField(max_length=20, write_only=True)
    token = serializers.CharField(max_length=128, read_only=True)

    def validate(self, attrs):
        phone = attrs.get("phone")
        otp = attrs.get("otp")

        user = User.objects.filter(phone=phone).first()

        if not user:
            raise serializers.ValidationError({"phone": _("Invalid phone")})

        user_otp = UserOtp.objects.filter(user=user).first()

        if not user_otp or user_otp.otp != otp:
            raise serializers.ValidationError({"otp": _("Invalid otp")})

        if user.role == ROLE_CUSTOMER:
            user.last_login = timezone.now()
            attrs["token"] = Token.objects.get(user=user).key

        user.is_active = True

        user.save()

        return attrs


class ResetPasswordSerializer(serializers.Serializer):
    otp = serializers.CharField(max_length=20, write_only=True)
    password = serializers.CharField(max_length=128, write_only=True)
    confirm_password = serializers.CharField(max_length=128, write_only=True)

    def validate(self, data):
        otp = data.get("otp")
        password = data.get("password")
        confirm_password = data.get("confirm_password")

        if password != confirm_password:
            raise serializers.ValidationError({"password": _("Passwords do not match")})

        user = self.context.get("user")

        user_otp = UserOtp.objects.filter(user=user).first()

        if not user_otp or user_otp.otp != otp:
            raise serializers.ValidationError({"otp": _("Invalid otp")})

        data["user"] = user

        return data

    def save(self):
        user = self.validated_data["user"]

        password = self.validated_data["password"]

        user.set_password(password)

        user.save()

        return user


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    def validate(self, data):
        old_password = data.get("old_password")
        password = data.get("password")
        confirm_password = data.get("confirm_password")

        if password != confirm_password:
            raise serializers.ValidationError(
                {"password": _("Password do not match confirm password")}
            )

        user = self.context.get("user")

        if not user.check_password(old_password):
            raise serializers.ValidationError(
                {"password": _("Old password is incorrect")}
            )

        data["user"] = user

        return data

    def save(self):
        user = self.validated_data["user"]

        password = self.validated_data["password"]

        user.set_password(password)

        user.save()

        return user


class FcmDeviceSerializer(serializers.Serializer):
    registration_id = serializers.CharField(max_length=255, write_only=True)
    device_type = serializers.ChoiceField(
        choices=FCM_CHOICES,
        write_only=True,
    )

    def create(self, validated_data):
        registration_id = validated_data.get("registration_id")
        device_type = validated_data.get("device_type")
        user = self.context.get("user")

        device, created = FCMDevice.objects.update_or_create(
            user=user,
            defaults={
                "registration_id": registration_id,
                "type": device_type,
                "active": True,
            },
        )

        return device


class LogoutSerializer(serializers.Serializer):
    def validate(self, attrs):
        user = self.context.get("user")

        attrs["user"] = user

        return attrs

    def save(self):
        user = self.validated_data["user"]

        device = FCMDevice.objects.get(user=user)

        device.active = False

        return device.save()


class DeleteUserSerializer(serializers.Serializer):
    password = serializers.CharField(max_length=128, write_only=True)

    def validate(self, attrs):
        password = attrs.get("password")

        user = self.context.get("user")

        if not user.check_password(password):
            raise serializers.ValidationError({"password": _("Password is incorrect")})

        return attrs

    def save(self):
        user = self.context.get("user")

        user.auth_token.delete()

        device = FCMDevice.objects.get(user=user)

        device.delete()

        return user.delete()


class CustomerPlaceSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerPlace
        fields = ["id", "title", "location"]

    def create(self, validated_data):
        user = self.context.get("user")
        customer = Customer.objects.get(user=user)
        return CustomerPlace.objects.create(customer=customer, **validated_data)



class RideStatusSerializer(serializers.ModelSerializer):
    client = UserSerializer()
    provider = UserSerializer()
    service = ServiceSerializer()
    service_price_info = serializers.SerializerMethodField()

    class Meta:
        model = RideStatus
        fields = [
            "id",
            "status",
            "client",
            "provider",
            "service",
            "pickup_lat",
            "pickup_lng",
            "drop_lat",
            "drop_lng",
            "created_at",
            "service_price_info",
            "total_price",
            "distance_km",
            "duration_minutes",
            "total_price_before_discount",
        ]

    def get_service_price_info(self, obj):
        if not obj.service:
            return None

        # Handle sub_service only for maintenance service
        sub_service = None
        try:
            if obj.service.name.lower() == "maintenance service":
                sub_service = obj.provider.provider.sub_service
        except AttributeError:
            pass  # Either provider or provider.provider is missing

        try:
            pricing = ProviderServicePricing.get_pricing_for_location(
                service=obj.service,
                sub_service=sub_service,
                lat=obj.pickup_lat,
                lng=obj.pickup_lng,
            )
            if pricing:
                return {
                    "base_fare": float(pricing.base_fare),
                    "price_per_km": float(pricing.price_per_km),
                    "price_per_minute": float(pricing.price_per_minute),
                    "minimum_fare": float(pricing.minimum_fare),
                    "platform_fee": float(pricing.platform_fee),
                    "service_fee": float(pricing.service_fee),
                    "booking_fee": float(pricing.booking_fee),
                    "peak_hour_multiplier": float(pricing.peak_hour_multiplier),
                    "zone": pricing.zone.name if pricing.zone else None,
                }
        except Exception as e:
            print(f"[Service Pricing Error] {e}")
        
        return None

class UserPointsSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserPoints
        fields = ['points']


class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ['id', 'product', 'image']
        read_only_fields = ['product']

class ProductSerializer(serializers.ModelSerializer):
    images = ProductImageSerializer(many=True, read_only=True)
    provider_name = serializers.CharField(source='provider.user.name', read_only=True)
    provider = ProviderSerializer(read_only=True)

    class Meta:
        model = Product
        fields = ['id', 'name', 'description', 'display_price', 'stock', 'is_active', 
                 'created_at', 'updated_at', 'images', 'provider_name', 'provider']
        read_only_fields = ['provider']

    def create(self, validated_data):
        request = self.context.get('request')
        provider = getattr(request.user, 'provider', None)
        validated_data['provider'] = provider
        return Product.objects.create(**validated_data)


class PurchaseSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    customer_name = serializers.CharField(source='customer.user.name', read_only=True)

    class Meta:
        model = Purchase
        fields = ['id', 'product', 'product_name', 'customer_name', 'money_spent', 
                 'quantity', 'status', 'created_at']
        read_only_fields = ['customer', 'money_spent', 'created_at']

    def validate(self, attrs):
        product = attrs.get('product')
        quantity = attrs.get('quantity', 1)
        customer = self.context.get('customer')
        
        # Only check product if present (i.e., on create, not on PATCH)
        if product is not None:
            # Check if product is active
            if not product.is_active:
                raise serializers.ValidationError(_("Product is not available."))
            
            # Check stock
            if product.stock < quantity:
                raise serializers.ValidationError(_("Not enough stock available."))
            
            # Check if customer has enough points
            total_price = product.display_price * quantity
            # user_points = UserPoints.objects.get(user=customer.user)
            
            # if user_points.points < total_points:
            #     raise serializers.ValidationError(_("Not enough points available."))
            
            attrs['money_spent'] = total_price
        return attrs

    def create(self, validated_data):
        customer = self.context.get('customer')
        product = validated_data.get('product')
        quantity = validated_data.get('quantity', 1)
        money_spent = validated_data.get('money_spent')

        # Update stock
        product.stock -= quantity
        if product.stock <= 0:
            product.is_active = False
        product.save()

        # Update customer points
        # user_points = UserPoints.objects.get(user=customer.user)
        # user_points.points -= points_spent
        # user_points.save()

        # Update provider points
        # provider_user = product.provider.user
        # provider_points, _ = UserPoints.objects.get_or_create(user=provider_user)
        # provider_points.points += points_spent
        # provider_points.save()

        return Purchase.objects.create(
            customer=customer,
            product=product,
            quantity=quantity,
            money_spent=money_spent
        )
        
        
class CarAgencySerializer(serializers.ModelSerializer):
    actual_free_times = serializers.SerializerMethodField()

    class Meta:
        model = CarAgency
        fields = '__all__'

    def get_actual_free_times(self, obj):
        from django.utils import timezone
        now = timezone.now()
        # Only include slots that have not ended yet
        slots = obj.availability_slots.filter(end_time__gte=now)
        # Only exclude rentals that are confirmed, in_progress, or completed
        rentals = obj.rentals.filter(status__in=[
            'confirmed', 'in_progress', 'completed'
        ])
        actual = []
        for slot in slots:
            cuts = [(slot.start_time, slot.end_time)]
            for rental in rentals:
                if rental.end_datetime <= slot.start_time or rental.start_datetime >= slot.end_time:
                    continue
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
            for s, e in cuts:
                if s < e:
                    actual.append({'start': s, 'end': e})
        actual.sort(key=lambda x: x['start'])
        return actual


class CarAvailabilitySerializer(serializers.ModelSerializer):
    class Meta:
        model = CarAvailability
        fields = '__all__'



class CarRentalSerializer(serializers.ModelSerializer):
    class Meta:
        model = CarRental
        fields = [
            'id',
            'customer',
            'car',
            'start_datetime',
            'end_datetime',
            'total_price',
            'status',
            'created_at',
        ]
        read_only_fields = ['customer', 'total_price', 'created_at']

    def validate(self, data):
        """
        Custom validation for create + update.
        """
        from django.utils import timezone
        request = self.context['request']
        is_create = self.instance is None

        # 🔑 Always get the car:
        if is_create:
            car = data.get('car')
            if not car:
                raise serializers.ValidationError({"car": "Car is required."})
        else:
            # If updating, get from existing instance
            car = self.instance.car

        start_datetime = data.get('start_datetime', getattr(self.instance, 'start_datetime', None))
        end_datetime = data.get('end_datetime', getattr(self.instance, 'end_datetime', None))

        if is_create and (not start_datetime or not end_datetime):
            raise serializers.ValidationError({"detail": "Start and End are required for new rental."})

        # Only check overlap if dates present
        if start_datetime and end_datetime:
            # 1. Check that the requested time is fully within an available slot
            now = timezone.now()
            available_slots = car.availability_slots.filter(
                start_time__lte=start_datetime,
                end_time__gte=end_datetime
            )
            if not available_slots.exists():
                raise serializers.ValidationError({
                    "detail": "The car is not available for the entire requested time range."
                })

            # 2. Check for overlapping rentals (excluding cancelled)
            overlapping_rentals = CarRental.objects.filter(
                car=car,
                start_datetime__lt=end_datetime,
                end_datetime__gt=start_datetime,
                status__in=["pending", "confirmed", "in_progress", "completed"]
            )
            if self.instance:
                overlapping_rentals = overlapping_rentals.exclude(pk=self.instance.pk)

            if overlapping_rentals.exists():
                raise serializers.ValidationError(
                    {"detail": "This car is already booked in the selected time range."}
                )

        return data


    def create(self, validated_data):
        validated_data['customer'] = self.context['request'].user.customer
        rental = CarRental.objects.create(**validated_data)
        return rental

class ProviderServicePricingSerializer(serializers.ModelSerializer):
    zone_name = serializers.CharField(source='zone.name', read_only=True)
    calculated_price = serializers.SerializerMethodField()
    
    class Meta:
        model = ProviderServicePricing
        fields = [
            "id",
            "service",
            "sub_service",
            "zone",
            "zone_name",
            # Application fees
            "platform_fee",
            "service_fee", 
            "booking_fee",
            # Zone-based fields
            "base_fare",
            "price_per_km",
            "price_per_minute",
            "minimum_fare",
            "peak_hour_multiplier",
            "peak_hours_start",
            "peak_hours_end",
            "is_active",
            "calculated_price",
            "created_at",
            "updated_at"
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def get_calculated_price(self, obj):
        """
        Calculate sample price for display purposes
        """
        # Use sample values: 5km distance, 15 minutes duration
        return obj.calculate_price(distance_km=5, duration_minutes=15)

    def validate_service(self, value):
        allowed_services = [
            "maintenance service",
            "delivery service",
            "car request",
            "food delivery"
        ]
        if value.name.lower() not in allowed_services:
            raise serializers.ValidationError(
                _("Pricing can only be set for maintenance service, delivery service, car request, or food delivery.")
            )
        return value

    def validate(self, attrs):
        attrs = super().validate(attrs)
        service = attrs.get('service')
        sub_service = attrs.get('sub_service')
        if service and service.name.lower() == "maintenance service" and not sub_service:
            raise serializers.ValidationError({
                'sub_service': _("Sub Service is required for maintenance service pricing.")
            })
        if service and service.name.lower() != "maintenance service" and sub_service:
            raise serializers.ValidationError({
                'sub_service': _("Sub Service should only be set for maintenance service pricing.")
            })
        return attrs


class PriceCalculationSerializer(serializers.Serializer):
    """
    Serializer for calculating ride prices
    """
    pickup_lat = serializers.FloatField()
    pickup_lng = serializers.FloatField()
    drop_lat = serializers.FloatField()
    drop_lng = serializers.FloatField()
    service_id = serializers.IntegerField()
    sub_service = serializers.CharField(required=False, allow_blank=True)
    pickup_time = serializers.DateTimeField(required=False)
    
    def validate(self, attrs):
        # Validate service exists
        try:
            service = Service.objects.get(id=attrs['service_id'])
            attrs['service'] = service
        except Service.DoesNotExist:
            raise serializers.ValidationError({'service_id': _('Service not found')})
        
        return attrs


class ProviderDriverRegisterSerializer(serializers.ModelSerializer):
    user = UserSerializer(write_only=True)
    service_ids = serializers.ListField(child=serializers.IntegerField(), write_only=True)
    driver_profile = DriverProfileSerializer(write_only=True)
    car = DriverCarSerializer(write_only=True)

    # Add these two for response
    driver_profile_data = DriverProfileSerializer(source='driverprofile', read_only=True)
    car_data = serializers.SerializerMethodField()

    class Meta:
        model = Provider
        fields = [
            "user", "service_ids", "sub_service", "driver_profile", "car",  # for write
            "driver_profile_data", "car_data"  # for read
        ]

    def get_car_data(self, obj):
        try:
            return DriverCarSerializer(obj.driverprofile.car).data
        except:
            return None

    def validate(self, attrs):
        service_ids = attrs.get('service_ids', [])
        sub_service = attrs.get('sub_service')
        
        if sub_service and service_ids:
            # Check if maintenance service is in the service_ids
            services = Service.objects.filter(pk__in=service_ids)
            has_maintenance = any('maintenance' in service.name.lower() for service in services)
            
            if not has_maintenance:
                raise serializers.ValidationError({
                    "sub_service": _("Sub service can only be set when maintenance service is assigned.")
                })
        
        return attrs

    def create(self, validated_data):
        user_data = validated_data.pop("user")
        service_ids = validated_data.pop("service_ids")
        driver_profile_data = validated_data.pop("driver_profile")
        car_data = validated_data.pop("car")

        user_serializer = UserSerializer(data=user_data)
        user_serializer.is_valid(raise_exception=True)
        user = user_serializer.save()

        provider = Provider.objects.create(user=user, **validated_data)
        
        if service_ids:
            services = Service.objects.filter(pk__in=service_ids)
            provider.services.set(services)

        driver_profile = DriverProfile.objects.create(provider=provider, **driver_profile_data)
        DriverCar.objects.create(driver_profile=driver_profile, **car_data)

        return provider



class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'title', 'message', 'notification_type', 'data', 'is_read', 'created_at']
        read_only_fields = fields


class RatingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rating
        fields = [
            'id',
            'ride',
            'driver_rating',
            'customer_rating',
            'driver_comment',
            'customer_comment',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['ride', 'created_at', 'updated_at']

class ProfileUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating user profile information.
    Allows users to update their name, email, image, and location.
    """
    
    class Meta:
        model = User
        fields = [
            "name",
            "email", 
            "image",
            "location",
        ]
        read_only_fields = ["id", "phone", "role", "average_rating"]

    def validate(self, attrs):
        location_str = attrs.get("location", "")
        
        # Validate location format if provided
        if location_str:
            try:
                lat_val, lng_val = map(float, location_str.split(","))
                # Update location2_lat and location2_lng to match location
                attrs["location2_lat"] = lat_val
                attrs["location2_lng"] = lng_val
            except Exception:
                raise serializers.ValidationError(_("Invalid location format. Use 'latitude,longitude'"))
        
        return attrs

    def update(self, instance, validated_data):
        # Update the user instance
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance


class RideHistorySerializer(serializers.ModelSerializer):
    """
    Serializer for ride history with essential information only.
    """
    client_name = serializers.CharField(source='client.name', read_only=True)
    provider_name = serializers.CharField(source='provider.name', read_only=True)
    service_name = serializers.CharField(source='service.name', read_only=True)
    # total_price = serializers.SerializerMethodField()
    pricing_details = serializers.SerializerMethodField()
    rating = serializers.SerializerMethodField()
    ride_type = serializers.SerializerMethodField()
    
    class Meta:
        model = RideStatus
        fields = [
            "id",
            "client_name",
            "provider_name", 
            "service_name",
            "status",
            "created_at",
            # "total_price",
            "pricing_details",
            "rating",
            "ride_type",
            "total_price",
            "distance_km",
            "duration_minutes",
            "total_price_before_discount"

        ]
        read_only_fields = fields

    def get_total_price(self, obj):
        """Get total price for the ride using zone/location-based pricing"""
        try:
            if obj.service:
                pricing = ProviderServicePricing.get_pricing_for_location(
                    service=obj.service,
                    sub_service=None,
                    lat=obj.pickup_lat,
                    lng=obj.pickup_lng
                )

                if pricing:
                    if all([obj.pickup_lat, obj.pickup_lng, obj.drop_lat, obj.drop_lng]):
                        distance_km = self._calculate_distance(
                            obj.pickup_lat, obj.pickup_lng, obj.drop_lat, obj.drop_lng
                        )
                        duration_minutes = (distance_km / 30) * 60  # estimate
                    else:
                        distance_km = 0
                        duration_minutes = 0

                    return pricing.calculate_price(
                        distance_km=distance_km,
                        duration_minutes=duration_minutes,
                        pickup_time=obj.created_at
                    )

                # Fallback if no zone-based pricing found
                pricing = ProviderServicePricing.objects.filter(
                    service=obj.service,
                    zone__isnull=True,
                    is_active=True
                ).first()

                if pricing:
                    if all([obj.pickup_lat, obj.pickup_lng, obj.drop_lat, obj.drop_lng]):
                        distance_km = self._calculate_distance(
                            obj.pickup_lat, obj.pickup_lng, obj.drop_lat, obj.drop_lng
                        )
                    else:
                        distance_km = 0

                    total_price = (
                        float(pricing.base_fare or 0) +
                        float(pricing.price_per_km or 0) * distance_km +
                        float(pricing.platform_fee or 0) +
                        float(pricing.service_fee or 0) +
                        float(pricing.booking_fee or 0)
                    )
                    return round(max(total_price, float(pricing.minimum_fare or 0)), 2)

        except Exception as e:
            print(f"Error calculating price: {e}")
        return 0

    
    def get_pricing_details(self, obj):
        """Get detailed pricing breakdown based on location"""
        try:
            if obj.service:
                pricing = ProviderServicePricing.get_pricing_for_location(
                    service=obj.service,
                    sub_service=None,
                    lat=obj.pickup_lat,
                    lng=obj.pickup_lng
                )

                if pricing:
                    if all([obj.pickup_lat, obj.pickup_lng, obj.drop_lat, obj.drop_lng]):
                        distance_km = self._calculate_distance(
                            obj.pickup_lat, obj.pickup_lng, obj.drop_lat, obj.drop_lng
                        )
                        duration_minutes = (distance_km / 30) * 60
                    else:
                        distance_km = 0
                        duration_minutes = 0

                    return {
                        "zone_name": pricing.zone.name if pricing.zone else "Default",
                        "base_fare": float(pricing.base_fare),
                        "price_per_km": float(pricing.price_per_km),
                        "price_per_minute": float(pricing.price_per_minute),
                        "distance_km": round(distance_km, 2),
                        "duration_minutes": round(duration_minutes, 2),
                        "minimum_fare": float(pricing.minimum_fare),
                        "peak_hour_multiplier": float(pricing.peak_hour_multiplier),
                    }
        except Exception as e:
            print(f"Error getting pricing details: {e}")
        return None


    def get_rating(self, obj):
        """Get rating for the ride (based on user role)"""
        try:
            if hasattr(obj, 'rating') and obj.rating:
                rating = obj.rating
                request = self.context.get('request')
                if request and request.user:
                    if obj.client == request.user:
                        return rating.customer_rating
                    elif obj.provider == request.user:
                        return rating.driver_rating
        except Exception as e:
            print(f"Error getting rating: {e}")
        return None

    def get_ride_type(self, obj):
        """Determine if the current user is the client or provider in this ride"""
        request = self.context.get('request')
        if request and request.user:
            if obj.client == request.user:
                return "customer"
            elif obj.provider == request.user:
                return "driver"
        return "unknown"

    def _calculate_distance(self, lat1, lon1, lat2, lon2):
        """
        Calculate the great-circle distance in kilometers between two points
        on the Earth specified by latitude and longitude.
        """
        R = 6371.0  # Radius of Earth in kilometers
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        d_phi = math.radians(lat2 - lat1)
        d_lambda = math.radians(lon2 - lon1)

        a = math.sin(d_phi / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        return round(R * c, 2)