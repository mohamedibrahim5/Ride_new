import requests, pyotp
from firebase_admin import messaging

from authentication.models import Provider, Customer


def send_sms(phone):
    # url = "http://messaging.cyparta.com/api/send-sms/"
    #
    # otp = pyotp.TOTP("base32secret3232").now()
    #
    # payload = {
    #     "phone_number": phone,
    #     "message": f"Your otp is {otp}.",
    #     "api_key": "156980c511bdebbd3d073f672bfe951287dbf842bfe89148d12bc9f76e79fda7",
    # }
    #
    # try:
    #     response = requests.post(url, json=payload)
    #     success = response.json().get("success", False)
    #     return  otp if success else None
    # except requests.exceptions.HTTPError:
    #     return None
    return "123456"


def send_fcm_notification(token, title, body):
    message = messaging.Message(
        notification=messaging.Notification(
            title=title,
            body=body,
        ),
        token=token,
    )

    try:
        response = messaging.send(message)
        print("Successfully sent message:", response)
        return response
    except Exception as e:
        print("Error sending message:", e)
        return None


def retrieve_object(user):
    if user.role == "CU":
        return Customer.objects.select_related("user").get(user=user)
    elif user.role == "PR":
        return Provider.objects.select_related("user").get(user=user)
    # If provider has a driver profile, return it
    elif hasattr(user, 'provider') and hasattr(user.provider, 'driver_profile'):
        return user.provider.driver_profile
    return None


def extract_user_data(initial_data):
    return {
        "name": initial_data.get("name"),
        "phone": initial_data.get("phone"),
        "email": initial_data.get("email"),
        "password": initial_data.get("password"),
        "image": initial_data.get("image"),
        "location": initial_data.get("location"),
        "role": initial_data.get("role"),
    }


def update_user_data(instance, initial_data):
    return {
        "name": initial_data.get("name", instance.user.name),
        "email": initial_data.get("email", instance.user.email),
        "image": initial_data.get("image", instance.user.image),
        "location": initial_data.get("location", instance.user.location),
    }
