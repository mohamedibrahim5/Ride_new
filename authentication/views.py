from authentication.filters import ProviderFilter
from authentication.models import (
    Provider,
    Customer,
    Service,
    DriverProfile,
    DriverCar,
    CustomerPlace,
    Product,
    Purchase,
    UserPoints,
    CarAgency, 
    CarAvailability, 
    CarRental,
    Notification,
    Rating,
    ProviderServicePricing,
    PricingZone
)
from authentication.serializers import (
    UserSerializer,
    LoginSerializer,
    SendOtpSerializer,
    VerifyOtpSerializer,
    ResetPasswordSerializer,
    ChangePasswordSerializer,
    ProviderSerializer,
    CustomerSerializer,
    FcmDeviceSerializer,
    LogoutSerializer,
    DeleteUserSerializer,
    ServiceSerializer,
    DriverCarSerializer,
    CustomerPlaceSerializer,
    ProductSerializer,
    PurchaseSerializer,
    UserPointsSerializer,
    CarAgencySerializer,
    CarAvailabilitySerializer,
    CarRentalSerializer,
    DriverProfileSerializer,
    ProductImageSerializer,
    ProviderDriverRegisterSerializer,
    NotificationSerializer,
    RatingSerializer,
    ProviderServicePricingSerializer,
    ProfileUpdateSerializer,
    ProviderDriverRegisterSerializer,
    PricingZoneSerializer,
    RideHistorySerializer,
    PriceCalculationSerializer
)
from authentication.choices import ROLE_CUSTOMER, ROLE_PROVIDER
from authentication.permissions import IsAdminOrReadOnly, IsCustomer, IsCustomerOrAdmin, IsAdminOrCarAgency, IsStoreProvider, IsAdminOrOwnCarAgency, ProductImagePermission
from rest_framework import status, generics, viewsets, filters
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from django.db import models
from .pagination import SimplePagination
from django.core.cache import cache
import math
import random
import string
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.utils.dateparse import parse_datetime
from rest_framework import serializers
from django.http import Http404
from django.db.models import Avg
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from collections import defaultdict
import json
from authentication.signals import set_request_data
from .utils import send_fcm_notification
from django.core.cache import cache

import json
from collections import defaultdict
from django.http import QueryDict
from django.core.files.uploadedfile import UploadedFile


import json
from django.http import QueryDict
from django.core.files.uploadedfile import UploadedFile


def flatten_form_data(data):
    """
    Safely flattens dot-notated keys into nested dictionaries.
    Handles list fields (e.g., service_ids) and file uploads (e.g., uploaded_images) correctly.
    """
    result = {}

    # Required to preserve all keys (even duplicates like uploaded_images)
    keys = list(dict.fromkeys(data.keys())) if isinstance(data, QueryDict) else data.keys()

    for key in keys:
        # Handle multiple values (like images[] or repeated fields)
        values = data.getlist(key) if isinstance(data, QueryDict) else [data[key]]

        # Special handling for 'uploaded_images': treat as raw files
        if key.endswith("uploaded_images"):
            final_value = values if len(values) > 1 else values[0]
        
        # Handle keys like service_ids that should be a list of integers
        elif key in ["service_ids"]:
            if len(values) == 1:
                # Try to parse JSON string like "[1, 2]"
                try:
                    parsed = json.loads(values[0])
                    if isinstance(parsed, list):
                        final_value = parsed
                    else:
                        final_value = [int(values[0])]
                except Exception:
                    final_value = [int(values[0])]
            else:
                final_value = [int(v) for v in values]

        # Handle everything else normally
        else:
            # If only one value and it's a JSON string list, parse it
            if len(values) == 1 and isinstance(values[0], str):
                try:
                    parsed = json.loads(values[0])
                    values = parsed if isinstance(parsed, list) else [parsed]
                except Exception:
                    pass
            final_value = values if len(values) > 1 else values[0]

        # Handle nested keys like "car.uploaded_images" → {"car": {"uploaded_images": [...]} }
        if "." in key:
            parts = key.split(".")
            current = result
            for part in parts[:-1]:
                current = current.setdefault(part, {})
            current[parts[-1]] = final_value
        else:
            result[key] = final_value

    return result





class UserRegisterView(generics.CreateAPIView):
    def get_serializer_class(self):
        role = self.request.data.get("role") 
        has_nested_user = (
            any(k.startswith("user.") for k in self.request.data.keys()) or
            isinstance(self.request.data.get("user"), dict)
        )
        if role == "CU":
            return CustomerSerializer
        elif role == "PR":
            if has_nested_user:
                return ProviderDriverRegisterSerializer
            return ProviderSerializer
        return UserSerializer

    def post(self, request, *args, **kwargs):
        # Only flatten if the request is form-data
        if request.content_type.startswith("multipart/form-data") or request.content_type.startswith("application/x-www-form-urlencoded"):
            data = flatten_form_data(request.data)
        else:
            data = request.data  # already JSON
        # Set thread local for signals
        set_request_data(data)
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        # Custom: include driver_profile and car in response if they exist
        provider = None
        if hasattr(serializer, 'instance') and serializer.instance:
            provider = serializer.instance
        elif hasattr(serializer, 'data') and 'id' in serializer.data:
            from authentication.models import Provider
            try:
                provider = Provider.objects.get(id=serializer.data['id'])
            except Exception:
                provider = None
        response_data = serializer.data
        if provider:
            # Try to get driver profile and car
            driver_profile = getattr(provider, 'driver_profile', None)
            if driver_profile:
                from authentication.serializers import DriverProfileSerializer, DriverCarSerializer
                response_data['driver_profile'] = DriverProfileSerializer(driver_profile).data
                car = getattr(driver_profile, 'car', None)
                if car:
                    response_data['car'] = DriverCarSerializer(car).data
        return Response(response_data, status=status.HTTP_201_CREATED, headers=headers)

class LoginView(generics.GenericAPIView):
    serializer_class = LoginSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class SendOtpView(generics.GenericAPIView):
    serializer_class = SendOtpSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class VerifyOtpView(generics.GenericAPIView):
    serializer_class = VerifyOtpSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ResetPasswordView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ResetPasswordSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(
            data=request.data, context={"user": self.request.user}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)


class ChangePasswordView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ChangePasswordSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(
            data=request.data, context={"user": self.request.user}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)


from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Q

from authentication.models import RideStatus, User, Customer, Provider
from authentication.serializers import (
    CustomerSerializer,
    ProviderSerializer,
    UserSerializer,
    ServiceSerializer,
)
from authentication.serializers import RideStatusSerializer  # Create this serializer (see below)


class ProfileUserView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated]

    def get_object(self):
        user = self.request.user
        role = user.role

        # Get the current active ride if exists
        current_ride = RideStatus.objects.filter(
            Q(client=user) | Q(provider=user),
            status__in=["pending", "accepted", "starting", "arriving"]
        ).select_related("client", "provider", "service").first()

        # Update user's in_ride field
        if role == "CU" and hasattr(user, "customer"):
            user.customer.in_ride = bool(current_ride)
            user.customer.save()
            self.request._user_object = user.customer
        elif role == "DR" and hasattr(user, "driver"):
            user.driver.in_ride = bool(current_ride)
            user.driver.save()
            self.request._user_object = user.driver
        elif role == "PR" and hasattr(user, "provider"):
            user.provider.in_ride = bool(current_ride)
            user.provider.save()
            self.request._user_object = user.provider
        else:
            self.request._user_object = user  # fallback

        self.request.current_ride = current_ride
        return self.request._user_object

    def get_serializer_class(self):
        role = self.request.user.role

        if role == "CU":
            return CustomerSerializer
        elif role == "DR":
            return ProviderSerializer
        elif role == "PR":
            return ProviderSerializer
        return UserSerializer

    def retrieve(self, request, *args, **kwargs):
        response = super().retrieve(request, *args, **kwargs)
        current_ride = getattr(request, "current_ride", None)
        user = request.user
        
        # Determine user type
        if hasattr(user, "customer"):
            response.data["user_type"] = "customer"

        elif hasattr(user, "provider"):
            response.data["user_type"] = "provider"
            provider = user.provider
            if hasattr(provider, "provider_type"):
                response.data["provider_type"] = provider.provider_type
            else:
                response.data["provider_type"] = None

        else:
            response.data["user_type"] = "user"            
            
                

        if current_ride:
            response.data["in_ride"] = True
            response.data["current_ride"] = RideStatusSerializer(current_ride).data
        else:
            response.data["in_ride"] = False
            response.data["current_ride"] = None

        return response


