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
    CarPurchase,
    Notification,
    Rating,
    ProviderServicePricing,
    PricingZone,
    NameOfCar,
    SubService,
    ScheduledRide,
    CarSaleListing,
    RestaurantModel, ProductCategory, Product, ProductImage,ProductImageRestaurant,ProductRestaurant,
    Cart, CartItem, Order, OrderItem, Coupon, ReviewRestaurant, OfferRestaurant, DeliveryAddress,
    CouponRestaurant
    
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
    CarPurchaseSerializer,
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
    PriceCalculationSerializer,
    ProviderOnlineStatusSerializer,
    NameOfCarSerializer,
    SubServiceSerializer,
    ScheduledRideSerializer,
    CarSaleListingSerializer,
    RestaurantSerializer, CategorySerializer, ProductSerializer, ProductImageSerializer,
    CartSerializer, CartItemSerializer, OrderSerializer, ReviewSerializer, OfferSerializer, DeliveryAddressSerializer, NotificationSerializer,
    ProductRestaurantSerializer, ProductImageRestaurantSerializer,
    CouponRestaurantSerializer
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
from django.conf import settings

import json
from django.http import QueryDict
from django.core.files.uploadedfile import UploadedFile


from django.http import QueryDict
from django.core.files.uploadedfile import UploadedFile
import json

from authentication.utils import set_request_data, clear_request_data, get_request_data
import re


def flatten_form_data(data):
    result = {}
    if not isinstance(data, (QueryDict, dict)):
        return data

    keys = data.keys()

    for key in keys:
        values = data.getlist(key) if isinstance(data, QueryDict) else data.get(key)
        if not isinstance(values, list):
            values = [values]

        if any(isinstance(v, UploadedFile) for v in values):
            parts = key.split('.')
            current = result
            for part in parts[:-1]:
                current = current.setdefault(part, {})
            current[parts[-1]] = values if len(values) > 1 else values[0]
            continue

        value = values if len(values) > 1 else values[0]
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
                if isinstance(parsed, (list, dict)):
                    value = parsed
            except Exception:
                pass

        parts = key.split('.')
        current = result
        for part in parts[:-1]:
            current = current.setdefault(part, {})
        current[parts[-1]] = value

    return result

