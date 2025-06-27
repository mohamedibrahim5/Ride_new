from django.utils.translation import gettext_lazy as _

ROLE_CUSTOMER = "CU"
ROLE_PROVIDER = "PR"
ROLE_ADMIN = "AD"


ROLE_CHOICES = (
    (ROLE_CUSTOMER, _("Customer")),
    (ROLE_PROVIDER, _("Provider")),
    (ROLE_ADMIN, _("Admin")),
)


FCM_IOS = "ios"
FCM_ANDROID = "android"
FCM_WEB = "web"


FCM_CHOICES = (
    (FCM_IOS, "iOS"),
    (FCM_ANDROID, "Android"),
    (FCM_WEB, "Web"),
)