class FcmDeviceView(generics.CreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = FcmDeviceSerializer

    def get_serializer_context(self):
        return {"user": self.request.user}


class LogoutView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = LogoutSerializer

    def get_serializer_context(self):
        return {"user": self.request.user}

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_204_NO_CONTENT)


class DeleteUserView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = DeleteUserSerializer

    def get_serializer_context(self):
        return {"user": self.request.user}

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_204_NO_CONTENT)


class ServiceViewSet(viewsets.ModelViewSet):
    queryset = Service.objects.all()
    serializer_class = ServiceSerializer
    permission_classes = [IsAdminOrReadOnly]


class DriverProfileViewSet(viewsets.ModelViewSet):
    queryset = DriverProfile.objects.select_related("provider__user")
    serializer_class = DriverProfileSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        provider = getattr(self.request.user, 'provider', None)
        if not provider:
            raise serializers.ValidationError({'provider': 'Current user is not a provider.'})
        serializer.save(provider=provider)


class DriverCarViewSet(viewsets.ModelViewSet):
    queryset = DriverCar.objects.select_related("driver_profile__provider__user")
    serializer_class = DriverCarSerializer
    permission_classes = [IsAuthenticated]

    def get_serializer_context(self):
        return super().get_serializer_context() | {"user": self.request.user}

    def perform_create(self, serializer):
        provider = getattr(self.request.user, 'provider', None)
        if not provider or not hasattr(provider, 'driver_profile'):
            raise serializers.ValidationError({'driver_profile': 'Current user does not have a driver profile.'})
        serializer.save(driver_profile=provider.driver_profile)


class CustomerPlaceViewSet(viewsets.ModelViewSet):
    queryset = CustomerPlace.objects.select_related("customer__user")
    serializer_class = CustomerPlaceSerializer
    permission_classes = [IsAuthenticated]

    def get_serializer_context(self):
        return super().get_serializer_context() | {"user": self.request.user}


class ProviderViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = ProviderSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = ProviderFilter

    def get_queryset(self):
        service_id = self.request.query_params.get("service_id")
        sub_service = self.request.query_params.get("sub_service")
        
        print(f"Debug - service_id: {service_id}, sub_service: {sub_service}")
        
        # First, let's see all providers with maintenance service
        all_maintenance_providers = Provider.objects.filter(
            services__name__icontains='maintenance'
        ).select_related("user")
        print(f"All maintenance providers: {all_maintenance_providers.count()}")
        for p in all_maintenance_providers:
            print(f"  Provider: {p.user.name}, sub_service: '{p.sub_service}', verified: {p.is_verified}")
        
        queryset = Provider.objects.filter(
            services__id=service_id,
            is_verified=True,
        ).select_related("user")
        
        print(f"Providers with service_id {service_id} and verified: {queryset.count()}")
        
        # Filter by sub_service if provided and service is maintenance
        if sub_service and service_id:
            try:
                service = Service.objects.get(pk=service_id)
                print(f"Service found: {service.name}")
                if 'maintenance' in service.name.lower():
                    queryset = queryset.filter(sub_service=sub_service)
                    print(f"After sub_service filter: {queryset.count()}")
            except Service.DoesNotExist:
                print(f"Service with ID {service_id} not found")
                pass
        
        return queryset
    
    @action(detail=False, methods=['get'])
    def sub_services(self, request):
        """Get available sub-services from registered providers"""
        # Get all unique sub-services from providers who have maintenance service
        sub_services = Provider.objects.filter(
            services__name__icontains='maintenance',
            sub_service__isnull=False
        ).exclude(
            sub_service=''
        ).values_list('sub_service', flat=True).distinct().order_by('sub_service')
        
        return Response({
            'sub_services': list(sub_services)
        })


from rest_framework.views import APIView
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
#from django.contrib.gis.geos import Point
#from django.contrib.gis.db.models.functions import Distance
from time import sleep    
#from django.contrib.gis.measure import D
#from django.contrib.gis.geos import Point
#from django.contrib.gis.db.models.functions import Distance
#from django.contrib.gis.measure import D
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from authentication.models import RideStatus, User
from django.db import models


def haversine(lat1, lng1, lat2, lng2):
    R = 6371  # Earth radius in km
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


class RequestProviderView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        service_id = request.data.get("service_id")
        if not service_id:
            return Response({"error": "Provider ID is required"}, status=400)

        try:
            provider = Provider.objects.select_related('user').filter(
                services__id=service_id,
                is_verified=True
            ).first()
        except Provider.DoesNotExist:
            return Response({"error": "Provider not found"}, status=404)

        # Send WebSocket signal to the provider
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"user_{provider.user.id}",
            {
                "type": "send_apply",
                "data": {
                    "client_id": request.user.id,
                    "client_name": request.user.name,
                    "message": "A client is requesting your service"
                }
            }
        )

        return Response({"status": "Request sent to provider"})
    



class StartRideRequestView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        lat = request.data.get("lat")
        lng = request.data.get("lng")
        service_id = request.data.get("service_id")

        if not (lat and lng and service_id):
            return Response({"error": "lat, lng, and service_id are required."}, status=400)

        lat = float(lat)
        lng = float(lng)

        providers = Provider.objects.filter(
            is_verified=True,
            services__id=service_id,
            user__location2_lat__isnull=False,
            user__location2_lng__isnull=False
        )

        # Filter providers within 5 km using Haversine and only those available
        nearby_providers = []
        from authentication.models import Service
        service = Service.objects.get(id=service_id)
        for provider in providers:
            # Exclude providers whose driver_profile.status is not 'available'
            if hasattr(provider, 'driver_profile') and provider.driver_profile.status != 'available':
                continue
            plat = provider.user.location2_lat
            plng = provider.user.location2_lng
            if plat is not None and plng is not None:
                distance = haversine(lat, lng, plat, plng)
                if distance <= 5:
                    # Get pricing for this provider/service
                    pricing = get_provider_service_pricing(provider, service)
                    if pricing:
                        total_price = (
                            pricing.application_fee +
                            pricing.service_price +
                            (pricing.delivery_fee_per_km * distance)
                        )
                    else:
                        total_price = None
                    provider.distance = distance
                    provider.total_price = total_price
                    nearby_providers.append(provider)
        nearby_providers.sort(key=lambda p: p.distance)

        if not nearby_providers:
            return Response({"error": "No nearby providers found."}, status=404)

        # Store client info
        client_data = {
            "client_id": request.user.id,
            "client_name": request.user.name,
            "lat": lat,
            "lng": lng
        }

        provider_price_map = {}

        for provider in nearby_providers:
            # Calculate price for this provider
            pricing = get_provider_service_pricing(provider, service)
            if pricing:
                total_price = (
                    pricing.application_fee +
                    pricing.service_price +
                    (pricing.delivery_fee_per_km * provider.distance)
                )
            else:
                total_price = None
            provider_price_map[provider.id] = {
                "provider_id": provider.id,
                "provider_name": provider.user.name,
                "distance_km": round(provider.distance, 2),
                "total_price": float(total_price) if total_price is not None else None
            }

            # Send WebSocket notification
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f"user_{provider.user.id}",
                {
                    "type": "send_apply",
                    "data": {
                        "message": "Ride request from nearby client",
                        **client_data,
                    }
                }
            )

        # Wait for 10 seconds to get a response (this is simulated; actual handling is done via WebSocket)
        for _ in range(10):
            from authentication.models import RideStatus
            accepted_ride = RideStatus.objects.filter(client_id=request.user.id, accepted=True).first()
            if accepted_ride:
                # Set customer.in_ride = True
                if hasattr(request.user, 'customer'):
                    request.user.customer.in_ride = True
                    request.user.customer.save()
                # Find the provider who accepted
                provider_id = accepted_ride.provider.id
                price_info = provider_price_map.get(provider_id, {})
                return Response({
                    "status": "Accepted by provider",
                    **price_info
                })
            sleep(1)

        return Response({"status": "No providers accepted the ride"})    
        



