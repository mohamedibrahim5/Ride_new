from authentication.models import Provider
from django.db.models import Case, When
from geopy.distance import geodesic
import django_filters


class ProviderFilter(django_filters.FilterSet):
    location = django_filters.CharFilter(method="filter_by_location")

    class Meta:
        model = Provider
        fields = ["location"]

    def filter_by_location(self, queryset, name, value):
        if not value:
            return queryset

        user_coordinates = tuple(map(float, value.split(",")))

        providers_with_distance = []

        for provider in queryset:
            provider_coordinates = tuple(map(float, provider.user.location.split(",")))

            distance = geodesic(user_coordinates, provider_coordinates).km

            providers_with_distance.append((provider.id, distance))

        sorted_ids = [
            pid for pid, _ in sorted(providers_with_distance, key=lambda x: x[1])
        ]

        preserved_order = Case(
            *[When(id=pid, then=pos) for pos, pid in enumerate(sorted_ids)]
        )

        return queryset.filter(id__in=sorted_ids).order_by(preserved_order)
