# core/context_processors.py

def simpleui_context(request):
    from authentication.models import PlatformSettings

    platform = PlatformSettings.objects.first()

    return {
        "SIMPLEUI_HOME_TITLE": platform.platform_name if platform else "Ride Store Dashboard",
        "SIMPLEUI_LOGO": platform.platform_logo.url if platform and platform.platform_logo else "https://default-logo.com/logo.png"
    }