from .models import Notification
from .utils import create_notification


#  a7aa7aa7a
class BroadcastRideRequestView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user

        if RideStatus.objects.filter(client=user).exclude(status__in=["finished", "cancelled"]).exists():
            return Response({"error": "You already have an active ride request."}, status=400)

        lat = request.data.get("lat")
        lng = request.data.get("lng")
        service_id = request.data.get("service_id")
        drop_lat = request.data.get("drop_lat")
        drop_lng = request.data.get("drop_lng")
        ride_type = request.data.get("ride_type", "one_way")
        # Validate fields based on ride_type
        if ride_type == "two_way":
            if not (lat and lng and service_id and drop_lat and drop_lng):
                return Response({"error": "lat, lng, service_id, drop_lat, and drop_lng are required for two_way rides."}, status=400)
            lat = float(lat)
            lng = float(lng)
            drop_lat = float(drop_lat)
            drop_lng = float(drop_lng)
        else:  # one_way
            if not (lat and lng and service_id):
                return Response({"error": "lat, lng, and service_id are required for one_way rides."}, status=400)
            lat = float(lat)
            lng = float(lng)
            drop_lat = None
            drop_lng = None

        # add coupon code opttional 
        coupon_code = request.data.get("coupon_code", None)
        if coupon_code:
            from authentication.models import Coupon
            try:
                coupon = Coupon.objects.get(code=coupon_code, is_active=True)
                if coupon == None:
                    # adding any thing rather returning None
                    couponMessage = "Coupon not found or inactive."
                    coupon = None
            except Coupon.DoesNotExist:
                coupon = None
                couponMessage = "Coupon not found or inactive."
                # return Response({"error": "Invalid coupon code."}, status=400)  
       
        pricing = ProviderServicePricing.objects.filter(
            service_id=service_id,
        ).first() 
        if not pricing:
            return Response({"error": "No pricing found for this service."}, status=404)
        distance_km = 0 
        duration_minutes = 0
        if pricing:
            if drop_lat and drop_lng:
                distance_km = haversine(lat, lng, drop_lat, drop_lng)  
                duration_minutes = (distance_km / 30) * 60  # Assuming 2 minutes per km
            else:
                # For one-way rides, calculate distance and duration based on lat and lng and user's location
                user_location_lat = user.location2_lat
                user_location_lng = user.location2_lng
                print(f"User's location: {user_location_lat}, {user_location_lng}")
                print(f"Pickup location: {lat}, {lng}")
                if user_location_lat is None or user_location_lng is None:
                    return Response({"error": "User's location is not set."}, status=400)
                distance_km = haversine(lat, lng, user_location_lat, user_location_lng) 
                duration_minutes = (distance_km / 30) * 60  # Assuming
            # Calculate total price based on distance and duration    
            total_price  = pricing.calculate_price(
                distance_km=distance_km,
                duration_minutes=duration_minutes,
                pickup_time=timezone.now()
            )  
            if total_price is None:
                return Response({"error": "Failed to calculate total price."}, status=400)
            print (f"Distance: {distance_km} km, Duration: {duration_minutes} minutes, Total Price: {total_price}")

            total_price_before_discount = total_price

            
            if coupon_code:
                if coupon is None:
                    total_price = total_price  # No discount applied
                else:
                    couponMessage = "Coupon applied successfully."    
                    discount_amount = float(coupon.discount_percentage)
                    total_price -= total_price * discount_amount / 100
                    if total_price < 0:
                        total_price = 0
                    print(f"Total price after coupon: {total_price}")
                # Apply coupon discount if available
                
        
        
        providers = Provider.objects.filter(
            is_verified=True,
            services__id=service_id,
            user__location2_lat__isnull=False,
            user__location2_lng__isnull=False
        )

        # Filter providers within 5 km using Haversine and only those available
        nearby_providers = []
        for provider in providers:
            # Exclude providers whose driver_profile.status is not 'available'
            if hasattr(provider, 'driver_profile') and provider.driver_profile.status != 'available':
                continue
            plat = provider.user.location2_lat
            plng = provider.user.location2_lng
            if plat is not None and plng is not None:
                distance = haversine(lat, lng, plat, plng)
                if distance <= 5000:
                    provider.distance = distance
                    nearby_providers.append(provider)
        nearby_providers.sort(key=lambda p: p.distance)

        if not nearby_providers:
            return Response({"error": "No nearby providers found."}, status=404)

        # Send to all nearby providers simultaneously
        channel_layer = get_channel_layer()
        print('request.user.id')
        print(vars(request.user))
        client_data = {
            "client_id": request.user.id,
            "client_name": request.user.name,
            "client_phone": request.user.phone,
            "client_image": request.user.image.url if request.user.image else None,
            "avarage_rating": request.user.average_rating,
            "lat": lat,
            "lng": lng,
            "drop_lat": drop_lat,
            "drop_lng": drop_lng,
            "ride_type": ride_type,
            "message": "Ride request from nearby client",
            "total_price": total_price,
            "distance_km": distance_km,
            "duration_minutes": duration_minutes,
            "total_price_before_discount": total_price_before_discount if coupon_code and coupon else None,
        }

        for provider in nearby_providers:
            async_to_sync(channel_layer.group_send)(
                f"user_{provider.user.id}",
                {
                    "type": "send_apply",
                    "data": client_data
                }
            )
            # Create notification in database
            create_notification(
                user=provider.user,
                title="New Ride Request",
                message=f"You have a new ride request from {request.user.name}",
                notification_type='ride_request',
                data={
                    'client_id': request.user.id,
                    'client_name': request.user.name,
                    'lat': lat,
                    'lng': lng,
                    'ride_type': ride_type,
                    # 'ride_id': ride.id if 'ride' in locals() else None
                }
            )
            
            # Push notification
            notification_title = "New Ride Request"
            notification_body = f"You have a new ride request from {request.user.name}"
            
            # Get all FCM tokens for this provider
            fcm_tokens = list(provider.user.fcmdevice_set.values_list('registration_id', flat=True))
            
            # Send to each device token
            for token in fcm_tokens:
                send_fcm_notification(
                    token=token,
                    title=notification_title,
                    body=notification_body,
                    data={
                        "type": "new_ride_request",
                        "ride_data": json.dumps(client_data)
                    }
                )
        ride = RideStatus.objects.create(
            client=user,
            provider=None,  # not selected yet
            status="pending",
            service_id=service_id,
            pickup_lat=lat,
            pickup_lng=lng,
            drop_lat=drop_lat,
            drop_lng=drop_lng,
            total_price=total_price,
            distance_km=distance_km,
            duration_minutes=duration_minutes,
            total_price_before_discount=total_price_before_discount if coupon_code and coupon else None,
        )    
        # Set customer.in_ride = True
        if hasattr(user, 'customer'):
            user.customer.in_ride = True
            user.customer.save()

        # Clear cache for both client and potential providers
        self._clear_user_statistics_cache(user.id)
        for provider in nearby_providers:
            self._clear_user_statistics_cache(provider.user.id)

        return Response({"status": f"Broadcasted ride request to {len(nearby_providers)} nearby providers",
                         "ride_id": ride.id,
                        "total_price": total_price,
                        "distance_km": distance_km,
                        "duration_minutes": duration_minutes,
                        "total_price_before_discount": total_price_before_discount if coupon_code and coupon else None,
                            "coupon_code": coupon_code if coupon_code else None,
                            "coupon_message": couponMessage if coupon_code and coupon is None else None
                        }, status=200)

    def _clear_user_statistics_cache(self, user_id):
        """Clear cached statistics for a user when rides are updated"""
        cache_key = f"ride_stats_user_{user_id}"
        cache.delete(cache_key)        
    



