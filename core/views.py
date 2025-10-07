from django.http import HttpResponse
from django.utils.html import escape
from django.http import JsonResponse
from urllib.parse import quote


def LiveRoomLandingView(request, room_id: str):
    safe_room = escape(room_id)
    canonical_url = request.build_absolute_uri()
    app_link = f"ride://live/{safe_room}?url={quote(canonical_url)}"
    target_path = request.path.lstrip('/')
    referrer = f"utm_source=deeplink&utm_content={target_path}"
    play_url = (
        "https://play.google.com/store/apps/details?id=com.mintops.zynvo"
        f"&referrer={quote(referrer)}"
    )
    html = f"""
<!doctype html>
<html>
  <head>
    <meta charset="utf-8"/>
    <meta name="viewport" content="width=device-width, initial-scale=1"/>
    <title>Join Live Room {safe_room}</title>
    <meta http-equiv="refresh" content="0; url={app_link}">
  </head>
  <body>
    <h1>Join Live Room {safe_room}</h1>
    <p><strong>App link:</strong> <a href="{app_link}">Open in app</a></p>
    <p><strong>Page URL:</strong> <a href="{canonical_url}">{canonical_url}</a></p>
    <p id="store-cta" style="display:none; margin-top:16px;">
      <a href="{play_url}" style="padding:10px 14px; background:#1a73e8; color:#fff; text-decoration:none; border-radius:6px;">Get the app on Google Play</a>
    </p>
    <script>
      setTimeout(function() {{
        var el = document.getElementById('store-cta');
        if (el) el.style.display = 'block';
      }}, 1200);
    </script>
    <p>If the app does not open automatically, tap the button above.</p>
  </body>
 </html>
"""
    return HttpResponse(html)


# Serve .well-known/apple-app-site-association (no extension, JSON content)
def apple_app_site_association(request):
    data = {
        "applinks": {
            "apps": [],
            "details": [
                {
                    # Replace with your iOS App ID: TEAMID.BUNDLEID
                    "appID": "TEAMID.com.example.yourapp",
                    "paths": ["/authentication/live/*", "/live/*"]
                }
            ]
        }
    }
    return JsonResponse(data, safe=False, json_dumps_params={"ensure_ascii": False})


# Serve .well-known/assetlinks.json for Android App Links
def android_assetlinks(request):
    data = [
        {
            "relation": ["delegate_permission/common.handle_all_urls"],
            "target": {
                "namespace": "android_app",
                # Replace with your Android package name and SHA256 cert fingerprint
                "package_name": "com.mintops.zynvo",
                "sha256_cert_fingerprints": [
                    "EC:20:69:E7:4B:EE:93:02:58:C7:58:1E:97:FC:F0:DF:C5:E9:C8:AF:57:23:5D:75:F9:14:64:E6:FC:33:F7:08"
                ]
            }
        }
    ]
    return JsonResponse(data, safe=False, json_dumps_params={"ensure_ascii": False})

from django.shortcuts import render

# Create your views here.