class UserRegisterView(generics.CreateAPIView):
    def get_serializer_class(self):
        role = self._get_role_from_request_data()
        if role == "CU":
            return CustomerSerializer
        elif role == "PR":
            if self._has_nested_user_data():
                return ProviderDriverRegisterSerializer
            return ProviderSerializer
        return UserSerializer

    def _get_role_from_request_data(self):
        data = get_request_data() or self.request.data
        if isinstance(data.get('user'), dict) and 'role' in data['user']:
            return data['user']['role']
        if 'user.role' in data:
            return data['user.role']
        return data.get('role')

    def _has_nested_user_data(self):
        data = get_request_data() or self.request.data
        return (
            any(k.startswith("user.") for k in data.keys()) or
            isinstance(data.get("user"), dict)
        )

    def _process_request_data(self):
        if self.request.content_type.startswith('multipart/form-data') or \
           self.request.content_type.startswith('application/x-www-form-urlencoded'):
            # Safely build a dict from POST and FILES without deepcopying file objects
            data_dict = {}
            for key in self.request.POST.keys():
                values = self.request.POST.getlist(key)
                data_dict[key] = values if len(values) > 1 else values[0]
            for file_key, file_list in self.request.FILES.lists():
                # Store file(s) directly without deepcopy
                data_dict[file_key] = file_list if len(file_list) > 1 else file_list[0]
            return flatten_form_data(data_dict)
        return self.request.data

    def post(self, request, *args, **kwargs):
        processed_data = self._process_request_data()
        set_request_data(processed_data)
        try:
            serializer = self.get_serializer(data=processed_data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            response_data = self._prepare_response_data(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(response_data, status=status.HTTP_201_CREATED, headers=headers)
        finally:
            clear_request_data()

    def _prepare_response_data(self, serializer):
        response_data = serializer.data
        provider = serializer.instance if hasattr(serializer, 'instance') else None
        if provider is None and 'id' in serializer.data:
            try:
                provider = Provider.objects.get(id=serializer.data['id'])
            except Provider.DoesNotExist:
                provider = None

        if provider and hasattr(provider, 'driver_profile'):
            response_data['driver_profile'] = DriverProfileSerializer(provider.driver_profile).data
            if hasattr(provider.driver_profile, 'car'):
                response_data['car'] = DriverCarSerializer(provider.driver_profile.car).data

        return response_data


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


class SubServiceViewSet(viewsets.ModelViewSet):
    queryset = SubService.objects.all()
    serializer_class = SubServiceSerializer
    permission_classes = [IsAdminOrReadOnly]


class NameOfCarViewSet(viewsets.ModelViewSet):
    queryset = NameOfCar.objects.all()
    serializer_class = NameOfCarSerializer
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
        sub_service_id = self.request.query_params.get("sub_service_id")
        
        print(f"Debug - service_id: {service_id}, sub_service_id: {sub_service_id}")
        
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

        if sub_service_id:
            queryset = queryset.filter(sub_services__id=sub_service_id)
        
        print(f"Providers with service_id {service_id} and verified: {queryset.count()}")
        
        # # Filter by sub_service if provided and service is maintenance
        # if sub_service and service_id:
        #     try:
        #         service = Service.objects.get(pk=service_id)
        #         print(f"Service found: {service.name}")
        #         if 'maintenance' in service.name.lower():
        #             queryset = queryset.filter(sub_service=sub_service)
        #             print(f"After sub_service filter: {queryset.count()}")
        #     except Service.DoesNotExist:
        #         print(f"Service with ID {service_id} not found")
        #         pass
        
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
        name_of_car_id = request.data.get("name_of_car_id", None)
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
        # check if name_of_car_id is not None
        if name_of_car_id:
            name_of_car = NameOfCar.objects.filter(pk=name_of_car_id).first()
            if name_of_car is None:
                return Response({"error": "Invalid name of car ID."}, status=400)
            providers = Provider.objects.filter(
                is_verified=True,
                services__id=service_id,
                user__location2_lat__isnull=False,
                user__location2_lng__isnull=False,
                onLine=True,
                name_of_car=name_of_car,
            )
        else :    
            providers = Provider.objects.filter(
            is_verified=True,
            services__id=service_id,
            user__location2_lat__isnull=False,
            user__location2_lng__isnull=False,
            onLine=True
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
        if name_of_car_id :  
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
            name_of_car_id =   name_of_car if name_of_car else None,
        )  
        else:
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

        # print her request user data to send driver location and driver car
        print("asdmasdas")
        print(dir(request.user))

        providerUser = Provider.objects.filter(user_id=request.user.id).first()
        if providerUser:
            print('providerUser')
            print(vars(providerUser))
            # Access DriverProfile
            driver_profile = getattr(providerUser, 'driver_profile', None)
            if driver_profile:
                print('driverProfile')
                print(vars(driver_profile))
                driver_car = getattr(driver_profile, 'car', None)
                if driver_car:
                    print('driverCar')
                    print(vars(driver_car))
                    driver_car_images = driver_car.images.all()
                    if driver_car_images:
                        print('driverCarImages')
                        for image in driver_car_images:
                            print(vars(image))
                    else:    
                        print('No DriverCarImages found for this car.')    
                else:        
                    print('No DriverCar found for this driver profile.')
            else:   
                print('No DriverProfile found for this provider.')     
        else :
            print('No Provider found for this user.')
        
        

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
                        "provider_phone": request.user.phone,
                        "accepted": accepted,
                        "pickup_lat": ride.pickup_lat,
                        "pickup_lng": ride.pickup_lng,
                        "drop_lat": ride.drop_lat,
                        "drop_lng": ride.drop_lng,
                        "provider_image": request.user.image.url if request.user.image else None,
                        "provider_phone": request.user.phone,
                        "avarage_rating": request.user.average_rating,
                        "car_details": {
                            "type": driver_profile.car.type,
                            "model": driver_profile.car.model,
                            "number": driver_profile.car.number,
                            "color": driver_profile.car.color,
                            "images": [
                                {"id": image.id, "url": image.image.url}
                                for image in driver_profile.car.images.all()
                                ]
                    
                        }
                        if driver_profile and hasattr(driver_profile, 'car') and driver_profile.car
                        else None
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
                    "service_id": ride.service.id if ride.service else None,
                    "pickup_lat": ride.pickup_lat,
                    "pickup_lng": ride.pickup_lng,
                    "drop_lat": ride.drop_lat,
                    "drop_lng": ride.drop_lng,
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
            "ride_id": ride.id,
            # adding price of ride 
            "price" :ride.total_price
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
        
        if provider.onLine is False:
            return Response({"message": "You are not online."}, status=200)

        lat = user.location2_lat
        lng = user.location2_lng
        if lat is None or lng is None:
            return Response({"error": "Provider location is not set."}, status=400)
        
        

        service_ids = provider.services.values_list('id', flat=True)

        pending_rides = RideStatus.objects.filter(
            status="pending",
            service_id__in=service_ids,
            pickup_lat__isnull=False,
            pickup_lng__isnull=False,
            name_of_car_id= provider.name_of_car_id if provider.name_of_car_id else None
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
class CarSaleListingViewSet(viewsets.ModelViewSet):
    queryset = CarSaleListing.objects.select_related('provider__user').prefetch_related('images').all()
    serializer_class = CarSaleListingSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['brand', 'model', 'fuel_type', 'transmission', 'is_active']
    search_fields = ['title', 'brand', 'model', 'description']

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAdminOrCarAgency()]
        return [AllowAny()]

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.user.is_staff:
            return qs
        provider = getattr(self.request.user, 'provider', None)
        if provider and self.action in ['list', 'retrieve']:
            return qs.filter(is_active=True)
        if provider and self.action in ['update', 'partial_update', 'destroy']:
            return qs.filter(provider=provider)
        return qs.filter(is_active=True)


from .permissions import IsProvider,IsProviderOrCustomer

class CarPurchaseViewSet(viewsets.ModelViewSet):
    queryset = CarPurchase.objects.select_related('listing__provider__user', 'customer__user').all()
    serializer_class = CarPurchaseSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.action in ['create']:
            return [IsAuthenticated(), IsCustomer()]
        if self.action in ['update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), IsProvider()]
        return [IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return self.queryset
        if hasattr(user, 'customer'):
            return self.queryset.filter(customer=user.customer)
        provider = getattr(user, 'provider', None)
        if provider:
            return self.queryset.filter(listing__provider=provider)
        return CarPurchase.objects.none()

    def perform_create(self, serializer):
        serializer.save()

    def _ensure_provider_owns_listing(self, instance):
        user = self.request.user
        if user.is_staff:
            return True
        provider = getattr(user, 'provider', None)
        return bool(provider and instance.listing and instance.listing.provider_id == provider.id)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        if not self._ensure_provider_owns_listing(instance):
            return Response({"detail": "Not allowed."}, status=status.HTTP_403_FORBIDDEN)
        response = super().update(request, *args, **kwargs)
        instance.refresh_from_db()
        if instance.status == CarPurchase.STATUS_CONFIRMED and instance.listing:
            if not instance.listing.is_sold:
                instance.listing.is_sold = True
                instance.listing.is_active = False
                instance.listing.save(update_fields=["is_sold", "is_active"])
        if instance.status == CarPurchase.STATUS_CANCELLED:
            instance.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        return response

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        if not self._ensure_provider_owns_listing(instance):
            return Response({"detail": "Not allowed."}, status=status.HTTP_403_FORBIDDEN)
        response = super().partial_update(request, *args, **kwargs)
        instance.refresh_from_db()
        if instance.status == CarPurchase.STATUS_CONFIRMED and instance.listing:
            if not instance.listing.is_sold:
                instance.listing.is_sold = True
                instance.listing.is_active = False
                instance.listing.save(update_fields=["is_sold", "is_active"])
        if instance.status == CarPurchase.STATUS_CANCELLED:
            instance.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        return response

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
from authentication.models import RideStatus, ScheduledRide, Rating, ScheduledRideRating, Customer, Provider
from authentication.serializers import RatingSerializer
from django.db.models import Avg
from rest_framework import status
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

class RateRideView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, ride_id):
        ride = None
        ride_type = None
        
        # Try to find the ride in RideStatus first
        try:
            ride = RideStatus.objects.get(id=ride_id, status='finished')
            ride_type = 'ridestatus'
        except RideStatus.DoesNotExist:
            # Try to find in ScheduledRide
            try:
                ride = ScheduledRide.objects.get(id=ride_id, status='finished')
                ride_type = 'scheduledride'
            except ScheduledRide.DoesNotExist:
                return Response({"error": "Ride not found or not completed."}, status=404)

        if request.user not in [ride.client, ride.provider]:
            return Response({"error": "You are not part of this ride."}, status=403)

        # Get or create rating based on ride type
        if ride_type == 'ridestatus':
            rating, created = Rating.objects.get_or_create(ride=ride)
        else:  # scheduledride
            rating, created = ScheduledRideRating.objects.get_or_create(ride=ride)

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
        """Update user's average ratings for both ride types"""
        if isinstance(user, Provider):
            # Calculate average driver ratings from both Rating and ScheduledRideRating
            ride_ratings = Rating.objects.filter(
                ride__provider=user, 
                driver_rating__isnull=False
            ).values_list('driver_rating', flat=True)
            
            scheduled_ratings = ScheduledRideRating.objects.filter(
                ride__provider=user, 
                driver_rating__isnull=False
            ).values_list('driver_rating', flat=True)
            
            # Combine all ratings
            all_ratings = list(ride_ratings) + list(scheduled_ratings)
            if all_ratings:
                user.average_rating = sum(all_ratings) / len(all_ratings)
                user.total_ratings = len(all_ratings)
                user.save(update_fields=['average_rating', 'total_ratings'])
            
        elif isinstance(user, Customer):
            # Calculate average customer ratings from both Rating and ScheduledRideRating
            ride_ratings = Rating.objects.filter(
                ride__client=user, 
                customer_rating__isnull=False
            ).values_list('customer_rating', flat=True)
            
            scheduled_ratings = ScheduledRideRating.objects.filter(
                ride__client=user, 
                customer_rating__isnull=False
            ).values_list('customer_rating', flat=True)
            
            # Combine all ratings
            all_ratings = list(ride_ratings) + list(scheduled_ratings)
            if all_ratings:
                user.average_rating = sum(all_ratings) / len(all_ratings)
                user.total_ratings = len(all_ratings)
                user.save(update_fields=['average_rating', 'total_ratings'])



                

class ScheduleRideView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not hasattr(request.user, 'customer'):
            return Response({"detail": "Only customers can schedule rides."}, status=403)
        serializer = ScheduledRideSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        scheduled = serializer.save()


        try:
            driver_profile = DriverProfile.objects.get(provider__user=scheduled.provider)
        except DriverProfile.DoesNotExist:
            driver_profile = None

        # Notify provider if chosen
        if scheduled.provider:
            create_notification(
                user=scheduled.provider,
                title="Scheduled Ride Request",
                message=f"You have a scheduled ride request from {request.user.name} at {scheduled.scheduled_time}",
                notification_type='ride_request',
                data={'scheduled_ride_id': scheduled.id}
            )
            # Prepare full scheduled ride payload
            try:
                import json
                from django.core.serializers.json import DjangoJSONEncoder
                scheduled_payload = ScheduledRideSerializer(scheduled).data
                scheduled_payload = json.loads(json.dumps(scheduled_payload, cls=DjangoJSONEncoder))
            except Exception:
                scheduled_payload = {
                    "id": scheduled.id,
                    "client": scheduled.client.id,
                    "provider": getattr(scheduled.provider, 'id', None),
                    "service": scheduled.service.id if scheduled.service else None,
                    "sub_service": scheduled.sub_service.id if scheduled.sub_service else None,
                    "pickup_lat": scheduled.pickup_lat,
                    "pickup_lng": scheduled.pickup_lng,
                    "drop_lat": scheduled.drop_lat,
                    "drop_lng": scheduled.drop_lng,
                    "scheduled_time": scheduled.scheduled_time.isoformat() if scheduled.scheduled_time else None,
                    "status": scheduled.status,
                    "total_price": float(scheduled.total_price) if scheduled.total_price is not None else None,
                    "distance_km": scheduled.distance_km,
                    "duration_minutes": scheduled.duration_minutes,
                    "created_at": scheduled.created_at.isoformat() if scheduled.created_at else None,
                }
            # Serialize driver profile (JSON safe)
            driver_profile_payload = None
            driver_car_payload = None
            if driver_profile:
                try:
                    driver_profile_payload = DriverProfileSerializer(driver_profile).data
                except Exception:
                    driver_profile_payload = {
                        'id': driver_profile.id,
                        'license': driver_profile.license,
                        'status': driver_profile.status,
                        'is_verified': driver_profile.is_verified,
                    }
                # Attach driver's car details if available
                try:
                    if hasattr(driver_profile, 'car') and driver_profile.car:
                        driver_car_payload = DriverCarSerializer(driver_profile.car).data
                except Exception:
                    car = getattr(driver_profile, 'car', None)
                    if car:
                        driver_car_payload = {
                            'type': car.type,
                            'model': car.model,
                            'number': car.number,
                            'color': car.color,
                        }

            async_to_sync(get_channel_layer().group_send)(
                f"user_{scheduled.provider.id}",
                {
                    "type": "send_apply_scheduled_ride",
                    "data": {
                        "type": "scheduled_ride",
                        "scheduled_ride": scheduled_payload,
                        "client_id": request.user.id,
                        "client_name": request.user.name,
                        "provider_phone": request.user.phone,
                        "driver_profile": driver_profile_payload,
                        "driver_car": driver_car_payload
                    }
                }
            )
        return Response(ScheduledRideSerializer(scheduled).data, status=201)


class ProviderScheduledRideAcceptView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        scheduled_ride_id = request.data.get('scheduled_ride_id')
        accept = request.data.get('accept', True)

        from authentication.models import ScheduledRide as SR
        try:
            sr = SR.objects.select_related('client', 'provider').get(id=scheduled_ride_id)
        except SR.DoesNotExist:
            return Response({"detail": "Scheduled ride not found."}, status=404)

        if sr.provider and sr.provider != request.user:
            return Response({"detail": "You are not assigned to this scheduled ride."}, status=403)

        # If no provider assigned yet, assign current provider on accept
        if accept:
            sr.provider = request.user
            sr.status = SR.STATUS_ACCEPTED
            sr.save()

            print("sr.scheduled_time", sr.scheduled_time)

            # Schedule Celery task to start the ride at the scheduled time
            # try:
            #     from authentication.tasks import start_scheduled_ride
            #     start_scheduled_ride.apply_async((sr.id,), eta=sr.scheduled_time)
            # except Exception:
            #     pass

            # why print connection refused 

            try:
                from authentication.tasks import send_notification_and_socket_to_client_and_provider
                print("send_notification_and_socket_to_client_and_provider", sr.scheduled_time)
                send_notification_and_socket_to_client_and_provider(sr.id)
            except Exception as e:
                print("error in send_notification_and_socket_to_client_and_provider", e)
            
                pass

            # Notify client
            create_notification(
                user=sr.client,
                title="Scheduled Ride Accepted",
                message=f"Your scheduled ride at {sr.scheduled_time} was accepted by {request.user.name}",
                notification_type='ride_accepted',
                data={'scheduled_ride_id': sr.id}
            )
            service_data = ServiceSerializer(sr.service).data
            print("service_data", service_data)

            # i want to getting all data from service and passing to async_to_sync(get_channel_layer() 
            
            # Prepare full scheduled ride payload
            try:
                # Ensure JSON-serializable payload (Decimal, datetime, etc.)
                import json
                from django.core.serializers.json import DjangoJSONEncoder
                scheduled_payload = ScheduledRideSerializer(sr).data
                scheduled_payload = json.loads(json.dumps(scheduled_payload, cls=DjangoJSONEncoder))
            except Exception:
                scheduled_payload = {
                    "id": sr.id,
                    "client": sr.client.id,
                    "provider": getattr(sr.provider, 'id', None),
                    "service": sr.service.id if sr.service else None,
                    "sub_service": sr.sub_service.id if sr.sub_service else None,
                    "pickup_lat": sr.pickup_lat,
                    "pickup_lng": sr.pickup_lng,
                    "drop_lat": sr.drop_lat,
                    "drop_lng": sr.drop_lng,
                    "scheduled_time": sr.scheduled_time.isoformat() if sr.scheduled_time else None,
                    "status": sr.status,
                    "total_price": float(sr.total_price) if sr.total_price is not None else None,
                    "distance_km": sr.distance_km,
                    "duration_minutes": sr.duration_minutes,
                    "created_at": sr.created_at.isoformat() if sr.created_at else None,
                }

            async_to_sync(get_channel_layer().group_send)(
                f"user_{sr.client.id}",
                {
                    "type": "send_acceptance",
                    "data": {
                        "type": "scheduled_ride",
                        "scheduled_ride": scheduled_payload,
                        "provider_id": request.user.id,
                        "provider_name": request.user.name,
                        "provider_phone": request.user.phone,
                    }
                }
            )
            return Response({"status": "accepted", "scheduled_ride_id": sr.id})
        else:
            sr.status = SR.STATUS_CANCELLED
            sr.save()
            return Response({"status": "declined", "scheduled_ride_id": sr.id})


class MyScheduledRidesView(APIView):
    permission_classes = [IsAuthenticated]
    filterset_fields = ['status', 'role']

    def get(self, request):
        user = request.user
        
        # Get scheduled rides where user is either client or provider
        scheduled_rides = ScheduledRide.objects.filter(
            models.Q(client=user) | models.Q(provider=user)
        ).select_related(
            'client', 'provider', 'service'
        ).order_by('-scheduled_time')
        
        # Filter by status if provided
        status = request.query_params.get('status')
        if status:
            scheduled_rides = scheduled_rides.filter(status=status)
        
        # Filter by role (customer/driver rides)
        role = request.query_params.get('role')
        if role == 'customer':
            scheduled_rides = scheduled_rides.filter(client=user)
        elif role == 'driver':
            scheduled_rides = scheduled_rides.filter(provider=user)
        
        serializer = ScheduledRideSerializer(scheduled_rides, many=True)
        return Response({
            'scheduled_rides': serializer.data,
            'total_count': scheduled_rides.count()
        })


class UpdateScheduledRideStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        scheduled_ride_id = request.data.get('scheduled_ride_id')
        new_status = request.data.get('status')
        
        valid_statuses = [
            ScheduledRide.STATUS_STARTED,
            ScheduledRide.STATUS_FINISHED,
            ScheduledRide.STATUS_CANCELLED
        ]
        
        if not scheduled_ride_id or new_status not in valid_statuses:
            return Response({
                "error": "scheduled_ride_id and valid status are required. Valid statuses: started, finished, cancelled"
            }, status=400)

        from authentication.models import ScheduledRide as SR
        try:
            scheduled_ride = SR.objects.select_related('client', 'provider').get(id=scheduled_ride_id)
        except SR.DoesNotExist:
            return Response({"error": "Scheduled ride not found."}, status=404)

        # Only the assigned provider can update status
        if scheduled_ride.provider != request.user:
            return Response({"error": "You are not assigned to this scheduled ride."}, status=403)

        # Validate status transitions
        if scheduled_ride.status == SR.STATUS_PENDING:
            return Response({"error": "Cannot update status of pending scheduled ride."}, status=400)
        
        if scheduled_ride.status == SR.STATUS_FINISHED:
            return Response({"error": "Cannot update status of finished scheduled ride."}, status=400)
        
        if scheduled_ride.status == SR.STATUS_CANCELLED:
            return Response({"error": "Cannot update status of cancelled scheduled ride."}, status=400)

        # Update status
        old_status = scheduled_ride.status
        scheduled_ride.status = new_status
        scheduled_ride.save()

        # Handle status-specific logic
        if new_status == SR.STATUS_FINISHED:
            # Mark provider as available again
            provider_profile = getattr(request.user, 'provider', None)
            if provider_profile:
                provider_profile.in_ride = False
                provider_profile.save()
                if hasattr(provider_profile, 'driver_profile'):
                    provider_profile.driver_profile.status = 'available'
                    provider_profile.driver_profile.save()

        # Create notification for client
        status_messages = {
            SR.STATUS_STARTED: "Your scheduled ride has started.",
            SR.STATUS_FINISHED: "Your scheduled ride has been completed.",
            SR.STATUS_CANCELLED: "Your scheduled ride has been cancelled by the provider."
        }
        
        notification_message = status_messages.get(new_status, f"Your scheduled ride status has been updated to {new_status}.")
        
        create_notification(
            user=scheduled_ride.client,
            title="Scheduled Ride Status Update",
            message=notification_message,
            notification_type='ride_status',
            data={
                'scheduled_ride_id': scheduled_ride.id,
                'status': new_status,
                'updated_by': request.user.id
            }
        )

        # Send WebSocket notification
        # Include full scheduled ride payload for clients
        try:
            import json
            from django.core.serializers.json import DjangoJSONEncoder
            scheduled_payload = ScheduledRideSerializer(scheduled_ride).data
            scheduled_payload = json.loads(json.dumps(scheduled_payload, cls=DjangoJSONEncoder))
        except Exception:
            scheduled_payload = {
                "id": scheduled_ride.id,
                "client": scheduled_ride.client.id,
                "provider": getattr(scheduled_ride.provider, 'id', None),
                "service": scheduled_ride.service.id if scheduled_ride.service else None,
                "sub_service": scheduled_ride.sub_service.id if scheduled_ride.sub_service else None,
                "pickup_lat": scheduled_ride.pickup_lat,
                "pickup_lng": scheduled_ride.pickup_lng,
                "drop_lat": scheduled_ride.drop_lat,
                "drop_lng": scheduled_ride.drop_lng,
                "scheduled_time": scheduled_ride.scheduled_time.isoformat() if scheduled_ride.scheduled_time else None,
                "status": scheduled_ride.status,
                "total_price": float(scheduled_ride.total_price) if scheduled_ride.total_price is not None else None,
                "distance_km": scheduled_ride.distance_km,
                "duration_minutes": scheduled_ride.duration_minutes,
                "created_at": scheduled_ride.created_at.isoformat() if scheduled_ride.created_at else None,
            }
        async_to_sync(get_channel_layer().group_send)(
            f"user_{scheduled_ride.client.id}",
            {
                "type": "scheduled_ride_status_update",
                "data": {
                    "type": "scheduled_ride",
                    "scheduled_ride": scheduled_payload,
                    "scheduled_ride_id": scheduled_ride.id,
                    "status": new_status,
                    "message": notification_message,
                    "provider_phone": request.user.phone,
                }
            }
        )

        # Send push notification
        fcm_tokens = list(scheduled_ride.client.fcmdevice_set.values_list('registration_id', flat=True))
        for token in fcm_tokens:
            send_fcm_notification(
                token=token,
                title="Scheduled Ride Status Update",
                body=notification_message,
                data={
                    "type": "scheduled_ride_status_update",
                    "scheduled_ride_id": str(scheduled_ride.id),
                    "status": new_status
                }
            )

        return Response({
            "status": "success",
            "scheduled_ride_id": scheduled_ride.id,
            "old_status": old_status,
            "new_status": new_status,
            "message": f"Scheduled ride status updated from {old_status} to {new_status}"
        })

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

def get_provider_service_pricing(provider, service, sub_service=None):
    try:
        return ProviderServicePricing.objects.get(provider=provider, service=service, sub_service=sub_service)
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
    

class ProviderOnlineStatusUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request):
        provider = get_object_or_404(Provider, user=request.user)
        serializer = ProviderOnlineStatusSerializer(provider, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({"status": "success", "onLine": serializer.data['onLine']})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)    


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
        
        
# core/utils.py
import math

def haversine_distance(lat1, lon1, lat2, lon2):
    # returns distance in kilometers
    if None in (lat1, lon1, lat2, lon2):
        return None
    R = 6371  # Earth radius in km
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c


class RestaurantViewSet(viewsets.ModelViewSet):
    queryset = RestaurantModel.objects.all()
    serializer_class = RestaurantSerializer
    permission_classes = [IsProvider]

    def get_queryset(self):
        # Filter by provider - providers can only see their own restaurants
        if hasattr(self.request.user, 'provider'):
            qs = RestaurantModel.objects.filter(provider=self.request.user.provider)
        else:
            qs = RestaurantModel.objects.none()
        
        # Apply search and filters
        q = self.request.query_params.get('q')
        lat = self.request.query_params.get('lat')
        lng = self.request.query_params.get('lng')
        offer = self.request.query_params.get('offer')
        min_rating = self.request.query_params.get('min_rating')

        if q:
            qs = qs.filter(Q(restaurant_name__icontains=q) | Q(restaurant_description__icontains=q) | Q(categories__name__icontains=q)).distinct()
        if offer in ['1','true','True']:
            qs = qs.filter(offers__active=True).distinct()

        if min_rating:
            try:
                qs = qs.filter(average_rating__gte=float(min_rating))
            except:
                pass

        if lat and lng:
            try:
                lat_f = float(lat); lng_f = float(lng)
                # annotate distance in python after fetch small set
                restaurants = list(qs)
                restaurants.sort(key=lambda r: (haversine_distance(lat_f,lng_f, r.latitude, r.longitude) or 999999))
                return restaurants
            except:
                pass
        return qs

    def perform_create(self, serializer):
        # Automatically assign the restaurant to the current provider
        serializer.save(provider=self.request.user.provider)

    def perform_update(self, serializer):
        # Ensure provider can only update their own restaurant
        if serializer.instance.provider != self.request.user.provider:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("You can only update your own restaurants.")
        serializer.save()

    def perform_destroy(self, instance):
        # Ensure provider can only delete their own restaurant
        if instance.provider != self.request.user.provider:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("You can only delete your own restaurants.")
        instance.delete()

    @action(detail=True, methods=['get'])
    def reviews(self, request, pk=None):
        restaurant = self.get_object()
        qs = restaurant.reviews.all()
        page = self.paginate_queryset(qs)
        if page is not None:
            from .serializers import ReviewSerializer
            serializer = ReviewSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = ReviewSerializer(qs, many=True)
        return Response(serializer.data)

class CategoryViewSet(viewsets.ModelViewSet):
    queryset = ProductCategory.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsProvider]

    def get_queryset(self):
        qs = super().get_queryset()
        restaurant = self.request.query_params.get('restaurant')
        if restaurant:
            qs = qs.filter(restaurant_id=restaurant)
        return qs

class ProductRestaurantViewSet(viewsets.ModelViewSet):
    queryset = ProductRestaurant.objects.prefetch_related('images_restaurant').all()
    serializer_class = ProductRestaurantSerializer
    permission_classes = [IsProviderOrCustomer]

    def get_queryset(self):
        qs = super().get_queryset()
        q = self.request.query_params.get('q')
        category = self.request.query_params.get('category')
        is_offer = self.request.query_params.get('is_offer')
        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(description__icontains=q))
        if category:
            qs = qs.filter(category_id=category)
        if is_offer in ['1','true','True']:
            qs = qs.filter(is_offer=True)
        return qs