class ProviderRideResponseView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        client_id = request.data.get("client_id")
        accepted = request.data.get("accepted")

        if not client_id or accepted is None:
            return Response({"error": "client_id and accepted are required."}, status=400)

        ride = RideStatus.objects.filter(client_id=client_id, status="pending").first()
        if not ride:
            return Response({"error": "No pending ride found."}, status=404)

        if accepted:
            if RideStatus.objects.filter(provider=request.user).exclude(status__in=["finished", "cancelled"]).exists():
                return Response({"error": "You already have an active ride."}, status=400)

            ride.provider = request.user
            ride.status = "accepted"
            ride.save()

            # Set provider.in_ride = True and driver_profile.status = 'in_ride'
            provider = getattr(request.user, 'provider', None)
            if provider:
                provider.in_ride = True
                provider.save()
                if hasattr(provider, 'driver_profile'):
                    provider.driver_profile.status = 'in_ride'
                    provider.driver_profile.save()
            # Create notification for client
            create_notification(
                user=ride.client,
                title="Ride Accepted",
                message=f"Your ride has been accepted by {request.user.name}",
                notification_type='ride_accepted',
                data={
                    'provider_id': request.user.id,
                    'provider_name': request.user.name,
                    'ride_id': ride.id
                }
            )                    

            # Notify client of acceptance
            async_to_sync(get_channel_layer().group_send)(
                f"user_{client_id}",
                {
                    "type": "send_acceptance",
                    "data": {
                        "ride_id": ride.id, 
                        "provider_id": request.user.id,
                        "provider_name": request.user.name,
                        "accepted": accepted,
                        "provider_image": request.user.image.url if request.user.image else None,
                        "provider_phone": request.user.phone,
                        "avarage_rating": request.user.average_rating
                    }
                }
            )
            
            # Send push notification to client
            notification_title = "Ride Accepted"
            notification_body = f"Your ride has been accepted by {request.user.name}"
            
            # Get all FCM tokens for the client
            client = User.objects.get(id=client_id)
            fcm_tokens = list(client.fcmdevice_set.values_list('registration_id', flat=True))
            
            for token in fcm_tokens:
                send_fcm_notification(
                    token=token,
                    title=notification_title,
                    body=notification_body,
                    data={
                        "type": "ride_accepted",
                        "provider_id": str(request.user.id),
                        "provider_name": request.user.name
                    }
                )
        else:
            ride.status = "cancelled"
            ride.save()

            # Notify client of cancellation
            async_to_sync(get_channel_layer().group_send)(
                f"user_{client_id}",
                {
                    "type": "send_cancel",
                    "data": {
                        "provider_id": request.user.id,
                        "accepted": accepted,
                    }
                }
            )
            
            # Send push notification to client
            notification_title = "Ride Declined"
            notification_body = "A driver has declined your ride request"
            
            # Get all FCM tokens for the client
            client = User.objects.get(id=client_id)
            fcm_tokens = list(client.fcmdevice_set.values_list('registration_id', flat=True))
            
            for token in fcm_tokens:
                send_fcm_notification(
                    token=token,
                    title=notification_title,
                    body=notification_body,
                    data={
                        "type": "ride_declined"
                    }
                )

        return Response({"status": "Response processed."})



class UpdateRideStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        status = request.data.get("status")
        valid_statuses = ["starting", "arriving", "finished", "cancelled"]

        if status not in valid_statuses:
            return Response({"error": "Invalid status."}, status=400)

        ride = RideStatus.objects.filter(
            models.Q(client=request.user) | models.Q(provider=request.user),
            status__in=["pending", "accepted", "starting", "arriving"]
        ).first()

        if not ride:
            return Response({"error": "No active ride found."}, status=404)

        ride.status = status
        ride.save()

        # Handle ride completion and rating creation
        if status == "finished":
            # Create or get a rating object when ride is finished
            Rating.objects.get_or_create(ride=ride)

        # Update in_ride and driver_profile status for both provider and customer
        if status in ["finished", "cancelled"]:
            # Provider
            provider_user = ride.provider
            provider = getattr(provider_user, 'provider', None)
            if provider and hasattr(provider, 'driver_profile'):
                provider.driver_profile.status = 'available'
                provider.driver_profile.save()
            if provider:
                provider.in_ride = False
                provider.save()
            # Customer
            customer = None
            if hasattr(ride.client, 'customer'):
                customer = ride.client.customer
            if customer and hasattr(customer, 'in_ride'):
                customer.in_ride = False
                customer.save()

        # Notify the other party about status change
        if request.user == ride.client:
            # Client is updating status - notify provider
            notify_user = ride.provider
            notification_title = "Ride Status Update"
            
            if status == "finished":
                notification_body = "The ride has been completed by the client. You can now rate the client."
            elif status == "cancelled":
                notification_body = "The ride has been cancelled by the client."
            else:
                notification_body = f"Ride status updated to {status}"
        else:
            # Provider is updating status - notify client
            notify_user = ride.client
            notification_title = "Ride Status Update"
            
            if status == "starting":
                notification_body = "Your driver is starting the ride."
            elif status == "arriving":
                notification_body = "Your driver is arriving at your location."
            elif status == "finished":
                notification_body = "Your ride has been completed. You can now rate the driver."
            elif status == "cancelled":
                notification_body = "Your ride has been cancelled by the driver."
            else:
                notification_body = f"Ride status updated to {status}"

        # Create notification in database
        create_notification(
            user=notify_user,
            title=notification_title,
            message=notification_body,
            notification_type='ride_status',
            data={
                'status': status,
                'ride_id': ride.id,
                'updated_by': request.user.id
            }
        )

        # Send WebSocket notification with ride_id
        async_to_sync(get_channel_layer().group_send)(
            f"user_{notify_user.id}",
            {
                "type": "ride_status_update",
                "data": {
                    "status": status,
                    "ride_id": ride.id,
                    "provider_id": ride.provider.id if ride.provider else None,
                    "message": notification_body
                }
            }
        )

        # Send push notification
        fcm_tokens = list(notify_user.fcmdevice_set.values_list('registration_id', flat=True))
        
        for token in fcm_tokens:
            send_fcm_notification(
                token=token,
                title=notification_title,
                body=notification_body,
                data={
                    "type": "ride_status_update",
                    "status": status,
                    "ride_id": str(ride.id)
                }
            )

        # Clear cache for both client and provider when ride status changes
        self._clear_user_statistics_cache(ride.client.id)
        if ride.provider:
            self._clear_user_statistics_cache(ride.provider.id)

        # Prepare response with ride_id
        response_data = {
            "status": f"Ride updated to {status}.",
            "ride_id": ride.id
        }

        return Response(response_data)

    def _clear_user_statistics_cache(self, user_id):
        """Clear cached statistics for a user when rides are updated"""
        cache_key = f"ride_stats_user_{user_id}"
        cache.delete(cache_key)
    


class NearbyRideRequestsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        provider = getattr(user, 'provider', None)
        if not provider:
            return Response({"error": "You are not a provider."}, status=403)

        lat = user.location2_lat
        lng = user.location2_lng
        if lat is None or lng is None:
            return Response({"error": "Provider location is not set."}, status=400)

        service_ids = provider.services.values_list('id', flat=True)

        pending_rides = RideStatus.objects.filter(
            status="pending",
            service_id__in=service_ids,
            pickup_lat__isnull=False,
            pickup_lng__isnull=False
        )
        if pending_rides:
            print(pending_rides)
        else:
            print("Ayad")

        nearby_rides = []
        for ride in pending_rides:
            distance = haversine(lat, lng, ride.pickup_lat, ride.pickup_lng)
            print(f"Distance to ride {ride.id}: {distance} meters")
            if distance <= 5000:
                nearby_rides.append({
                    "ride_id": ride.id,
                    "client_id": ride.client.id,
                    "client_name": ride.client.name,
                    "pickup_lat": ride.pickup_lat,
                    "pickup_lng": ride.pickup_lng,
                    "drop_lat": ride.drop_lat,
                    "drop_lng": ride.drop_lng,
                    "service_id": ride.service_id,
                    "distance_km": round(distance, 2)
                })

        return Response({"rides": nearby_rides})


class DriverLocationUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        location = request.data.get("location")
        heading = request.data.get("heading", None)

        if not location:
            return Response({"error": "Location is required."}, status=400)

        # Parse location string
        try:
            lat_str, lng_str = location.split(',')
            lat = float(lat_str.strip())
            lng = float(lng_str.strip())
        except Exception:
            return Response({"error": "Invalid location format. Use 'lat,lng'."}, status=400)

        # Update user location
        User.objects.filter(id=user.id).update(
            location=location,
            location2_lat=lat,
            location2_lng=lng
        )

        # Get active ride where this user is the provider
        ride = RideStatus.objects.filter(
            provider=user,
            status__in=["accepted", "starting", "arriving"]
        ).order_by('-created_at').first()

        if ride and ride.client:
            # Send location to client via WebSocket
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f"user_{ride.client.id}",
                {
                    "type": "location",
                    "location": location,
                    "heading": heading,
                }
            )

            # Optionally create notification for significant location updates
            # You might want to add logic to determine significant changes
            create_notification(
                user=ride.client,
                title="Driver Location Updated",
                message="Your driver's location has been updated",
                notification_type='driver_location',
                data={
                    'location': location,
                    'heading': heading,
                    'ride_id': ride.id
                }
            )            
            
            # Optionally send push notification if significant location change
            # (You might want to add logic to only notify on significant changes)
            notification_title = "Driver Location Update"
            notification_body = "Your driver's location has been updated"
            
            fcm_tokens = list(ride.client.fcmdevice_set.values_list('registration_id', flat=True))
            
            for token in fcm_tokens:
                send_fcm_notification(
                    token=token,
                    title=notification_title,
                    body=notification_body,
                    data={
                        "type": "driver_location_update",
                        "location": location,
                        "heading": str(heading) if heading else None
                    }
                )

        return Response({"message": "Location updated and sent."})
    
class ClientCancelRideView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user

        # Find an active ride for the client with status "pending" or "accepted"
        ride = RideStatus.objects.filter(
            client=user,
            status__in=["pending", "accepted"]
        ).first()

        if not ride:
            return Response({"error": "No active ride found with status 'pending' or 'accepted'."}, status=404)

        # Update ride status to cancelled
        ride.status = "cancelled"
        ride.save()

        # Reset customer's in_ride status
        if hasattr(user, 'customer'):
            user.customer.in_ride = False
            user.customer.save()

        # If a provider is assigned, reset their in_ride and driver_profile status
        if ride.provider:
            provider = getattr(ride.provider, 'provider', None)
            if provider:
                provider.in_ride = False
                provider.save()
                if hasattr(provider, 'driver_profile'):
                    provider.driver_profile.status = 'available'
                    provider.driver_profile.save()
            # Create notification for provider
            create_notification(
                user=ride.provider,
                title="Ride Cancelled",
                message=f"The ride request from {user.name} has been cancelled",
                notification_type='ride_cancelled',
                data={
                    'client_id': user.id,
                    'client_name': user.name,
                    'ride_id': ride.id
                }
            )
            # Notify provider via WebSocket
            async_to_sync(get_channel_layer().group_send)(
                f"user_{ride.provider.id}",
                {
                    "type": "ride_status_update",
                    "data": {
                        "status": "cancelled",
                        "ride_id": ride.id,
                        "message": "The ride has been cancelled by the client"
                    }
                }
            )

            # Send push notification to provider
            notification_title = "Ride Cancelled"
            notification_body = f"The ride request from {user.name} has been cancelled."
            fcm_tokens = list(ride.provider.fcmdevice_set.values_list('registration_id', flat=True))

            for token in fcm_tokens:
                send_fcm_notification(
                    token=token,
                    title=notification_title,
                    body=notification_body,
                    data={
                        "type": "ride_cancelled",
                        "ride_id": str(ride.id)
                    }
                )

        return Response({"status": "Ride cancelled successfully."})

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.select_related('provider__user').prefetch_related('images')
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated, IsStoreProvider]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['is_active', 'provider']

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy', 'upload_image']:
            return [IsAuthenticated(), IsStoreProvider()]
        elif self.action in ['list', 'retrieve']:
            return [IsAuthenticated()]
        return [IsCustomer()]

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.user.role == ROLE_PROVIDER:
            return queryset.filter(provider__user=self.request.user)
        return queryset.filter(is_active=True)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    @action(detail=True, methods=['post'], url_path='upload-image')
    def upload_image(self, request, pk=None):
        """
        Upload one or multiple images for a specific product.
        Only the product owner (provider) can upload images.
        """
        try:
            product = self.get_object()
        except Product.DoesNotExist:
            return Response({"detail": "Product not found."}, status=404)

        # Check if the current user is the owner of the product
        if product.provider.user != request.user:
            return Response(
                {"detail": "You can only upload images to your own products."}, 
                status=403
            )

        # Handle multiple images
        uploaded_images = []
        errors = []
        
        # Get all files from request.FILES
        files = request.FILES.getlist('image') if hasattr(request.FILES, 'getlist') else [request.FILES.get('image')]
        
        if not files or not any(files):
            return Response({"detail": "No image files provided."}, status=400)
        
        for file in files:
            if file:  # Check if file exists
                serializer = ProductImageSerializer(data={'image': file})
                if serializer.is_valid():
                    serializer.save(product=product)
                    uploaded_images.append(serializer.data)
                else:
                    errors.append(f"Error with file {file.name}: {serializer.errors}")
        
        if uploaded_images:
            response_data = {
                "uploaded_images": uploaded_images,
                "total_uploaded": len(uploaded_images)
            }
            if errors:
                response_data["errors"] = errors
            
            return Response(response_data, status=status.HTTP_201_CREATED)
        else:
            return Response({"errors": errors}, status=status.HTTP_400_BAD_REQUEST)


