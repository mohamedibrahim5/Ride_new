import requests, pyotp
from firebase_admin import messaging
import logging


from authentication.models import Provider, Customer
from .models import Notification



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


def send_fcm_notification(token, title, body, data=None):
    """
    Sends an FCM notification to a specific device.

    Args:
        token (str): The FCM device token.
        title (str): Notification title.
        body (str): Notification body.
        data (dict, optional): Custom data payload.

    Returns:
        str or None: Message ID if sent successfully, None otherwise.
    """
    try:
        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=body,
            ),
            token=token,
            data=data or {}
        )

        response = messaging.send(message)
        logging.info(f"Successfully sent FCM message: {response}")
        return response

    except messaging.ApiCallError as e:
        # Firebase API-specific errors
        logging.error(f"FCM API error: {e.code} - {e.message}")
    except Exception as e:
        logging.exception(f"Unexpected error sending FCM message: {e}")

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


def create_notification(user, title, message, notification_type='general', data=None):
    """
    Creates a new notification for a user
    """
    notification = Notification.objects.create(
        user=user,
        title=title,
        message=message,
        notification_type=notification_type,
        data=data or {}
    )
    return notification