import os
from pathlib import Path
from dotenv import load_dotenv
import firebase_admin
from django.utils.translation import gettext_lazy as _

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv("SECRET_KEY")

DEBUG = True

ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS").split(",")

CSRF_TRUSTED_ORIGINS = [
    "https://ridenew-production-41e4.up.railway.app",
    "http://ridenew-production-41e4.up.railway.app/",
]

INSTALLED_APPS = [
    'simpleui',
    'django.contrib.admin',
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "authentication",
    "location_field.apps.DefaultConfig",
    "rest_framework",
    "rest_framework.authtoken",
    "fcm_django",
    "django_filters",
    "channels",
    "core",
    #"django.contrib.gis"
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    'django.middleware.locale.LocaleMiddleware',
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "project.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

ASGI_APPLICATION = "project.asgi.application"
WSGI_APPLICATION = "project.wsgi.application"

if DEBUG:
    # DATABASES = {
    #     'default': {
    #         'ENGINE': 'django.contrib.gis.db.backends.postgis',
    #         'NAME': 'ride_db',
    #         'USER': 'postgres',
    #         'PASSWORD': 'cyparta@2024',
    #         'HOST': 'localhost',
    #         'PORT': '5432',
    #     }
    # }


    # DATABASES = {
    #     'default': {
    #         'ENGINE': 'django.db.backends.mysql',
    #         'NAME': 'scooter',
    #         'USER': 'root',
    #         'PASSWORD': 'cyparta@2024',
    #         'HOST':'localhost',
    #         'PORT':'3306',
    #     }
    # }
    # DATABASES = {
    #     "default": {
    #         "ENGINE": "django.db.backends.sqlite3",
    #         "NAME": os.path.join(BASE_DIR, "db.sqlite3"),
    #     }
    # }
    DATABASES = {
        "default": {
            'ENGINE': 'django.db.backends.postgresql',
            "NAME": "railway",  # Replace with your actual DB name
            "USER": "postgres",  # Replace with your actual DB user
            "PASSWORD": "hscKMhKfGhnAqhaLoToyYiaywiDCNEct",  # Replace with your actual DB password
            "HOST": "postgres.railway.internal",  # Use Railway's host
            "PORT": "5432",  # PostgreSQL default por
        }
    }
    
    # CHANNEL_LAYERS = {
    #     "default": {
    #         "BACKEND": "channels_redis.core.RedisChannelLayer",
    #         "CONFIG": {
    #             "hosts": [("127.0.0.1", 6379)],#192.168.1.8, 192.168.1.23
    #             # "prefix": "gradcam",
    #         },
    #     },
    # }

    # settings.py or your appropriate config file

    REDIS_USER = "default"
    REDIS_PASSWORD = "kfckXuBMZDDwGNqnmriCUkxqOBpbPrqH"
    REDIS_HOST = "redis.railway.internal"
    REDIS_PORT = 6379
    REDIS_DB = 0

    REDIS_URL = f"redis://{REDIS_USER}:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"

    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels_redis.core.RedisChannelLayer",
            "CONFIG": {
                "hosts": [REDIS_URL],
            },
        },
    }




    
else:
    DATABASES = {
        "default": {
            "ENGINE": os.getenv("POSTGRES_ENGINE"),
            "NAME": os.getenv("POSTGRES_DB"),
            "USER": os.getenv("POSTGRES_USER"),
            "PASSWORD": os.getenv("POSTGRES_PASSWORD"),
            "HOST": os.getenv("POSTGRES_HOSTNAME"),
            "PORT": os.getenv("POSTGRES_PORT"),
        }
    }

    REDIS_HOST = os.getenv("REDIS_HOST")
    REDIS_PORT = os.getenv("REDIS_PORT")
    REDIS_DB = os.getenv("REDIS_DB")
    REDIS_PASSWORD = os.getenv("REDIS_PASSWORD")
    REDIS_URL = f"redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"

    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels_redis.core.RedisChannelLayer",
            "CONFIG": {
                "hosts": [REDIS_URL],
            },
        },
    }

    CELERY_BROKER_URL = REDIS_URL
    CELERY_RESULT_BACKEND = REDIS_URL
    CELERY_REDBEAT_REDIS_URL = REDIS_URL
    CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
    CELERY_WORKER_SEND_TASK_EVENTS = True

