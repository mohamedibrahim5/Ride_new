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
    SubService,
    NameOfCar,
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
    DriverCarImage,
    ScheduledRideRating,
    RestaurantModel,
    WorkingDay, ProductCategory, Product, ProductImage, 
    Cart, CartItem, Order, OrderItem, Coupon, ReviewRestaurant, OfferRestaurant,CouponRestaurant,
    DeliveryAddress,
    ProductImageRestaurant,
    ProductRestaurant
    
)
from authentication.utils import send_sms, extract_user_data, update_user_data
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework.authtoken.models import Token
from django.utils import timezone
from fcm_django.models import FCMDevice
from django.contrib.gis.geos import Point
from django.db.models import Avg
from .models import CarAgency, CarAvailability, CarRental, ProductImage, ScheduledRide, CarPurchase, CarSaleListing, CarSaleImage
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

class SubServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubService
        fields = ["id", "name"]

class NameOfCarSerializer(serializers.ModelSerializer):
    class Meta:
        model = NameOfCar
        fields = ["id", "name"]


class RestaurantModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = RestaurantModel
        fields = ["id", "restaurant_name", "restaurant_id_image", "restaurant_license"]

class ProviderSerializer(serializers.ModelSerializer):
    service_ids = serializers.ListField(
        child=serializers.IntegerField(), write_only=True, required=False
    )
    sub_service_ids = serializers.ListField(
        child=serializers.IntegerField(), write_only=True, required=False
    )
    addCar = serializers.BooleanField(write_only=True, required=False, default=False)
    addRestaurant = serializers.BooleanField(write_only=True, required=False, default=False)
    name_of_car_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)  # Changed to single ID
    user = UserSerializer(read_only=True)
    services = ServiceSerializer(many=True, read_only=True)
    sub_services = SubServiceSerializer(many=True, read_only=True)
    name_of_car = NameOfCarSerializer(read_only=True)  # Changed to singular, for ForeignKey
    driver_profile = serializers.SerializerMethodField(read_only=True)
    car = serializers.SerializerMethodField(read_only=True)
    customer_ratings = serializers.SerializerMethodField(read_only=True)
    customer_ratings_scheduled_rides = serializers.SerializerMethodField(read_only=True)
    restaurant = RestaurantModelSerializer(read_only=True)

    class Meta:
        model = Provider
        fields = [
            "id",
            "user",
            "service_ids",
            "services",
            "sub_service_ids",
            "sub_services",
            "onLine",
            "addCar",
            "name_of_car_id",
            "name_of_car",
            "driver_profile",
            "car",
            "customer_ratings",
            "customer_ratings_scheduled_rides",
            "addRestaurant",
            "restaurant",

        ]

    def validate(self, attrs):
        service_ids = attrs.get("service_ids", None)
        sub_service_ids = attrs.get('sub_service_ids', None)
        name_of_car_id = attrs.get("name_of_car_id", None)
        # requires_driver_profile = service_ids and 5 in service_ids
        # Changed: Check for addCar key instead of service ID 5
        requires_driver_profile = bool(attrs.get("addCar", False)) is True
        requires_restaurant = bool(attrs.get("addRestaurant", False)) is True

        print(f"requires_driver_profile: {requires_driver_profile}")

        # Validate service_ids
        if service_ids:
            try:
                Service.objects.get(pk__in=service_ids)
            except Service.DoesNotExist:
                raise serializers.ValidationError({"service_ids": _("Invalid service IDs")})
        if sub_service_ids:
            try:
                SubService.objects.get(pk__in=sub_service_ids)
            except SubService.DoesNotExist:
                raise serializers.ValidationError({"sub_service_ids": _("Invalid sub service IDs")})
            
        user_data = extract_user_data(self.initial_data)
        phone = user_data.get("phone")
        if phone and User.objects.filter(phone=phone).exists():
            raise serializers.ValidationError({"phone": _("Phone number already exists")})

        # If service ID 5, require driver_profile and car
        if requires_driver_profile:
            if not self.initial_data.get("driver_profile"):
                raise serializers.ValidationError({"driver_profile": _("Driver profile is required")})
            if not self.initial_data.get("car"):
                raise serializers.ValidationError({"car": _("Car is required")}) 
            # validae sending all data of car when service id 5
            if self.initial_data.get("car"):
                car_data = self.initial_data.get("car")
                # validate her type and model and number and color and uploaded_images not null
                if not car_data.get("type") or not car_data.get("model") or not car_data.get("number") or not car_data.get("color") or not car_data.get("uploaded_images"):
                    raise serializers.ValidationError({"car": _("All Car data is required")})

        # add restaurant her and assign it to provider
        if requires_restaurant:
            if not self.initial_data.get("restaurant_name"):
                raise serializers.ValidationError({"restaurant_name": _("Restaurant Name is required")})
            if not self.initial_data.get("restaurant_id_image"):
                raise serializers.ValidationError({"restaurant_id_image": _("Restaurant ID Image is required")})
            if not self.initial_data.get("restaurant_license"):
                raise serializers.ValidationError({"restaurant_license": _("Restaurant License is required")})
            restaurant = RestaurantModel.objects.create(
                restaurant_name=self.initial_data.get("restaurant_name"),
                restaurant_id_image=self.initial_data.get("restaurant_id_image"),
                restaurant_license=self.initial_data.get("restaurant_license")
            )
            attrs['restaurant'] = restaurant


    
            
        # validate driver_profile license
        if self.initial_data.get("driver_profile"):
            license = self.initial_data.get("driver_profile").get("license")
            if license and DriverProfile.objects.filter(license=license).exists():
                raise serializers.ValidationError({"license": _("License number already exists")}) 
            

        # Validate name_of_car_id
        if name_of_car_id is not None:
            try:
                name_of_car = NameOfCar.objects.get(pk=name_of_car_id)
                attrs['name_of_car'] = name_of_car
            except NameOfCar.DoesNotExist:
                raise serializers.ValidationError({"name_of_car_id": _("Invalid Name of Car ID")})
        else:
            attrs['name_of_car'] = None  # Allow null for ForeignKey

        # Validate sub_service
        # if sub_service_ids and service_ids:
        #     services = Service.objects.filter(pk__in=service_ids)
        #     has_maintenance = any('maintenance' in service.name.lower() for service in services)
        #     if not has_maintenance:
        #         raise serializers.ValidationError({
        #             "sub_service": _("Sub service can only be set when maintenance service is assigned.")
        #         })

        

        return attrs

    def create(self, validated_data):
        service_ids = validated_data.pop("service_ids", None)
        sub_service_ids = validated_data.pop("sub_service_ids", None)
        validated_data.pop("addCar", None)
        validated_data.pop("addRestaurant", None)
        name_of_car = validated_data.pop("name_of_car", None)  # Changed to singular
        user_data = extract_user_data(self.initial_data)
        user_serializer = UserSerializer(data=user_data)
        user_serializer.is_valid(raise_exception=True)
        user = user_serializer.save()

        # Create provider with name_of_car (singular)
        provider = Provider.objects.create(user=user, name_of_car=name_of_car, **validated_data)

        # Set services if provided
        if service_ids:
            services = Service.objects.filter(pk__in=service_ids)
            if not services.exists():
                raise serializers.ValidationError({"service_ids": _("Invalid service IDs")})
            provider.services.set(services)
        if sub_service_ids:
            sub_services = SubService.objects.filter(pk__in=sub_service_ids)
            if not sub_services.exists():
                raise serializers.ValidationError({"sub_service_ids": _("Invalid sub service IDs")})
            provider.sub_services.set(sub_services)

        # Handle driver profile creation
        driver_profile_data = {}
        driver_profile_fields = ["license", "status", "is_verified", "documents"]
        for f in driver_profile_fields:
            val = self.initial_data.get(f"driver_profile.{f}")
            if val is not None:
                driver_profile_data[f] = val
        if not driver_profile_data and self.initial_data.get("driver_profile"):
            driver_profile_data = self.initial_data.get("driver_profile")

        if driver_profile_data:
            if isinstance(driver_profile_data.get("documents"), list):
                raise serializers.ValidationError({
                    "documents": "Only one file can be uploaded."
                })
            existing_profile = DriverProfile.objects.filter(license=driver_profile_data.get("license")).first()
            if existing_profile:
                raise serializers.ValidationError({"license": _("License already exists")})
            driver_profile = DriverProfile.objects.create(provider=provider, **driver_profile_data)

            # Handle car creation
            car_data = {}
            car_fields = ["type", "model", "number", "color", "image"]
            for f in car_fields:
                val = self.initial_data.get(f"car.{f}")
                if val is not None:
                    car_data[f] = val
            if not car_data and self.initial_data.get("car"):
                car_data = self.initial_data.get("car")
            if car_data:
                car_serializer = DriverCarSerializer(data=car_data)
                car_serializer.is_valid(raise_exception=True)
                car_serializer.save(driver_profile=driver_profile)

        return provider

    def update(self, validated_data, instance):
        user_data = update_user_data(instance, self.initial_data)
        user_serializer = UserSerializer(instance.user, data=user_data, partial=True)
        user_serializer.is_valid(raise_exception=True)
        user_serializer.save()

        service_ids = validated_data.pop("service_ids", None)
        sub_service_ids = validated_data.pop("sub_service_ids", None)
        validated_data.pop("addCar", None)
        validated_data.pop("addRestaurant", None)
        name_of_car = validated_data.pop("name_of_car", None)  # Changed to singular

        # Update services if provided
        if service_ids is not None:
            services = Service.objects.filter(pk__in=service_ids)
            if not services.exists():
                raise serializers.ValidationError({"service_ids": _("Invalid service IDs")})
            instance.services.set(services)
        if sub_service_ids:
            sub_services = SubService.objects.filter(pk__in=sub_service_ids)
            if not sub_services.exists():
                raise serializers.ValidationError({"sub_service_ids": _("Invalid sub service IDs")})
            instance.sub_services.set(sub_services)

        # Update name_of_car (singular)
        instance.name_of_car = name_of_car

        # Update other fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        return instance

    def get_driver_profile(self, obj):
        try:
            profile = getattr(obj, 'driver_profile', None)
            if not profile:
                return None
            # Importing here avoids forward reference issues at class load time
            return DriverProfileSerializer(profile).data
        except Exception:
            return None

    def get_car(self, obj):
        try:
            profile = getattr(obj, 'driver_profile', None)
            if not profile:
                return None
            car = getattr(profile, 'car', None)
            if not car:
                return None
            return DriverCarSerializer(car).data
        except Exception:
            return None

    def get_customer_ratings(self, obj):
        try:
            # Ratings given by customers about this provider (driver)
            ratings_qs = Rating.objects.filter(
                ride__provider=obj.user,
                customer_rating__isnull=False
            ).select_related('ride__client').order_by('-created_at')

            results = []
            for r in ratings_qs:
                client = r.ride.client if r.ride and r.ride.client_id else None
                results.append({
                    "ride_id": r.ride_id,
                    "client_id": getattr(client, 'id', None),
                    "client_name": getattr(client, 'name', None),
                    "value": r.customer_rating,
                    "comment": r.customer_comment,
                    "created_at": r.created_at,
                })
            return results
        except Exception:
            return []

    def get_customer_ratings_scheduled_rides(self, obj):
        try:
            ratings_qs = ScheduledRideRating.objects.filter(
                ride__provider=obj.user,
                customer_rating__isnull=False
            ).select_related('ride__client').order_by('-created_at')
            results = []
            for r in ratings_qs:
                client = r.ride.client if r.ride and r.ride.client_id else None
                results.append({
                    "ride_id": r.ride_id,
                    "client_id": getattr(client, 'id', None),
                    "client_name": getattr(client, 'name', None),
                    "value": r.customer_rating,
                    "comment": r.customer_comment,
                    "created_at": r.created_at,
                })
            return results
        except Exception:
            return []

class DriverProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = DriverProfile
        fields = ["id", "license", "status", "is_verified", "documents"]
        
    def to_internal_value(self, data):
        # Prevent multi-file upload issue before DRF processes the file field
        documents = data.get('documents')
        if isinstance(documents, list):
            raise serializers.ValidationError({
                "documents": "Only one file can be uploaded."
            })
        return super().to_internal_value(data)


class DriverCarImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = DriverCarImage
        fields = ['id', 'image']
        

from rest_framework.fields import empty

class DriverCarSerializer(serializers.ModelSerializer):
    images = DriverCarImageSerializer(many=True, read_only=True)
    uploaded_images = serializers.ListField(
        child=serializers.ImageField(), write_only=True, required=False
    )

    class Meta:
        model = DriverCar
        fields = ['type', 'model', 'number', 'color', 'images', 'uploaded_images']

    def to_internal_value(self, data):
        uploaded_images = data.get('uploaded_images')
        if uploaded_images and not isinstance(uploaded_images, list):
            if hasattr(data, 'setlist'):
                data.setlist('uploaded_images', [uploaded_images])
            else:
                data['uploaded_images'] = [uploaded_images]
        return super().to_internal_value(data)

    def create(self, validated_data):
        images_data = validated_data.pop('uploaded_images', [])
        car = DriverCar.objects.create(**validated_data)
        for image in images_data:
            DriverCarImage.objects.create(car=car, image=image)
        return car

    def update(self, instance, validated_data):
        images_data = validated_data.pop('uploaded_images', [])
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        for image in images_data:
            DriverCarImage.objects.create(car=instance, image=image)
        return instance



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

        # if user.role == ROLE_CUSTOMER:
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


class CarSaleImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = CarSaleImage
        fields = ['id', 'image']


class CarSaleListingSerializer(serializers.ModelSerializer):
    images = CarSaleImageSerializer(many=True, read_only=True)
    uploaded_images = serializers.ListField(child=serializers.ImageField(), write_only=True, required=False)
    provider = ProviderSerializer(read_only=True)

    class Meta:
        model = CarSaleListing
        fields = [
            'id', 'provider', 'title', 'brand', 'model', 'year', 'mileage_km',
            'transmission', 'fuel_type', 'color', 'price', 'description',
            'is_active', 'is_sold', 'images', 'uploaded_images', 'created_at'
        ]
        read_only_fields = ['provider', 'is_sold', 'created_at']

    def to_internal_value(self, data):
        uploaded_images = data.get('uploaded_images')
        if uploaded_images and not isinstance(uploaded_images, list):
            if hasattr(data, 'setlist'):
                data.setlist('uploaded_images', [uploaded_images])
            else:
                data['uploaded_images'] = [uploaded_images]
        return super().to_internal_value(data)

    def create(self, validated_data):
        images_data = validated_data.pop('uploaded_images', [])
        request = self.context.get('request')
        listing = CarSaleListing.objects.create(provider=request.user.provider, **validated_data)
        for image in images_data:
            CarSaleImage.objects.create(listing=listing, image=image)
        return listing

    def update(self, instance, validated_data):
        images_data = validated_data.pop('uploaded_images', [])
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        for image in images_data:
            CarSaleImage.objects.create(listing=instance, image=image)
        return instance

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
    provider = ProviderSerializer(read_only=True)

    class Meta:
        model = CarAgency
        fields = '__all__'

    def get_provider(self, obj):
        return ProviderSerializer(obj.provider).data

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
    carData = CarAgencySerializer(source='car', read_only=True)
    class Meta:
        model = CarAvailability
        fields = [
            'id',
            'car',
            'carData',
            'start_time',
            'end_time',
        ]



