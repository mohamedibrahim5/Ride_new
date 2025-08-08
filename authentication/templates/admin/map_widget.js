function initMap() {
    var map = new google.maps.Map(document.getElementById('map'), {
        center: {lat: 30.0444, lng: 31.2357}, // Default center (e.g., Cairo)
        zoom: 10
    });

    var drawingManager = new google.maps.drawing.DrawingManager({
        drawingMode: google.maps.drawing.OverlayType.POLYGON,
        drawingControl: true,
        polygonOptions: {
            editable: true
        }
    });
    drawingManager.setMap(map);

    var polygon;
    var boundariesInput = document.getElementById('id_boundaries');

    // Load existing boundaries if any
    if (boundariesInput.value) {
        var boundaries = JSON.parse(boundariesInput.value);
        if (boundaries && boundaries.length > 0) {
            var path = boundaries.map(function(coord) {
                return new google.maps.LatLng(coord.lat, coord.lng);
            });
            polygon = new google.maps.Polygon({
                paths: path,
                editable: true
            });
            polygon.setMap(map);
            var bounds = new google.maps.LatLngBounds();
            path.forEach(function(point) {
                bounds.extend(point);
            });
            map.fitBounds(bounds);
        }
    }

    google.maps.event.addListener(drawingManager, 'polygoncomplete', function(poly) {
        if (polygon) {
            polygon.setMap(null);
        }
        polygon = poly;
        updateBoundaries();
    });

    function updateBoundaries() {
        if (polygon) {
            var path = polygon.getPath();
            var boundaries = [];
            path.forEach(function(latLng) {
                boundaries.push({lat: latLng.lat(), lng: latLng.lng()});
            });
            boundariesInput.value = JSON.stringify(boundaries);
        }
    }

    if (polygon) {
        google.maps.event.addListener(polygon.getPath(), 'set_at', updateBoundaries);
        google.maps.event.addListener(polygon.getPath(), 'insert_at', updateBoundaries);
        google.maps.event.addListener(polygon.getPath(), 'remove_at', updateBoundaries);
    }
}