AUTH_USER_MODEL = "authentication.User"

LANGUAGES = [
    ('en', 'English'),
    ('ar', 'العربية'),
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
LOCALE_PATHS = [BASE_DIR / "locale"]  # Ensure you have this line

STATIC_URL = "static/"
STATIC_ROOT = os.path.join(BASE_DIR, "static")

MEDIA_URL = "media/"
MEDIA_ROOT = os.path.join(BASE_DIR, "media")

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.TokenAuthentication",
    ],
    "EXCEPTION_HANDLER": "project.exception_handler.custom_exception_handler",
    "COERCE_DECIMAL_TO_STRING": False,
}

try:
    firebase_admin.get_app()
except ValueError:
    FCM_CREDENTIALS_PATH = os.path.join(
        BASE_DIR, "rides-7fe48-firebase-adminsdk-fbsvc-1f06aadce5.json"
    )
    cred = firebase_admin.credentials.Certificate(FCM_CREDENTIALS_PATH)
    firebase_admin.initialize_app(cred)

FCM_DJANGO_SETTINGS = {
    "ONE_DEVICE_PER_USER": True,
    "DELETE_INACTIVE_DEVICES": True,
}

# SimpleUI Settings
SIMPLEUI_HOME_INFO = False
SIMPLEUI_ANALYSIS = False
SIMPLEUI_HOME_QUICK = True
SIMPLEUI_HOME_ACTION = True
SIMPLEUI_DEFAULT_THEME = 'admin.lte.css'

SIMPLEUI_CONFIG = {
    'system_keep': False,
    'menu_display': [_('Authentication'), _('Products'), _('Points'), _('Purchases')],
    'dynamic': True,
    'menus': [
        {
            'name': _('Authentication'),
            'icon': 'fas fa-users',
            'models': [
                {
                    'name': _('Users'),
                    'icon': 'fas fa-user',
                    'url': 'authentication/user/'
                },
                {
                    'name': _('Providers'),
                    'icon': 'fas fa-store',
                    'url': 'authentication/provider/'
                },
                {
                    'name': _('Customers'),
                    'icon': 'fas fa-user-tie',
                    'url': 'authentication/customer/'
                },
                {
                    'name': _('Drivers'),
                    'icon': 'fas fa-car',
                    'url': 'authentication/driver/'
                },
                {
                    'name': _('Tokens'),
                    'icon': 'fas fa-key',
                    'url': 'authtoken/token/',
                }
            ]
        },
        {
            'name': _('Products'),
            'icon': 'fas fa-shopping-bag',
            'models': [
                {
                    'name': _('Products'),
                    'icon': 'fas fa-box',
                    'url': 'authentication/product/'
                },
                {
                    'name': _('Product Images'),
                    'icon': 'fas fa-images',
                    'url': 'authentication/productimage/'
                }
            ]
        },
        {
            'name': _('Points'),
            'icon': 'fas fa-coins',
            'models': [
                {
                    'name': _('User Points'),
                    'icon': 'fas fa-wallet',
                    'url': 'authentication/userpoints/'
                }
            ]
        },
        {
            'name': _('Purchases'),
            'icon': 'fas fa-shopping-cart',
            'models': [
                {
                    'name': _('Purchase History'),
                    'icon': 'fas fa-history',
                    'url': 'authentication/purchase/'
                }
            ]
        }
    ]
}

# Customize SimpleUI theme colors
SIMPLEUI_DEFAULT_THEME = 'admin.lte.css'
SIMPLEUI_LOGO = 'https://your-logo-url.com/logo.png'  # Replace with your logo URL

# Customize SimpleUI sidebar
SIMPLEUI_HOME_TITLE = _('Ride Store Dashboard')
SIMPLEUI_HOME_ICON = 'fa fa-store'
SIMPLEUI_INDEX = _('Dashboard')

# Customize SimpleUI login page
SIMPLEUI_LOGIN_PARTICLES = True
