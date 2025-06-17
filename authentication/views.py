from authentication.filters import ProviderFilter
from authentication.models import (
    Provider,
    Driver,
    Customer,
    Service,
    DriverCar,
    CustomerPlace,
    Product,
    Purchase,
    UserPoints,
    Token,
)
from authentication.serializers import (
    UserSerializer,
    LoginSerializer,
    SendOtpSerializer,
    VerifyOtpSerializer,
    ResetPasswordSerializer,
    ChangePasswordSerializer,
    ProviderSerializer,
    DriverSerializer,
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
    TokenSerializer,
)
from authentication.choices import ROLE_CUSTOMER, ROLE_DRIVER, ROLE_PROVIDER
from authentication.permissions import IsAdminOrReadOnly, IsCustomer, IsCustomerOrAdmin
from rest_framework import status, generics, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.decorators import action
import math
import random
import string


class UserRegisterView(generics.CreateAPIView):
    def get_serializer_class(self):
        role = self.request.data.get("role")

        if role == "CU":
            return CustomerSerializer
        elif role == "DR":
            return DriverSerializer
        elif role == "PR":
            return ProviderSerializer

        return UserSerializer


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

from authentication.models import RideStatus, User, Customer, Driver, Provider
from authentication.serializers import (
    CustomerSerializer,
    DriverSerializer,
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
            return DriverSerializer
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


class DriverCarViewSet(viewsets.ModelViewSet):
    queryset = DriverCar.objects.select_related("driver__user")
    serializer_class = DriverCarSerializer
    permission_classes = [IsAuthenticated]

    def get_serializer_context(self):
        return super().get_serializer_context() | {"user": self.request.user}


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
            service__id=service_id,
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
                service_id=service_id,
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
            service__id=service_id,
            user__location2_lat__isnull=False,
            user__location2_lng__isnull=False
        )

        # Filter providers within 5 km using Haversine
        nearby_providers = []
        for provider in providers:
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

        if not (lat and lng and service_id):
            return Response({"error": "lat, lng, and service_id are required."}, status=400)

        lat = float(lat)
        lng = float(lng)

        providers = Provider.objects.filter(
            is_verified=True,
            service_id=service_id,
            user__location2_lat__isnull=False,
            user__location2_lng__isnull=False
        )

        # Filter providers within 5 km using Haversine
        nearby_providers = []
        for provider in providers:
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
            status="pending"
        )    

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
        else:
            ride.status = "cancelled"
            ride.save()

        # Notify client
        async_to_sync(get_channel_layer().group_send)(
            f"user_{client_id}",
            {
                "type": "send_acceptance" if accepted else "send_cancel",
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
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['is_active', 'provider']

    def get_queryset(self):
        queryset = super().get_queryset()
        # Only show products for providers with service name 'online store'
        queryset = queryset.filter(provider__service__name__icontains='store')
        if self.request.user.role == ROLE_PROVIDER:
            return queryset.filter(provider__user=self.request.user)
        return queryset.filter(is_active=True)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context


class PurchaseViewSet(viewsets.ModelViewSet):
    serializer_class = PurchaseSerializer

    def get_permissions(self):
        if self.action == 'create':
            return [IsAuthenticated(), IsCustomer()]
        return [IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        if hasattr(user, 'customer'):
            return Purchase.objects.filter(customer__user=user)
        elif hasattr(user, 'provider'):
            return Purchase.objects.filter(product__provider__user=user)
        return Purchase.objects.none()

    def create(self, request, *args, **kwargs):
        if not hasattr(request.user, 'customer'):
            return Response(
                {"detail": "Only customers can make purchases."},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().create(request, *args, **kwargs)


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


class TokenViewSet(viewsets.ModelViewSet):
    queryset = Token.objects.all()
    serializer_class = TokenSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'post', 'delete']  # Only allow these methods

    def get_queryset(self):
        if self.request.user.is_staff:
            return Token.objects.all()
        return Token.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        # Generate a random token key
        key = ''.join(random.choices(string.ascii_letters + string.digits, k=40))
        serializer.save(user=self.request.user, key=key)

    def perform_destroy(self, instance):
        # Instead of deleting, just deactivate the token
        instance.is_active = False
        instance.save()
