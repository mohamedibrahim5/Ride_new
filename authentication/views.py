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
    CarRental
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
)
from authentication.choices import ROLE_CUSTOMER, ROLE_PROVIDER
from authentication.permissions import IsAdminOrReadOnly, IsCustomer, IsCustomerOrAdmin, IsAdminOrCarAgency, IsStoreProvider, IsAdminOrOwnCarAgency, ProductImagePermission
from rest_framework import status, generics, viewsets, filters
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.decorators import action
import math
import random
import string
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.utils.dateparse import parse_datetime
from rest_framework import serializers
from django.db import models
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from collections import defaultdict
import json
from authentication.signals import set_request_data

def flatten_form_data(data):
    from collections import defaultdict
    import json

    result = defaultdict(dict)
    normal = {}

    for key, value in data.items():
        if '.' in key:
            prefix, subkey = key.split('.', 1)
            # Parse JSON arrays from string if needed
            if isinstance(value, str) and value.startswith('[') and value.endswith(']'):
                try:
                    value = json.loads(value)
                except Exception:
                    pass
            result[prefix][subkey] = value
        else:
            if isinstance(value, str) and value.startswith('[') and value.endswith(']'):
                try:
                    value = json.loads(value)
                except Exception:
                    pass
            normal[key] = value

    for key, val in result.items():
        normal[key] = val
    return normal


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
        return Provider.objects.filter(
            services__id=service_id,
            is_verified=True,
        ).select_related("user")


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
        for provider in providers:
            # Exclude providers whose driver_profile.status is not 'available'
            if hasattr(provider, 'driver_profile') and provider.driver_profile.status != 'available':
                continue
            plat = provider.user.location2_lat
            plng = provider.user.location2_lng
            if plat is not None and plng is not None:
                distance = haversine(lat, lng, plat, plng)
                if distance <= 5:
                    provider.distance = distance
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

        for provider in nearby_providers:
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
                if RideStatus.objects.filter(client_id=request.user.id, accepted=True).exists():
                    # Set customer.in_ride = True
                    if hasattr(request.user, 'customer'):
                        request.user.customer.in_ride = True
                        request.user.customer.save()
                    return Response({"status": "Accepted by provider"})
                sleep(1)

        return Response({"status": "No providers accepted the ride"})    
        





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
                if distance <= 5:
                    provider.distance = distance
                    nearby_providers.append(provider)
        nearby_providers.sort(key=lambda p: p.distance)

        if not nearby_providers:
            return Response({"error": "No nearby providers found."}, status=404)

        # Send to all nearby providers simultaneously
        channel_layer = get_channel_layer()
        client_data = {
            "client_id": request.user.id,
            "client_name": request.user.name,
            "lat": lat,
            "lng": lng,
            "drop_lat": drop_lat,
            "drop_lng": drop_lng,
            "ride_type": ride_type,
            "message": "Ride request from nearby client"
        }

        for provider in nearby_providers:
            async_to_sync(channel_layer.group_send)(
                f"user_{provider.user.id}",
                {
                    "type": "send_apply",
                    "data": client_data
                }
            )

        RideStatus.objects.create(
            client=user,
            provider=None,  # not selected yet
            status="pending",
            service_id=service_id,
            pickup_lat=lat,
            pickup_lng=lng,
            drop_lat=drop_lat,
            drop_lng=drop_lng
        )    
        # Set customer.in_ride = True
        if hasattr(user, 'customer'):
            user.customer.in_ride = True
            user.customer.save()

        return Response({"status": f"Broadcasted ride request to {len(nearby_providers)} nearby providers"})        
    




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

            # Notify client
            async_to_sync(get_channel_layer().group_send)(
                f"user_{client_id}",
                {
                    "type": "send_acceptance",
                    "data": {
                        "provider_id": request.user.id,
                        "accepted": accepted,
                    }
                }
            )
        else:
            ride.status = "cancelled"
            ride.save()

        # Notify client
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

        # --- Update in_ride and driver_profile status for both provider and customer ---
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
        # --- End block ---

        async_to_sync(get_channel_layer().group_send)(
            f"user_{ride.client.id}",
            {
                "type": "ride_status_update",
                "data": {
                    "status": status,
                    "ride_id": ride.id,
                    "provider_id": ride.provider.id if ride.provider else None
                }
            }
        )

        return Response({"status": f"Ride updated to {status}."})


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.select_related('provider__user').prefetch_related('images')
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated, IsStoreProvider]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['is_active', 'provider']

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy', 'upload_image']:
            return [IsAuthenticated(), IsStoreProvider()]
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