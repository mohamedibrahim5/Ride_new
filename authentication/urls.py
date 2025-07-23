from authentication.views import (
    UserRegisterView,
    LoginView,
    SendOtpView,
    VerifyOtpView,
    ResetPasswordView,
    ChangePasswordView,
    ProfileUserView,
    ProfileUpdateView,
    RideHistoryView,
    FcmDeviceView,
    LogoutView,
    DeleteUserView,
    ServiceViewSet,
    DriverCarViewSet,
    CustomerPlaceViewSet,
    ProviderViewSet,
    RequestProviderView,
    StartRideRequestView,
    BroadcastRideRequestView,
    ProviderRideResponseView,
    UpdateRideStatusView,
    ProductViewSet,
    PurchaseViewSet,
    UserPointsViewSet,
    CarAgencyViewSet, 
    CarAvailabilityViewSet, 
    CarRentalViewSet,
    DriverProfileViewSet, 
    NearbyRideRequestsView,
    DriverLocationUpdateView,
    ClientCancelRideView,
    NotificationListView,
    NotificationMarkAsReadView,
    UnreadNotificationCountView,
    RateRideView,
    RideRatingView,
    ProviderServicePricingViewSet,
    ProviderAutocomplete,
    ServiceAutocomplete,
)
from django.urls import path, include
from rest_framework.routers import DefaultRouter


router = DefaultRouter()
router.register("services", ServiceViewSet, basename="services")
router.register("providers", ProviderViewSet, basename="providers")
router.register("driver-cars", DriverCarViewSet, basename="driver-cars")
router.register("customer-places", CustomerPlaceViewSet, basename="customer-places")
router.register(r'products', ProductViewSet, basename='product')
router.register(r'purchases', PurchaseViewSet, basename='purchase')
router.register(r'points', UserPointsViewSet, basename='points')
router.register(r'cars', CarAgencyViewSet)
router.register(r'availability', CarAvailabilityViewSet)
router.register(r'rentals', CarRentalViewSet)
router.register("driver-profiles", DriverProfileViewSet, basename="driver-profiles")
router.register("service-pricing", ProviderServicePricingViewSet, basename="service-pricing")
router.register("pricing-zones", PricingZoneViewSet, basename="pricing-zones")


urlpatterns = [
    path("register/", UserRegisterView.as_view(), name="register"),
    path("login/", LoginView.as_view(), name="login"),
    path("send-otp/", SendOtpView.as_view(), name="send-otp"),
    path("verify-otp/", VerifyOtpView.as_view(), name="verify-otp"),
    path("reset-password/", ResetPasswordView.as_view(), name="reset-password"),
    path("change-password/", ChangePasswordView.as_view(), name="change-password"),
    path("profile/", ProfileUserView.as_view(), name="profile"),
    path("profile/update/", ProfileUpdateView.as_view(), name="profile-update"),
    path("rides/history/", RideHistoryView.as_view(), name="ride-history"),
    path("fcm-device/", FcmDeviceView.as_view(), name="fcm-device"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("delete/", DeleteUserView.as_view(), name="delete-user"),
    path("", include(router.urls)),
    path("request-provider/", RequestProviderView.as_view(), name="request-provider"),

    path("start-ride/", StartRideRequestView.as_view(), name="start-ride"),

    #a7aa7a 
    path("book-ride/", BroadcastRideRequestView.as_view(), name="book-ride"),
    path("ride/respond/", ProviderRideResponseView.as_view(), name="provider_ride_response"),
    path("update-ride/", UpdateRideStatusView.as_view(), name="update_ride" ),
    path("provider/nearby-rides/", NearbyRideRequestsView.as_view(), name="nearby-rides"),
    path("provider/update-location/", DriverLocationUpdateView.as_view(), name="provider_update_location"),
    path("cancel-ride/", ClientCancelRideView.as_view(), name="cancel-ride"),  # New URL


    path('notifications/', NotificationListView.as_view(), name='notification-list'),
    path('notifications/<int:pk>/mark-as-read/', NotificationMarkAsReadView.as_view(), name='notification-mark-read'),
    path('notifications/unread-count/', UnreadNotificationCountView.as_view(), name='unread-notification-count'),

    path('rides/<int:ride_id>/rate/', RateRideView.as_view(), name='rate-ride'),
    path('rides/<int:ride_id>/rating/', RideRatingView.as_view(), name='ride-rating'),
    path('provider-autocomplete/', ProviderAutocomplete.as_view(), name='provider-autocomplete'),
    path('service-autocomplete/', ServiceAutocomplete.as_view(), name='service-autocomplete'),
    path('calculate-price/', CalculatePriceView.as_view(), name='calculate-price'),




]