class CarRentalSerializer(serializers.ModelSerializer):
    # Accept car id in requests
    car = serializers.PrimaryKeyRelatedField(queryset=CarAgency.objects.all(), write_only=True)
    # Return nested car details in responses
    car_detail = CarAgencySerializer(source='car', read_only=True)
    customer = CustomerSerializer(read_only=True)

    class Meta:
        model = CarRental
        fields = [
            'id',
            'customer',
            'car',            # write-only PK
            'car_detail',     # read-only nested data
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

        # Get car instance
        car = data.get('car') if is_create else getattr(self.instance, 'car', None)
        if is_create and not car:
            raise serializers.ValidationError({"car": "Car is required."})

        start_datetime = data.get('start_datetime', getattr(self.instance, 'start_datetime', None))
        end_datetime = data.get('end_datetime', getattr(self.instance, 'end_datetime', None))

        if is_create and (not start_datetime or not end_datetime):
            raise serializers.ValidationError({"detail": "Start and End are required for new rental."})

        if start_datetime and end_datetime and car:
            # 1) Ensure requested range is within an available slot
            available_slots = car.availability_slots.filter(
                start_time__lte=start_datetime,
                end_time__gte=end_datetime
            )
            if not available_slots.exists():
                raise serializers.ValidationError({
                    "detail": "The car is not available for the entire requested time range."
                })

            # 2) Ensure no overlapping rentals
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


class CarPurchaseSerializer(serializers.ModelSerializer):
    listing = CarSaleListingSerializer(read_only=True)
    listing_id = serializers.PrimaryKeyRelatedField(source='listing', queryset=CarSaleListing.objects.filter(is_active=True, is_sold=False), write_only=True)
    customer = CustomerSerializer(read_only=True)

    class Meta:
        model = CarPurchase
        fields = [
            'id',
            'customer',
            'listing',
            'listing_id',
            'price',
            'status',
            'created_at',
        ]
        read_only_fields = ['customer', 'price', 'created_at']

    def validate(self, attrs):
        listing = attrs.get('listing') if 'listing' in attrs else getattr(self.instance, 'listing', None)
        if not listing:
            raise serializers.ValidationError({'listing_id': _('Listing is required.')})
        if not listing.is_active or listing.is_sold:
            raise serializers.ValidationError({'listing_id': _('This listing is not available for purchase.')})
        # Prevent duplicate or conflicting purchases
        request = self.context.get('request')
        customer = getattr(getattr(request, 'user', None), 'customer', None)
        if customer:
            # Has this customer already created a non-cancelled purchase for this listing?
            exists_for_customer = CarPurchase.objects.filter(
                listing=listing,
                customer=customer,
                status__in=[CarPurchase.STATUS_PENDING, CarPurchase.STATUS_CONFIRMED, CarPurchase.STATUS_COMPLETED]
            )
            if self.instance:
                exists_for_customer = exists_for_customer.exclude(pk=self.instance.pk)
            if exists_for_customer.exists():
                raise serializers.ValidationError({'listing_id': _('You have already placed a purchase for this listing.')})

        # Is there any active purchase for this listing (by anyone) that would block new one?
        conflicting = CarPurchase.objects.filter(
            listing=listing,
            status__in=[CarPurchase.STATUS_PENDING, CarPurchase.STATUS_CONFIRMED, CarPurchase.STATUS_COMPLETED]
        )
        if self.instance:
            conflicting = conflicting.exclude(pk=self.instance.pk)
        if conflicting.exists():
            raise serializers.ValidationError({'listing_id': _('This listing already has an active purchase and cannot be bought again.')})
        attrs['price'] = listing.price
        return attrs

    def create(self, validated_data):
        request = self.context.get('request')
        validated_data['customer'] = request.user.customer
        return CarPurchase.objects.create(**validated_data)

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
        # if value.name.lower() not in allowed_services:
        #     raise serializers.ValidationError(
        #         _("Pricing can only be set for maintenance service, delivery service, car request, or food delivery.")
        #     )
        return value

    def validate(self, attrs):
        attrs = super().validate(attrs)
        service = attrs.get('service')
        sub_service = attrs.get('sub_service')
        if service and service.name.lower() == "maintenance service" and not sub_service:
            raise serializers.ValidationError({
                'sub_service': _("Sub Service is required for maintenance service pricing.")
            })
        # if service and service.name.lower() != "maintenance service" and sub_service:
        #     raise serializers.ValidationError({
        #         'sub_service': _("Sub Service should only be set for maintenance service pricing.")
        #     })
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
    driver_profile_data = DriverProfileSerializer(source='driver_profile', read_only=True)
    car_data = serializers.SerializerMethodField()

    class Meta:
        model = Provider
        fields = [
            "user", "service_ids", "sub_service", "driver_profile", "car",  # for write
            "driver_profile_data", "car_data"  # for read
        ]

    def get_car_data(self, obj):
        try:
            return DriverCarSerializer(obj.driver_profile.car).data
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

        # Create user
        user_serializer = UserSerializer(data=user_data)
        user_serializer.is_valid(raise_exception=True)
        user = user_serializer.save()

        # Create provider
        provider = Provider.objects.create(user=user, **validated_data)

        # Set services
        if service_ids:
            services = Service.objects.filter(pk__in=service_ids)
            provider.services.set(services)

        existing_profile = DriverProfile.objects.filter(license=driver_profile_data.get("license")).first()
        if existing_profile:
            raise serializers.ValidationError({"license": _("License already exists")})     

        # Create driver profile
        driver_profile = DriverProfile.objects.create(provider=provider, **driver_profile_data)

        # ✅ Create car using serializer to handle uploaded_images
        car_serializer = DriverCarSerializer(data=car_data)
        car_serializer.is_valid(raise_exception=True)
        car_serializer.save(driver_profile=driver_profile)

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


class ProviderOnlineStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Provider
        fields = ['onLine']


class ScheduledRideSerializer(serializers.ModelSerializer):
    client_name = serializers.CharField(source='client.name', read_only=True)
    provider_name = serializers.CharField(source='provider.name', read_only=True)
    service_name = serializers.CharField(source='service.name', read_only=True)
    sub_service_name = serializers.CharField(source='sub_service.name', read_only=True)

    class Meta:
        model = ScheduledRide
        fields = [
            'id', 'client', 'client_name', 'provider', 'provider_name', 'service', 'service_name',
            'sub_service', 'sub_service_name',
            'pickup_lat', 'pickup_lng', 'drop_lat', 'drop_lng', 'scheduled_time', 'status', 
            'total_price', 'distance_km', 'duration_minutes', 'created_at'
        ]
        read_only_fields = ['client', 'status', 'created_at', 'total_price', 'distance_km', 'duration_minutes']

    def validate(self, attrs):
        attrs = super().validate(attrs)
        from django.utils import timezone
        scheduled_time = attrs.get('scheduled_time')
        provider = attrs.get('provider')
        request = self.context.get('request')

        if not scheduled_time or scheduled_time <= timezone.now():
            raise serializers.ValidationError({'scheduled_time': _('Scheduled time must be in the future.')})

        # Check user doesn't have more than 3 active scheduled rides
        if request and request.user:
            active_rides_count = ScheduledRide.objects.filter(
                client=request.user,
                status__in=[ScheduledRide.STATUS_ACCEPTED, ScheduledRide.STATUS_STARTED]
            ).count()
            if active_rides_count >= 3:
                raise serializers.ValidationError({
                    'scheduled_time': _('You cannot have more than 3 active scheduled rides. Please cancel or complete existing rides first.')
                })

        if provider:
            # Ensure provider is a provider user
            if not hasattr(provider, 'provider'):
                raise serializers.ValidationError({'provider': _('Selected user is not a provider.')})
            # Check provider has no conflicting accepted scheduled ride within 1 hour window
            window_start = scheduled_time - timezone.timedelta(minutes=60)
            window_end = scheduled_time + timezone.timedelta(minutes=60)
            conflict = ScheduledRide.objects.filter(
                provider=provider,
                status__in=[ScheduledRide.STATUS_ACCEPTED, ScheduledRide.STATUS_STARTED],
                scheduled_time__range=(window_start, window_end)
            ).exists()
            if conflict:
                raise serializers.ValidationError({'provider': _('Provider is not available around this time.')})

        return attrs

    def create(self, validated_data):
        request = self.context.get('request')
        validated_data['client'] = request.user
        
        # Calculate price, distance, and duration
        service = validated_data.get('service')
        sub_service = validated_data.get('sub_service')
        pickup_lat = validated_data.get('pickup_lat')
        pickup_lng = validated_data.get('pickup_lng')
        drop_lat = validated_data.get('drop_lat')
        drop_lng = validated_data.get('drop_lng')
        
        if service and pickup_lat and pickup_lng:
            # Calculate distance and duration
            distance_km = 0
            duration_minutes = 0
            
            if drop_lat and drop_lng:
                # Calculate distance between pickup and drop
                distance_km = self._calculate_distance(pickup_lat, pickup_lng, drop_lat, drop_lng)
            else:
                # For one-way rides, use a default distance or calculate from user location
                user_location_lat = request.user.location2_lat
                user_location_lng = request.user.location2_lng
                if user_location_lat and user_location_lng:
                    distance_km = self._calculate_distance(pickup_lat, pickup_lng, user_location_lat, user_location_lng)
            
            duration_minutes = (distance_km / 30) * 60  # Assuming 30 km/h average speed
            
            # Get pricing for the service and location
            print(f"Service: {service}, Sub Service: {sub_service}")
            pricing = ProviderServicePricing.get_pricing_for_location(
                service=service,
                sub_service=sub_service,
                lat=pickup_lat,
                lng=pickup_lng
            )
            
            if pricing:
                total_price = pricing.calculate_price(
                    distance_km=distance_km,
                    duration_minutes=duration_minutes,
                    pickup_time=validated_data.get('scheduled_time')
                )
                validated_data['total_price'] = total_price
                validated_data['distance_km'] = distance_km
                validated_data['duration_minutes'] = duration_minutes
            else :
                raise serializers.ValidationError({'pricing': _('Pricing of this service is not found.')})
        
        return ScheduledRide.objects.create(**validated_data)
    
    def _calculate_distance(self, lat1, lon1, lat2, lon2):
        """Calculate distance between two points in kilometers"""
        import math
        R = 6371.0  # Radius of Earth in kilometers
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        d_phi = math.radians(lat2 - lat1)
        d_lambda = math.radians(lon2 - lon1)

        a = math.sin(d_phi / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        return round(R * c, 2)


class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ['id','image','alt_text','is_primary','created_at']

class ProductSerializer(serializers.ModelSerializer):
    images = ProductImageSerializer(many=True, required=False)
    class Meta:
        model = Product
        fields = ['id','category','name','description','display_price','stock','is_offer','is_active','images','created_at','updated_at']
    
    def create(self, validated_data):
        images_data = validated_data.pop('images', [])
        product = Product.objects.create(**validated_data)
        for img_data in images_data:
            ProductImage.objects.create(product=product, **img_data)
        return product

    def update(self, instance, validated_data):
        images_data = validated_data.pop('images', None)

        # Update basic fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if images_data is not None:
            # Delete old images if client sends new ones
            instance.images.all().delete()
            for img_data in images_data:
                ProductImage.objects.create(product=instance, **img_data)

        return instance







class ProductImageRestaurantSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImageRestaurant
        fields = ['id','product','image','alt_text','is_primary','created_at']
        read_only_fields = ['product']
        extra_kwargs = {
            'alt_text': {'required': False, 'allow_blank': True},
        }


        
class ProductRestaurantSerializer(serializers.ModelSerializer):
    images = ProductImageRestaurantSerializer(many=True, read_only=True, source='images_restaurant')
    uploaded_images = serializers.ListField(child=serializers.ImageField(), write_only=True, required=False)
    class Meta:
        model = ProductRestaurant
        fields = ['id','category','name','description','display_price','stock','is_offer','is_active','created_at','updated_at','images','uploaded_images']

    def to_internal_value(self, data):
        # Map form-data 'images' (list of files) → 'uploaded_images'
        try:
            incoming = data.get('images') if hasattr(data, 'get') else None
            if incoming:
                # If a single file, normalize to list
                if not isinstance(incoming, list):
                    if hasattr(data, 'setlist'):
                        data.setlist('uploaded_images', [incoming])
                    else:
                        data = data.copy() if hasattr(data, 'copy') else data
                        data['uploaded_images'] = [incoming]
                else:
                    # Already a list of files
                    if hasattr(data, 'setlist'):
                        data.setlist('uploaded_images', incoming)
                    else:
                        data = data.copy() if hasattr(data, 'copy') else data
                        data['uploaded_images'] = incoming
                # Remove original images key to avoid type errors
                if hasattr(data, 'pop'):
                    data.pop('images', None)

            # Also support bracketed keys images[0][image]
            if hasattr(data, 'getlist'):
                collected = []
                for key in list(data.keys()):
                    if isinstance(key, str) and key.startswith('images[') and key.endswith('][image]'):
                        f = data.get(key)
                        if f:
                            collected.append(f)
                if collected:
                    existing = data.get('uploaded_images') if hasattr(data, 'get') else None
                    if existing and isinstance(existing, list):
                        collected = existing + collected
                    if hasattr(data, 'setlist'):
                        data.setlist('uploaded_images', collected)
                    else:
                        data = data.copy() if hasattr(data, 'copy') else data
                        data['uploaded_images'] = collected
        except Exception:
            pass
        return super().to_internal_value(data)

    def create(self, validated_data):
        images_files = validated_data.pop('uploaded_images', [])
        product = ProductRestaurant.objects.create(**validated_data)
        for f in images_files:
            ProductImageRestaurant.objects.create(product=product, image=f, alt_text='', is_primary=False)
        return product

    def update(self, instance, validated_data):
        images_files = validated_data.pop('uploaded_images', [])
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        for f in images_files:
            ProductImageRestaurant.objects.create(product=instance, image=f, alt_text='', is_primary=False)
        return instance
        


class CategorySerializer(serializers.ModelSerializer):
    products = ProductRestaurantSerializer(many=True, read_only=True)
    class Meta:
        model = ProductCategory
        fields = ['id','restaurant','name','products']

class WorkingDaySerializer(serializers.ModelSerializer):
    day_name = serializers.CharField(source='get_day_of_week_display', read_only=True)
    
    class Meta:
        model = WorkingDay
        fields = ['id','restaurant','day_of_week','day_name','opening_time','closing_time']
        




class RestaurantSerializer(serializers.ModelSerializer):
    categories = CategorySerializer(many=True, read_only=True)
    offers = serializers.SerializerMethodField()
    reviews_count = serializers.SerializerMethodField()
    working_days = WorkingDaySerializer(many=True, required=False)
    provider_id = serializers.IntegerField(source='provider.id', read_only=True)
    provider_name = serializers.CharField(source='provider.user.name', read_only=True)
    
    class Meta:
        model = RestaurantModel
        fields = ['id','restaurant_name','restaurant_id_image','restaurant_description','phone','email','address','latitude','longitude','is_verified','average_rating','menu_link','categories','offers','reviews_count','provider_id','provider_name','working_days','restaurant_license']
        read_only_fields = ['provider']
    
    def to_internal_value(self, data):
        # Handle form data for working_days
        if hasattr(data, 'getlist'):
            # This is form data
            working_days_data = []
            days = data.getlist('working_days[day]')
            open_times = data.getlist('working_days[open_time]')
            close_times = data.getlist('working_days[close_time]')
            
            print(f"DEBUG: Found {len(days)} days, {len(open_times)} open_times, {len(close_times)} close_times")
            print(f"DEBUG: Days: {days}")
            print(f"DEBUG: Open times: {open_times}")
            print(f"DEBUG: Close times: {close_times}")
            
            for i, day in enumerate(days):
                if i < len(open_times) and i < len(close_times):
                    # Convert day name to day_of_week integer
                    day_mapping = {
                        'Monday': 2, 'Tuesday': 3, 'Wednesday': 4, 'Thursday': 5,
                        'Friday': 6, 'Saturday': 0, 'Sunday': 1
                    }
                    day_of_week = day_mapping.get(day, 2)  # Default to Monday
                    
                    working_days_data.append({
                        'day_of_week': day_of_week,
                        'opening_time': open_times[i],
                        'closing_time': close_times[i]
                    })
            
            print(f"DEBUG: Working days data: {working_days_data}")
            
            # Create a mutable copy of data without file objects
            data_copy = {}
            for key, value in data.items():
                if key != 'working_days':  # Skip working_days as we'll add it separately
                    data_copy[key] = value
            data_copy['working_days'] = working_days_data
            return super().to_internal_value(data_copy)
        
        return super().to_internal_value(data)
    
    def create(self, validated_data):
        print(f"DEBUG: Create method called with validated_data: {validated_data}")
        
        # Handle working_days from initial_data if not in validated_data
        working_days_data = validated_data.pop('working_days', [])
        print(f"DEBUG: Working days from validated_data: {working_days_data}")
        
        # If no working_days in validated_data, try to get from initial_data
        if not working_days_data and hasattr(self, 'initial_data'):
            initial_data = self.initial_data
            print(f"DEBUG: Initial data keys: {list(initial_data.keys()) if hasattr(initial_data, 'keys') else 'No keys method'}")
            print(f"DEBUG: Initial data type: {type(initial_data)}")
            
            # Check if working_days is sent as JSON string
            working_days_json = initial_data.get('working_days')
            print(f"DEBUG: Working days JSON string: {working_days_json}")
            print(f"DEBUG: Working days JSON type: {type(working_days_json)}")
            
            if working_days_json:
                try:
                    import json
                    working_days_list = json.loads(working_days_json)
                    print(f"DEBUG: Working days JSON parsed: {working_days_list}")
                    
                    for wd in working_days_list:
                        # Convert day name to day_of_week integer
                        day_mapping = {
                            'Monday': 2, 'Tuesday': 3, 'Wednesday': 4, 'Thursday': 5,
                            'Friday': 6, 'Saturday': 0, 'Sunday': 1
                        }
                        day_of_week = day_mapping.get(wd.get('day'), 2)  # Default to Monday
                        
                        working_days_data.append({
                            'day_of_week': day_of_week,
                            'opening_time': wd.get('open_time'),
                            'closing_time': wd.get('close_time')
                        })
                    
                    print(f"DEBUG: Converted working days data: {working_days_data}")
                    
                except json.JSONDecodeError as e:
                    print(f"DEBUG: JSON decode error: {e}")
                    pass
            
            # Fallback to old format (separate fields)
            elif hasattr(initial_data, 'getlist'):
                # This is form data
                days = initial_data.getlist('working_days[day]')
                open_times = initial_data.getlist('working_days[open_time]')
                close_times = initial_data.getlist('working_days[close_time]')
                
                print(f"DEBUG: Found {len(days)} days, {len(open_times)} open_times, {len(close_times)} close_times")
                print(f"DEBUG: Days: {days}")
                print(f"DEBUG: Open times: {open_times}")
                print(f"DEBUG: Close times: {close_times}")
                
                for i, day in enumerate(days):
                    if i < len(open_times) and i < len(close_times):
                        # Convert day name to day_of_week integer
                        day_mapping = {
                            'Monday': 2, 'Tuesday': 3, 'Wednesday': 4, 'Thursday': 5,
                            'Friday': 6, 'Saturday': 0, 'Sunday': 1
                        }
                        day_of_week = day_mapping.get(day, 2)  # Default to Monday
                        
                        working_days_data.append({
                            'day_of_week': day_of_week,
                            'opening_time': open_times[i],
                            'closing_time': close_times[i]
                        })
                
                print(f"DEBUG: Working days data: {working_days_data}")
        
        restaurant = super().create(validated_data)
        for wd in working_days_data:
            WorkingDay.objects.create(restaurant=restaurant, **wd)
        return restaurant

    def update(self, instance, validated_data):
        working_days_data = validated_data.pop('working_days', None)
        instance = super().update(instance, validated_data)
        if working_days_data is not None:
            instance.working_days.all().delete()
            for wd in working_days_data:
                WorkingDay.objects.create(restaurant=instance, **wd)
        return instance

    def get_offers(self, obj):
        now = timezone.now()
        offers = obj.offers.filter(active=True, valid_from__lte=now, valid_to__gte=now)
        return OfferSerializer(offers, many=True).data

    def get_reviews_count(self, obj):
        return obj.reviews.count()

class CartItemSerializer(serializers.ModelSerializer):
    product = ProductRestaurantSerializer(read_only=True)
    product_id = serializers.PrimaryKeyRelatedField(write_only=True, queryset=ProductRestaurant.objects.all(), source='product')
    class Meta:
        model = CartItem
        fields = ['id','cart','product','product_id','quantity']

class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    total = serializers.SerializerMethodField()
    class Meta:
        model = Cart
        fields = ['id','customer','created_at','items','total']
    def get_total(self, obj):
        return obj.total_price()

class OrderItemSerializer(serializers.ModelSerializer):
    product = ProductRestaurantSerializer(read_only=True)
    product_id = serializers.PrimaryKeyRelatedField(write_only=True, queryset=ProductRestaurant.objects.all(), source='product')
    class Meta:
        model = OrderItem
        fields = ['id','order','product','product_id','quantity','price']

class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True)

    class Meta:
        model = Order
        fields = [
            'id', 'customer', 'restaurant', 'driver',
            'total_price', 'discount', 'final_price',
            'status', 'payment_method',
            'expected_order_time', 'created_at', 'items'
        ]

    def create(self, validated_data):
        items_data = validated_data.pop('items')
        order = Order.objects.create(**validated_data)
        for it in items_data:
            OrderItem.objects.create(
                order=order,
                product=it['product'],
                quantity=it['quantity'],
                price=it['price']
            )
        order.recalc_prices()
        return order


class CouponRestaurantSerializer(serializers.ModelSerializer):
    class Meta:
        model = CouponRestaurant
        fields = ['id','code','discount_percentage','valid_from','valid_to','active']

class ReviewSerializer(serializers.ModelSerializer):
    customer = serializers.PrimaryKeyRelatedField(read_only=True, default=serializers.CurrentUserDefault())
    class Meta:
        model = ReviewRestaurant
        fields = ['id','customer','restaurant','rating','comment','created_at']

class OfferSerializer(serializers.ModelSerializer):
    class Meta:
        model = OfferRestaurant
        fields = ['id','restaurant','title','description','discount_percentage','valid_from','valid_to','active']

class DeliveryAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryAddress
        fields = ['id','customer','address','latitude','longitude','is_default']
        read_only_fields = ['customer']
