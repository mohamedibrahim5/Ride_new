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
    DriverCar
)
from authentication.utils import send_sms, extract_user_data, update_user_data
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework.authtoken.models import Token
from django.utils import timezone
from fcm_django.models import FCMDevice
from django.contrib.gis.geos import Point
from .models import CarAgency, CarAvailability, CarRental, ProductImage


class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    role = serializers.ChoiceField(write_only=True, choices=ROLE_CHOICES)
    location2_lat = serializers.FloatField(required=False, allow_null=True)
    location2_lng = serializers.FloatField(required=False, allow_null=True)

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
            "location2_lng"
        ]



    def validate(self, attrs):
        location_str = attrs.get("location", "")
        lat = attrs.get("location2_lat")
        lng = attrs.get("location2_lng")
        # Accept either lat/lng fields or a comma-separated string in location
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
        fields = ["id", "user", "service_ids", "services"]

    def validate(self, attrs):
        service_ids = attrs.pop("service_ids", None)
        if service_ids is not None:
            services = Service.objects.filter(pk__in=service_ids)
            if len(services) != len(service_ids):
                raise serializers.ValidationError({"services": _(f"Some services not found.")})
            attrs["services"] = services
        return attrs

    def create(self, validated_data):
        user_data = extract_user_data(self.initial_data)
        user_serializer = UserSerializer(data=user_data)
        user_serializer.is_valid(raise_exception=True)
        user = user_serializer.save()
        services = validated_data.pop("services", [])
        provider = Provider.objects.create(user=user, **validated_data)
        provider.services.set(services)
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
        fields = ["id", "license", "status", "is_verified"]


class DriverCarSerializer(serializers.ModelSerializer):
    class Meta:
        model = DriverCar
        fields = ["type", "model", "number", "color", "image", "license"]


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
    token = serializers.CharField(max_length=128, read_only=True)
    is_verified = serializers.BooleanField(read_only=True)

    def validate(self, attrs):
        phone = attrs.get("phone")
        password = attrs.get("password")

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
        ]


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

    class Meta:
        model = Product
        fields = ['id', 'name', 'description', 'display_price', 'stock', 'is_active', 
                 'created_at', 'updated_at', 'images', 'provider_name']
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

class ProviderRegisterSerializer(serializers.ModelSerializer):
    service_ids = serializers.ListField(child=serializers.IntegerField(), write_only=True)
    driver_profile = DriverProfileSerializer(write_only=True)
    car = DriverCarSerializer(write_only=True)
    user = UserSerializer(write_only=True)

    class Meta:
        model = Provider
        fields = ["user", "service_ids", "driver_profile", "car"]

    def create(self, validated_data):
        user_data = validated_data.pop("user")
        service_ids = validated_data.pop("service_ids")
        driver_profile_data = validated_data.pop("driver_profile")
        car_data = validated_data.pop("car")

        user_serializer = UserSerializer(data=user_data)
        user_serializer.is_valid(raise_exception=True)
        user = user_serializer.save()

        provider = Provider.objects.create(user=user)
        provider.services.set(Service.objects.filter(pk__in=service_ids))

        driver_profile = DriverProfile.objects.create(provider=provider, **driver_profile_data)
        DriverCar.objects.create(driver_profile=driver_profile, **car_data)

        return provider