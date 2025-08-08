from django.forms import Widget
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe
from django.conf import settings

class GoogleMapWidget(Widget):
    class Media:
        js = [
            f'https://maps.googleapis.com/maps/api/js?key={settings.GOOGLE_MAPS_API_KEY}&libraries=drawing,places&callback=initMap',
            'https://cdn.jsdelivr.net/npm/clipboard@2.0.8/dist/clipboard.min.js',
        ]

    def render(self, name, value, attrs=None, renderer=None):
        context = {
            'name': name,
            'value': value or '[]',
            'google_maps_api_key': settings.GOOGLE_MAPS_API_KEY,
        }
        return mark_safe(render_to_string('admin/google_map_widget.html', context))