class ProductImageViewSet(viewsets.ModelViewSet):
    queryset = ProductImage.objects.all()
    serializer_class = ProductImageSerializer
    permission_classes = [IsProvider]

class ProductImageRestaurantViewSet(viewsets.ModelViewSet):
    queryset = ProductImageRestaurant.objects.all()
    serializer_class = ProductImageRestaurantSerializer
    permission_classes = [IsProvider]

class CartViewSet(viewsets.ViewSet):
    permission_classes = []
    serializer_class = CartSerializer

    def list(self, request):
        user = request.user
        cart, _ = Cart.objects.get_or_create(customer=user)
        serializer = CartSerializer(cart, context={'request': request})
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def add_item(self, request):
        user = request.user
        cart, _ = Cart.objects.get_or_create(customer=user)
        product_id = request.data.get('product_id')
        quantity = int(request.data.get('quantity', 1))
        try:
            product = ProductRestaurant.objects.get(pk=product_id)
        except ProductRestaurant.DoesNotExist:
            return Response({'error':'product not found'}, status=404)
        item, created = CartItem.objects.get_or_create(cart=cart, product=product, defaults={'quantity': quantity})
        if not created:
            item.quantity += quantity
            item.save()
        return Response(CartSerializer(cart).data)

    @action(detail=False, methods=['patch'])
    def update_item(self, request):
        item_id = request.data.get('item_id')
        quantity = int(request.data.get('quantity', 1))
        try:
            item = CartItem.objects.get(pk=item_id, cart__customer=request.user)
        except CartItem.DoesNotExist:
            return Response({'error':'item not found'}, status=404)
        if quantity <= 0:
            item.delete()
        else:
            item.quantity = quantity
            item.save()
        cart = item.cart if hasattr(item, 'cart') else Cart.objects.get(customer=request.user)
        return Response(CartSerializer(cart).data)

    @action(detail=False, methods=['delete'])
    def remove_item(self, request):
        item_id = request.data.get('item_id')
        try:
            item = CartItem.objects.get(pk=item_id, cart__customer=request.user)
            cart = item.cart
            item.delete()
            return Response(CartSerializer(cart).data)
        except CartItem.DoesNotExist:
            return Response({'error':'item not found'}, status=404)