class PurchaseViewSet(viewsets.ModelViewSet):
    serializer_class = PurchaseSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status', 'product__provider']

    def get_permissions(self):
        if self.action == 'create':
            return [IsAuthenticated(), IsCustomer()]
        elif self.action in ['update', 'partial_update']:
            return [IsAuthenticated()]
        return [IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        if hasattr(user, 'customer'):
            return Purchase.objects.filter(customer__user=user).select_related('product', 'customer__user')
        elif hasattr(user, 'provider'):
            # Only show purchases for store providers
            if user.provider.services.filter(name__icontains='store').exists():
                return Purchase.objects.filter(product__provider__user=user).select_related('product', 'customer__user')
            return Purchase.objects.none()
        return Purchase.objects.none()

    def get_serializer_context(self):
        context = super().get_serializer_context()
        if hasattr(self.request.user, 'customer'):
            context['customer'] = self.request.user.customer
        return context

    def create(self, request, *args, **kwargs):
        if not hasattr(request.user, 'customer'):
            return Response(
                {"detail": "Only customers can make purchases."},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        user = request.user
        
        # Only allow providers with store service to update status of their products' purchases
        if hasattr(user, 'provider'):
            if not user.provider.services.filter(name__icontains='store').exists():
                return Response(
                    {"detail": "Only store providers can update purchase status."},
                    status=status.HTTP_403_FORBIDDEN
                )
            if instance.product.provider.user != user:
                return Response(
                    {"detail": "You can only update purchases of your own products."},
                    status=status.HTTP_403_FORBIDDEN
                )
        # Customers can only update their own purchases
        elif hasattr(user, 'customer'):
            if instance.customer.user != user:
                return Response(
                    {"detail": "You can only update your own purchases."},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        return super().update(request, *args, **kwargs)


class UserPointsViewSet(viewsets.ModelViewSet):
    serializer_class = UserPointsSerializer
    http_method_names = ['get', 'patch', 'post']
    permission_classes = [IsAuthenticated, IsCustomerOrAdmin]

    def get_queryset(self):
        # Only allow customers to see their own, admins can see all
        if self.request.user.is_staff:
            return UserPoints.objects.all()
        return UserPoints.objects.filter(user=self.request.user)

    @action(detail=False, methods=['post'], url_path='charge', permission_classes=[IsAuthenticated, IsCustomerOrAdmin])
    def charge(self, request):
        amount = request.data.get('points')
        user_id = request.data.get('user_id')
        if not amount or not str(amount).isdigit():
            return Response({'detail': 'Invalid points value.'}, status=status.HTTP_400_BAD_REQUEST)
        amount = int(amount)

        # Admin can specify user_id, customer can only charge themselves
        if request.user.is_staff and user_id:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            try:
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                return Response({'detail': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)
        else:
            user = request.user

        user_points, _ = UserPoints.objects.get_or_create(user=user)
        user_points.points += amount
        user_points.save()
        return Response({'points': user_points.points, 'detail': 'Points charged successfully.'})

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.user != request.user:
            return Response({"detail": "Not allowed."}, status=403)
        return super().retrieve(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.user != request.user:
            return Response({"detail": "Not allowed."}, status=403)
        return super().partial_update(request, *args, **kwargs)


class CarAgencyViewSet(viewsets.ModelViewSet):
    queryset = CarAgency.objects.prefetch_related('availability_slots', 'rentals')
    serializer_class = CarAgencySerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['brand', 'model', 'color']
    search_fields = ['brand', 'model', 'color']

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAdminOrOwnCarAgency()]
        return [IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        queryset = super().get_queryset()

        # Customers see only available cars in valid slots & no conflicting rentals
        if user.role == "CU":
            now = timezone.now()
            queryset = queryset.filter(
                available=True,
                availability_slots__end_time__gte=now
            ).distinct()
            
            desired_start = self.request.query_params.get('desired_start')
            desired_end = self.request.query_params.get('desired_end')

            if desired_start and desired_end:
                qs_ids = []
                for car in queryset:
                    slots = car.availability_slots.filter(
                        start_time__lte=desired_start,
                        end_time__gte=desired_end
                    )
                    rentals = car.rentals.filter(
                        start_datetime__lt=desired_end,
                        end_datetime__gt=desired_start,
                        status__in=["pending", "confirmed", "in_progress", "completed"]
                    )
                    if slots.exists() and not rentals.exists():
                        qs_ids.append(car.id)
                queryset = queryset.filter(id__in=qs_ids)
            else:
                qs_ids = []
                for car in queryset:
                    slots = car.availability_slots.filter(end_time__gte=now)
                    has_free_slot = False
                    for slot in slots:
                        overlapping_rentals = car.rentals.filter(
                            start_datetime__lt=slot.end_time,
                            end_datetime__gt=slot.start_time,
                            status__in=["pending", "confirmed", "in_progress", "completed"]
                        )
                        total_slot_time = (slot.end_time - slot.start_time).total_seconds()
                        reserved_time = 0
                        for rental in overlapping_rentals:
                            overlap_start = max(slot.start_time, rental.start_datetime)
                            overlap_end = min(slot.end_time, rental.end_datetime)
                            reserved_time += max(0, (overlap_end - overlap_start).total_seconds())
                        if reserved_time < total_slot_time:
                            has_free_slot = True
                            break
                    if has_free_slot:
                        qs_ids.append(car.id)
                queryset = queryset.filter(id__in=qs_ids)

        provider = getattr(user, 'provider', None)
        if provider and provider.services.filter(name__iexact='car agency').exists():
            queryset = queryset.filter(provider=provider)

        return queryset

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        desired_start = request.query_params.get('desired_start')
        desired_end = request.query_params.get('desired_end')
        if desired_start and desired_end:
            desired_start_dt = parse_datetime(desired_start)
            desired_end_dt = parse_datetime(desired_end)
            queryset = super().get_queryset()
            now = timezone.now()
            queryset = queryset.filter(
                available=True,
                availability_slots__end_time__gte=now
            ).distinct()
            cars_with_overlap = []
            for car in queryset:
                slots = car.availability_slots.filter(
                    end_time__gte=desired_start_dt,
                    start_time__lte=desired_end_dt
                )
                if slots.exists():
                    cars_with_overlap.append(car)
            serializer = self.get_serializer(cars_with_overlap, many=True)
            filtered_data = []
            for car, car_data in zip(cars_with_overlap, serializer.data):
                filtered_times = []
                for t in car_data.get('actual_free_times', []):
                    s = parse_datetime(t['start']) if isinstance(t['start'], str) else t['start']
                    e = parse_datetime(t['end']) if isinstance(t['end'], str) else t['end']
                    # Only include if overlaps with desired window
                    overlap_start = max(s, desired_start_dt)
                    overlap_end = min(e, desired_end_dt)
                    if overlap_start < overlap_end:
                        # If the available time fully covers the desired window, only return the desired window
                        if s <= desired_start_dt and e >= desired_end_dt:
                            filtered_times = [{
                                'start': desired_start_dt.isoformat(),
                                'end': desired_end_dt.isoformat()
                            }]
                            break  # Only show the exact desired window
                        else:
                            filtered_times.append({
                                'start': overlap_start.isoformat(),
                                'end': overlap_end.isoformat()
                            })
                if filtered_times:
                    car_data['actual_free_times'] = filtered_times
                    filtered_data.append(car_data)
            return Response(filtered_data, status=status.HTTP_200_OK)
        return response

    def perform_create(self, serializer):
        provider = getattr(self.request.user, 'provider', None)
        if not provider:
            raise serializers.ValidationError({'provider': 'Current user does not have a provider profile.'})
        serializer.save(provider=provider)


class CarAvailabilityViewSet(viewsets.ModelViewSet):
    queryset = CarAvailability.objects.all()
    serializer_class = CarAvailabilitySerializer
    permission_classes = [IsAuthenticated, IsAdminOrOwnCarAgency]

    @action(detail=False, methods=['post'], url_path='bulk_create')
    def bulk_create(self, request):
        car_id = request.data.get('car')
        slots = request.data.get('slots')
        if not car_id or not slots:
            return Response({"detail": "Missing car or slots."}, status=status.HTTP_400_BAD_REQUEST)

        car = get_object_or_404(CarAgency, id=car_id)
        created_slots = []
        for slot in slots:
            serializer = self.get_serializer(data={'car': car.id, **slot})
            serializer.is_valid(raise_exception=True)
            serializer.save()
            created_slots.append(serializer.data)
        return Response({"slots_created": created_slots}, status=status.HTTP_201_CREATED)


class CarRentalViewSet(viewsets.ModelViewSet):
    queryset = CarRental.objects.all()
    serializer_class = CarRentalSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.action in ['update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), IsAdminOrOwnCarAgency()]
        if self.action == 'create':
            return [IsAuthenticated(), IsCustomer()]
        return [IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        if user.role == "CU" and hasattr(user, 'customer'):
            return CarRental.objects.filter(customer=user.customer)
        # Providers with Car Agency service see rentals for their cars
        provider = getattr(user, 'provider', None)
        if provider and provider.services.filter(name__iexact='car agency').exists():
            return CarRental.objects.filter(car__provider=provider)
        elif user.is_staff:
            return CarRental.objects.all()
        return CarRental.objects.none()

    def perform_create(self, serializer):
        serializer.save(customer=self.request.user.customer)

from .pagination import SimplePagination

class NotificationListView(generics.ListAPIView):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = SimplePagination

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user).order_by('-created_at')

class NotificationMarkAsReadView(generics.UpdateAPIView):
    permission_classes = [IsAuthenticated]
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer

    def update(self, request, *args, **kwargs):
        notification = self.get_object()
        if notification.user != request.user:
            return Response(
                {"detail": "You don't have permission to mark this notification as read."},
                status=status.HTTP_403_FORBIDDEN
            )
        notification.mark_as_read()
        return Response({"status": "Notification marked as read"})

class UnreadNotificationCountView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        count = Notification.objects.filter(user=request.user, is_read=False).count()
        return Response({"unread_count": count})
    


from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from authentication.models import RideStatus, Rating, Customer, Provider
from authentication.serializers import RatingSerializer
from django.db.models import Avg
from rest_framework import status

class RateRideView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, ride_id):
        try:
            ride = RideStatus.objects.get(id=ride_id, status='finished')
        except RideStatus.DoesNotExist:
            return Response({"error": "Ride not found or not completed."}, status=404)

        if request.user not in [ride.client, ride.provider]:
            return Response({"error": "You are not part of this ride."}, status=403)

        rating, created = Rating.objects.get_or_create(ride=ride)

        # Prevent duplicate ratings
        if request.user == ride.client and rating.driver_rating is not None:
            return Response({"error": "You have already rated the driver for this ride."}, status=400)
        elif request.user == ride.provider and rating.customer_rating is not None:
            return Response({"error": "You have already rated the customer for this ride."}, status=400)

        # Assign rating based on user role
        if request.user == ride.client:
            # Customer rates the driver
            serializer = RatingSerializer(rating, data={
                'driver_rating': request.data.get('rating'),
                'driver_comment': request.data.get('comment', '')
            }, partial=True)
            notify_user = ride.provider
            notification_title = "New Driver Rating"
            notification_message = f"Client {request.user.name} rated you for ride #{ride.id}."
        elif request.user == ride.provider:
            # Driver rates the customer
            serializer = RatingSerializer(rating, data={
                'customer_rating': request.data.get('rating'),
                'customer_comment': request.data.get('comment', '')
            }, partial=True)
            notify_user = ride.client
            notification_title = "New Customer Rating"
            notification_message = f"Driver {request.user.name} rated you for ride #{ride.id}."

        if serializer.is_valid():
            serializer.save()

            # Update average ratings
            self.update_user_ratings(ride.client)
            if ride.provider:
                self.update_user_ratings(ride.provider)

            # Send WebSocket notification to the other party
            if notify_user:
                async_to_sync(get_channel_layer().group_send)(
                    f"user_{notify_user.id}",
                    {
                        "type": "rating_update",
                        "data": {
                            "ride_id": ride.id,
                            "message": notification_message
                        }
                    }
                )

                # Create database notification
                create_notification(
                    user=notify_user,
                    title=notification_title,
                    message=notification_message,
                    notification_type='ride_status',
                    data={
                        'ride_id': ride.id,
                        'rated_by': request.user.id,
                        'rated_by_name': request.user.name
                    }
                )

                # Send FCM push notification
                fcm_tokens = list(notify_user.fcmdevice_set.values_list('registration_id', flat=True))
                for token in fcm_tokens:
                    send_fcm_notification(
                        token=token,
                        title=notification_title,
                        body=notification_message,
                        data={
                            "type": "rating_update",
                            "ride_id": str(ride.id),
                            "rated_by": str(request.user.id)
                        }
                    )

            return Response(serializer.data)
        return Response(serializer.errors, status=400)

    def update_user_ratings(self, user):
        """Update the average rating for a user"""
        if hasattr(user, 'customer'):
            ratings = Rating.objects.filter(ride__client=user).exclude(customer_rating__isnull=True)
            if ratings.exists():
                avg_rating = ratings.aggregate(Avg('customer_rating'))['customer_rating__avg']
                user.customer.average_rating = round(avg_rating, 1)
                user.customer.save()
        elif hasattr(user, 'provider'):
            ratings = Rating.objects.filter(ride__provider=user).exclude(driver_rating__isnull=True)
            if ratings.exists():
                avg_rating = ratings.aggregate(Avg('driver_rating'))['driver_rating__avg']
                user.provider.average_rating = round(avg_rating, 1)
                user.provider.save()


class RideRatingView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = RatingSerializer
    queryset = Rating.objects.all()

    def get_object(self):
        ride_id = self.kwargs.get('ride_id')
        try:
            ride = RideStatus.objects.get(id=ride_id)
            if self.request.user not in [ride.client, ride.provider]:
                raise PermissionDenied("You are not part of this ride.")
            return ride.rating
        except RideStatus.DoesNotExist:
            raise Http404("Ride not found")
        except Rating.DoesNotExist:
            raise Http404("Rating not found")

class ProviderServicePricingViewSet(viewsets.ModelViewSet):
    queryset = ProviderServicePricing.objects.all()
    serializer_class = ProviderServicePricingSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['provider', 'service', 'sub_service', 'zone', 'is_active']
    search_fields = ['provider__user__name', 'service__name', 'sub_service', 'zone__name']

def get_provider_service_pricing(provider, service):
    try:
        return ProviderServicePricing.objects.get(provider=provider, service=service)
    except ProviderServicePricing.DoesNotExist:
        return None

# Example usage in your business logic:
# pricing = get_provider_service_pricing(provider, service)
# if not pricing:
#     # Handle missing pricing (e.g., error or default)
# class PricingZoneViewSet(viewsets.ModelViewSet):
#     queryset = PricingZone.objects.all()
#     serializer_class = PricingZoneSerializer
#     permission_classes = [IsAuthenticated]
#     filter_backends = [DjangoFilterBackend, filters.SearchFilter]
#     filterset_fields = ['is_active']
#     search_fields = ['name', 'description']
    
#     def get_permissions(self):
#         """
#         Only admin can create/update/delete zones, others can only read
#         """
#         if self.action in ['create', 'update', 'partial_update', 'destroy']:
#             permission_classes = [IsAdminUser]
#         else:
#             permission_classes = [IsAuthenticated]
#         return [permission() for permission in permission_classes]
# total = pricing.application_fee + pricing.service_price + (pricing.delivery_fee_per_km * distance_km)

# class CalculatePriceView(APIView):
#     """
#     Calculate ride price based on pickup/drop locations and service
#     """
#     permission_classes = [IsAuthenticated]
    
#     def post(self, request):
#         serializer = PriceCalculationSerializer(data=request.data)
#         if serializer.is_valid():
#             data = serializer.validated_data
            
#             # Find available providers for the service
#             providers = Provider.objects.filter(
#                 services=data['service'],
#                 is_verified=True
#             )
            
#             if data.get('sub_service'):
#                 providers = providers.filter(sub_service=data['sub_service'])
            
#             pricing_options = []
            
#             for provider in providers:
#                 # Get pricing for pickup location
#         # Get pricing for this service and location
#         pricing = ProviderServicePricing.get_pricing_for_location(
#             service=service,
#             sub_service=sub_service,
#             lat=pickup_lat,
#             lng=pickup_lng
#         )
        
#         if not pricing:
#             return Response({
#                 'error': 'No pricing available for this service and location'
#             }, status=status.HTTP_404_NOT_FOUND)
        
#         total_price = pricing.calculate_price(
#             distance_km=distance_km,
#             duration_minutes=duration_minutes,
#             pickup_time=pickup_time
#         )
        
#         # Calculate breakdown
#         base_cost = float(pricing.base_fare)
#         distance_cost = float(pricing.price_per_km) * distance_km
#         time_cost = float(pricing.price_per_minute) * duration_minutes
#         subtotal = base_cost + distance_cost + time_cost
        
#         # Apply peak hour multiplier
#         peak_multiplier = 1.0
#         if pickup_time and pricing.peak_hours_start and pricing.peak_hours_end:
#             pickup_time_only = pickup_time.time() if hasattr(pickup_time, 'time') else pickup_time
#             if pricing.peak_hours_start <= pickup_time_only <= pricing.peak_hours_end:
#                 peak_multiplier = float(pricing.peak_hour_multiplier)
#         booking_fee = float(pricing.booking_fee or 0)
#                 'service_name': data['service'].name,
#                 'sub_service': data.get('sub_service'),
#             'zone_name': pricing.zone.name if pricing.zone else 'Default Zone',
#             'total_price': final_total,
#             'distance_km': round(distance_km, 2),
#             'estimated_duration_minutes': round(duration_minutes, 2),
#             'pricing_breakdown': {
#                 'base_fare': base_cost,
#                 'distance_cost': float(pricing.price_per_km) * distance_km,
#                 'time_cost': float(pricing.price_per_minute) * duration_minutes,
#                 'subtotal': base_cost + distance_cost + time_cost,
#                 'peak_multiplier': peak_multiplier,
#                 'subtotal_after_peak': subtotal,
#                 'platform_fee': platform_fee,
#                 'service_fee': service_fee,
#                 'booking_fee': booking_fee,
#                 'total_with_fees': total_with_fees,
#                 'minimum_fare': float(pricing.minimum_fare),
#                 'final_total': final_total
#             }
#         return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
#     def _calculate_distance(self, lat1, lon1, lat2, lon2):
#         """Calculate distance between two points in kilometers"""
#         import math
#         R = 6371.0  # Radius of Earth in kilometers
#         phi1 = math.radians(lat1)
#         phi2 = math.radians(lat2)
#         d_phi = math.radians(lat2 - lat1)
#         d_lambda = math.radians(lon2 - lon1)

#         a = math.sin(d_phi / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2)**2
#         c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

#         return round(R * c, 2)

from dal import autocomplete
class ProviderAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        qs = Provider.objects.all()
        if self.q:
            qs = qs.filter(user__name__icontains=self.q)
        return qs

class ServiceAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        qs = Service.objects.all()
        provider_id = self.forwarded.get('provider', None)
        if provider_id:
            try:
                provider = Provider.objects.get(pk=provider_id)
                qs = provider.services.all()
            except Provider.DoesNotExist:
                qs = Service.objects.none()
        return qs


class ProfileUpdateView(generics.UpdateAPIView):
    """
    View for updating user profile information.
    Supports PATCH requests to update name, email, image, and location.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = ProfileUpdateSerializer
    http_method_names = ['patch']

    def get_object(self):
        return self.request.user

    def patch(self, request, *args, **kwargs):
        """
        Update user profile information.
        
        Accepts:
        - name: string
        - email: string  
        - image: file
        - location: string (format: "latitude,longitude")
        - location2_lat: float
        - location2_lng: float
        
        Returns updated user profile data.
        """
        return super().patch(request, *args, **kwargs)

class RideHistoryView(generics.ListAPIView):
    """
    View for getting ride history for both drivers and customers.
    Returns rides where the authenticated user is either the client or provider.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = RideHistorySerializer
    pagination_class = SimplePagination

    def get_queryset(self):
        user = self.request.user
        
        # Get rides where user is either client or provider
        queryset = RideStatus.objects.filter(
            models.Q(client=user) | models.Q(provider=user)
        ).select_related(
            'client', 'provider', 'service'
        ).prefetch_related(
            'rating'
        ).order_by('-created_at')
        
        # Filter by status if provided
        status = self.request.query_params.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        # Filter by date range if provided
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        
        if start_date:
            queryset = queryset.filter(created_at__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__lte=end_date)
        
        # Filter by ride type (customer/driver rides)
        ride_type = self.request.query_params.get('ride_type')
        if ride_type == 'customer':
            queryset = queryset.filter(client=user)
        elif ride_type == 'driver':
            queryset = queryset.filter(provider=user)
        
        return queryset

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)
        
        page_number = request.query_params.get('page', 1)
        try:
            page_number = int(page_number)
        except (ValueError, TypeError):
            page_number = 1
        
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            response_data = self.get_paginated_response(serializer.data)
    
            # Include statistics only on the first page
            if page_number == 1:
                statistics = self._get_cached_statistics(queryset)
                response_data.data['statistics'] = statistics
    
            return response_data  # ✅ Already a DRF Response
    
        # No pagination
        serializer = self.get_serializer(queryset, many=True)
        response_data = {
            'results': serializer.data,
            'statistics': self._get_cached_statistics(queryset)
        }
        return Response(response_data)  # ✅ Wrapped in DRF Response

    def _get_cached_statistics(self, queryset):
        """Get cached statistics or calculate and cache them"""
        user_id = self.request.user.id
        cache_key = f"ride_stats_user_{user_id}"
        
        # Try to get cached statistics
        cached_stats = cache.get(cache_key)
        
        if cached_stats is None:
            # Calculate and cache statistics
            stats = self._calculate_ride_statistics(queryset)
            # Cache for 5 minutes (300 seconds)
            cache.set(cache_key, stats, 300)
            return stats
        
        return cached_stats

    def _clear_user_statistics_cache(self, user_id):
        """Clear cached statistics for a user when rides are updated"""
        cache_key = f"ride_stats_user_{user_id}"
        cache.delete(cache_key)

    def _calculate_ride_statistics(self, queryset):
        """Calculate essential ride statistics for the user"""
        user = self.request.user
        
        total_rides = queryset.count()
        completed_rides = queryset.filter(status='finished').count()
        
        # Calculate total earnings/spent
        total_amount = 0
        if hasattr(user, 'provider'):
            # For drivers: calculate earnings
            driver_rides = queryset.filter(provider=user, status='finished')
            for ride in driver_rides:
                # Calculate price for each completed ride
                if ride.provider and ride.service:
                    provider_obj = getattr(ride.provider, 'provider', None)
                    if provider_obj:
                        pricing = ProviderServicePricing.objects.filter(
                            service=ride.service
                        ).first()
                        if pricing:
                            if all([ride.pickup_lat, ride.pickup_lng, ride.drop_lat, ride.drop_lng]):
                                distance_km = self._calculate_distance(
                                    ride.pickup_lat, ride.pickup_lng, ride.drop_lat, ride.drop_lng
                                )
                            else:
                                distance_km = 0
                            application_fee = float(pricing.platform_fee or 0)
                            service_price = float(pricing.service_fee or 0)
                            delivery_fee_per_km = float(pricing.price_per_km or 0)
                            delivery_fee_total = delivery_fee_per_km * distance_km
                            total_amount += round(application_fee + service_price + delivery_fee_total, 2)
        
        elif hasattr(user, 'customer'):
            # For customers: calculate total spent
            customer_rides = queryset.filter(client=user, status='finished')
            for ride in customer_rides:
                # Calculate price for each completed ride
                if ride.provider and ride.service:
                    provider_obj = getattr(ride.provider, 'provider', None)
                    if provider_obj:
                        pricing = ProviderServicePricing.objects.filter(
                            service=ride.service
                        ).first()
                        if pricing:
                            if all([ride.pickup_lat, ride.pickup_lng, ride.drop_lat, ride.drop_lng]):
                                distance_km = self._calculate_distance(
                                    ride.pickup_lat, ride.pickup_lng, ride.drop_lat, ride.drop_lng
                                )
                            else:
                                distance_km = 0
                            application_fee = float(pricing.platform_fee or 0)
                            service_price = float(pricing.service_fee or 0)
                            delivery_fee_per_km = float(pricing.price_per_km or 0)
                            delivery_fee_total = delivery_fee_per_km * distance_km
                            total_amount += round(application_fee + service_price + delivery_fee_total, 2)
        
        return {
            'total_rides': total_rides,
            'completed_rides': completed_rides,
            'total_amount': round(total_amount, 2),
            'completion_rate': round((completed_rides / total_rides * 100) if total_rides > 0 else 0, 2)
        }

    def _calculate_distance(self, lat1, lon1, lat2, lon2):
        """
        Calculate the great-circle distance in kilometers between two points
        on the Earth specified by latitude and longitude.
        """
        import math
        R = 6371.0  # Radius of Earth in kilometers
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        d_phi = math.radians(lat2 - lat1)
        d_lambda = math.radians(lon2 - lon1)

        a = math.sin(d_phi / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        return round(R * c, 2)


from django.http import HttpResponse
from .models import PlatformSettings

def dashboard_logo(request):
    settings = PlatformSettings.objects.first()
    if settings and settings.platform_logo:
        with open(settings.platform_logo.path, 'rb') as f:
            return HttpResponse(f.read(), content_type="image/png")  # Adjust content type as needed
    else:
        return HttpResponse(status=404)
    
from django.shortcuts import render

def notification_test_view(request):
    return render(request, 'admin/notifications_test.html')



from django.http import JsonResponse
from pyfcm import FCMNotification

from django.http import JsonResponse
from pyfcm import FCMNotification

def test_notification(request):
    try:
        send_fcm_notification(
            token='d28d_rtvHpvO6K_eShNOYD:APA91bF2GPBnuq7boFdQSwYkVNapumUomUKJUkke6lDIU1_5MDV1-UWePFqO-HMRU7sx55O-1g2flRUXl2mxewciHN45VE2bCDS18Z-XIz96gEjDTKpmzUg',
            title='Test Notification',
            body='This is a test notification from the Django app.',
            data={
                "type": "test_notification",
                "message": "This is a test message",
            }
        )
        
        return JsonResponse({
            "status": "success",
            "message": "Notification sent successfully"
        })
        
    except Exception as e:
        print(f"Error sending notification: {e}")
        return JsonResponse({
            "status": "error",
            "message": str(e)
        }, status=500)