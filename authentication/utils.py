import requests, pyotp
from firebase_admin import messaging
import logging


from authentication.models import Provider, Customer
from .models import Notification, RideStatus, ProviderServicePricing, WhatsAppAPISettings



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


####  Whatsapp Buissness   #################
def send_whatsapp_message_Wb(to_number):
    token = 'EAAPPOWkxN58BPLZA5ZCgzoiNIwZCnVwz2CM7jvPaOwtzhKQtin7PRcijCVmsxYI47ftrvZBBVUPhlUTjM8mWJT0j21WjPaB9HZAgXGquoRs0TA3QZAIrfHjs1wIuBYMKcOTo3tNh4Ovf2AZAvbKEOSssRGXIvtAvIWq98VUJk3PcccML5ZCSfK0tOykIiDOLCE0TepSWqZCBSSIMsPNvl0HhQ3KJZCFzXAZAfluPf2n0Ln2ZCCAATQZDZD'
    phone_number_id = '703448656188733'
    url = f'https://graph.facebook.com/v22.0/{phone_number_id}/messages'

    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }

    data = {
        "messaging_product": "whatsapp",
        "to": to_number,
        "type": "template",
        "template": {
            "name": "hello_world",  # Must match the approved template name
            "language": {
                "code": "en_US"
            }
        }
    }

    response = requests.post(url, headers=headers, json=data)
    return response.json()


###################################################################
def send_whatsapp_message(phone, message):
    """
    Send a WhatsApp message using the UltraMsg API.
    
    Args:
        phone (str): The recipient's phone number (international format, no '+')
        message (str): The message text to send
    
    Returns:
        dict: The API response or None on failure
    """
    try:
        # Get the only credentials record
        settings = WhatsAppAPISettings.objects.first()
        if not settings:
            print("WhatsApp API settings not found in the database.")
            return None

        url = f"https://api.ultramsg.com/{settings.instance_id}/messages/chat"
        payload = f"token={settings.token}&to={phone}&body={message}"
        payload = payload.encode('utf8').decode('iso-8859-1')
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}

        response = requests.post(url, data=payload, headers=headers)
        response.raise_for_status()
        return response.json()

    except requests.exceptions.RequestException as e:
        print(f"Error sending WhatsApp message: {e}")
        return None
    
# your_app/load_platform_settings.py
from django.core.exceptions import ImproperlyConfigured
from django.conf import settings

def get_platform_settings():
    try:
        from authentication.models import PlatformSettings
        obj = PlatformSettings.objects.first()
        if obj:
            return {
                "title": obj.platform_name,
                "logo": obj.platform_logo.url if obj.platform_logo else "https://default-logo.com/logo.png",
            }
    except Exception as e:
        # Fallback if DB not ready
        return {
            "title": "Ride Store Dashboard",
            "logo": "https://default-logo.com/logo.png",
        }