class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all().order_by('-created_at')
    serializer_class = OrderSerializer

    def get_queryset(self):
        user = self.request.user
        return self.queryset.filter(customer=user)

    def create(self, request, *args, **kwargs):
        user = request.user
        cart = Cart.objects.filter(customer=user).first()
        if not cart or cart.items.count() == 0:
            return Response({'error': 'cart empty'}, status=400)

        restaurant_id = request.data.get('restaurant')
        coupon_code = request.data.get('coupon')

        try:
            restaurant = RestaurantModel.objects.get(pk=restaurant_id)
        except RestaurantModel.DoesNotExist:
            return Response({'error': 'restaurant not found'}, status=404)

        order = Order.objects.create(
            customer=user,
            restaurant=restaurant,
            payment_method=request.data.get('payment_method', 'cash')
        )

        # نقل عناصر الكارت
        for ci in cart.items.all():
            OrderItem.objects.create(
                order=order,
                product=ci.product,
                quantity=ci.quantity,
                price=ci.product.display_price
            )

        # Calculate totals before applying coupon
        order.recalc_prices()

        # Apply coupon after totals are calculated
        if coupon_code:
            try:
                coupon = CouponRestaurant.objects.get(code__iexact=coupon_code)
                if coupon.is_valid():
                    discount = (coupon.discount_percentage / 100.0) * order.total_price
                    order.discount = discount
                    order.recalc_prices()
                else:
                    return Response({'error': 'coupon invalid'}, status=400)
            except CouponRestaurant.DoesNotExist:
                return Response({'error': 'coupon not found'}, status=404)

        # تفريغ الكارت
        cart.items.all().delete()

        serializer = OrderSerializer(order)

        # إشعار المطعم (مؤقت)
        # Notification.objects.create(
        #     user=order.restaurant.owner if hasattr(order.restaurant, 'owner') else order.restaurant,
        #     title="New Order",
        #     body=f"New order #{order.id}",
        #     data={'order_id': order.id}
        # )

        return Response(serializer.data, status=201)

    @action(detail=False, methods=['get'], url_path='my-orders', permission_classes=[IsProvider])
    def my_orders(self, request):
        provider = getattr(request.user, 'provider', None)
        if not provider:
            return Response({'detail': 'Provider account required.'}, status=403)

        orders = (
            Order.objects
            .filter(restaurant__provider=provider)
            .order_by('-created_at')
            .prefetch_related('items__product')
        )
        serializer = OrderSerializer(orders, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        order = self.get_object()
        if order.status != 'pending':
            return Response({'error':'cannot cancel after processing'}, status=400)
        order.status = 'cancelled'
        order.save()
        return Response({'status':'cancelled'})
    @action(detail=True, methods=['post'])

    def reorder(self, request, pk=None):
        original = self.get_object()
        user = request.user
        cart, _ = Cart.objects.get_or_create(customer=user)
        # empty old cart if needed or keep
        for oi in original.items.all():
            CartItem.objects.create(cart=cart, product=oi.product, quantity=oi.quantity)
        return Response(CartSerializer(cart).data)

    @action(detail=True, methods=['get'])
    def track(self, request, pk=None):
        order = self.get_object()
        # Placeholder: real location needs driver telemetry
        data = {
            'status': order.status,
            'driver_location': {'latitude': None, 'longitude': None},
            'expected_time_minutes': int(order.expected_order_time.total_seconds()//60)
        }
        return Response(data)

class CouponRestaurantViewSet(viewsets.ModelViewSet):
    queryset = CouponRestaurant.objects.all()
    serializer_class = CouponRestaurantSerializer
    permission_classes = [IsProvider]

    @action(detail=False, methods=['get'])
    def validate(self, request):
        code = request.query_params.get('code')
        if not code:
            return Response({'error':'code required'}, status=400)
        try:
            coupon = CouponRestaurant.objects.get(code__iexact=code)
            return Response({'valid': coupon.is_valid(), 'discount_percentage': coupon.discount_percentage})
        except CouponRestaurant.DoesNotExist:
            return Response({'valid': False}, status=404)

class ReviewViewSet(viewsets.ModelViewSet):
    queryset = ReviewRestaurant.objects.all()
    serializer_class = ReviewSerializer

    def perform_create(self, serializer):
        serializer.save(customer=self.request.user)

class OfferViewSet(viewsets.ModelViewSet):
    queryset = OfferRestaurant.objects.all()
    serializer_class = OfferSerializer
    permission_classes = [IsAdminOrReadOnly]

class AddressViewSet(viewsets.ModelViewSet):
    queryset = DeliveryAddress.objects.all()
    serializer_class = DeliveryAddressSerializer

    def get_queryset(self):
        return self.queryset.filter(customer=self.request.user)

    def perform_create(self, serializer):
        serializer.save(customer=self.request.user)

from django.db.models import Sum, Count, F
from django.utils.timezone import now
class ReportViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def get_queryset(self, request):
        # restrict to restaurant owner
        return Order.objects.filter(restaurant__owner=request.user)

    @action(detail=False, methods=['get'])
    def summary(self, request):
        qs = self.get_queryset(request)
        today = now().date()

        daily_sales = qs.filter(created_at__date=today).aggregate(
            total_orders=Count('id'),
            total_revenue=Sum('total_price')
        )

        monthly_sales = qs.filter(created_at__month=today.month, created_at__year=today.year).aggregate(
            total_orders=Count('id'),
            total_revenue=Sum('total_price')
        )

        total_sales = qs.aggregate(
            total_orders=Count('id'),
            total_revenue=Sum('total_price')
        )

        return Response({
            "daily": daily_sales,
            "monthly": monthly_sales,
            "total": total_sales
        })

    @action(detail=False, methods=['get'])
    def sales(self, request):
        """
        Report grouped by date (daily revenue & order count).
        Query params: ?period=daily OR ?period=monthly
        """
        period = request.query_params.get('period', 'daily')
        qs = self.get_queryset(request)

        if period == 'monthly':
            report = (
                qs.values(year=F('created_at__year'), month=F('created_at__month'))
                  .annotate(total_orders=Count('id'), total_revenue=Sum('total_price'))
                  .order_by('-year', '-month')
            )
        else:  # daily
            report = (
                qs.values(date=F('created_at__date'))
                  .annotate(total_orders=Count('id'), total_revenue=Sum('total_price'))
                  .order_by('-date')
            )

        return Response(report)

    @action(detail=False, methods=['get'])
    def totals(self, request):
        qs = self.get_queryset(request)
        totals = qs.aggregate(
            total_orders=Count('id'),
            total_revenue=Sum('total_price'),
            avg_order_value=Sum('total_price') / Count('id') if qs.exists() else 0
        )
        return Response(totals)

class PublicRestaurantListView(generics.ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = RestaurantSerializer

    def get_queryset(self):
        qs = RestaurantModel.objects.all()
        q = self.request.query_params.get('q')
        min_rating = self.request.query_params.get('min_rating')
        offer = self.request.query_params.get('offer')
        if q:
            qs = qs.filter(Q(restaurant_name__icontains=q) | Q(restaurant_description__icontains=q) | Q(categories__name__icontains=q)).distinct()
        if offer in ['1','true','True']:
            qs = qs.filter(offers__active=True).distinct()
        if min_rating:
            try:
                qs = qs.filter(average_rating__gte=float(min_rating))
            except Exception:
                pass
        return qs

class AgoraTokenView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        channel = request.data.get('channel')
        if not channel:
            return Response({"detail": "channel is required"}, status=400)
        try:
            uid = int(request.data.get('uid') or 0)
        except Exception:
            uid = 0
        expire = int(request.data.get('expire') or 3600)

        app_id = getattr(settings, 'AGORA_APP_ID', None)
        app_cert = getattr(settings, 'AGORA_APP_CERTIFICATE', None)
        if not app_id or not app_cert:
            return Response({"detail": "Agora not configured"}, status=500)

        # Minimal HMAC-based token placeholder. For production, use Agora AccessToken2 builder.
        from time import time
        from hashlib import sha256
        import hmac, base64
        issue_ts = int(time())
        expire_ts = issue_ts + expire
        payload = f"{app_id}:{channel}:{uid}:{expire_ts}".encode()
        sig = hmac.new(app_cert.encode(), payload, sha256).digest()
        token = base64.urlsafe_b64encode(sig + b'.' + payload).decode()

        return Response({
            "appId": app_id,
            "channel": channel,
            "uid": uid,
            "expireAt": expire_ts,
            "token": token,
        })