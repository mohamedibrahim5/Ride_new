ROLE_CUSTOMER = "CU"
ROLE_DRIVER = "DR"
ROLE_CAR_AGENCY = "CA"
ROLE_PROVIDER = "PR"
ROLE_ADMIN = "AD"


ROLE_CHOICES = (
    (ROLE_CUSTOMER, "Customer"),
    (ROLE_DRIVER, "Driver"),
    (ROLE_CAR_AGENCY, "Car Agency"),
    (ROLE_PROVIDER, "Provider"),
    (ROLE_ADMIN, "Admin"),
)


FCM_IOS = "ios"
FCM_ANDROID = "android"
FCM_WEB = "web"


FCM_CHOICES = (
    (FCM_IOS, "iOS"),
    (FCM_ANDROID, "Android"),
    (FCM_WEB, "Web"),
)
