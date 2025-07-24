# Zone-Based Pricing System Documentation

## Overview

The zone-based pricing system allows providers to set different pricing rates based on geographical areas. This enables dynamic pricing based on location, time, and demand patterns.

## Features

### 1. Pricing Zones
- **Zone Definition**: Define geographical boundaries using coordinate points
- **Zone Management**: Admin can create, update, and manage pricing zones
- **Point-in-Polygon**: Automatic detection if pickup/drop locations are within specific zones

### 2. Advanced Pricing Structure
- **Base Fare**: Fixed starting price for any ride
- **Price per KM**: Rate charged per kilometer traveled
- **Price per Minute**: Rate charged per minute of ride duration
- **Minimum Fare**: Guaranteed minimum price for any ride
- **Peak Hour Multiplier**: Dynamic pricing during peak hours

### 3. Backward Compatibility
- Legacy pricing fields are maintained for existing implementations
- Automatic fallback to legacy pricing if no zone-based pricing is found

## API Endpoints

### 1. Pricing Zones Management

#### List Pricing Zones
```http
GET /authentication/pricing-zones/
Authorization: Token <your_token>
```

#### Create Pricing Zone (Admin Only)
```http
POST /authentication/pricing-zones/
Authorization: Token <admin_token>
Content-Type: application/json

{
  "name": "Downtown Cairo",
  "description": "Central business district",
  "boundaries": [
    {"lat": 30.0444, "lng": 31.2357},
    {"lat": 30.0500, "lng": 31.2400},
    {"lat": 30.0450, "lng": 31.2450},
    {"lat": 30.0400, "lng": 31.2400}
  ],
  "is_active": true
}
```

### 2. Provider Service Pricing

#### Create Zone-Based Pricing
```http
POST /authentication/service-pricing/
Authorization: Token <provider_token>
Content-Type: application/json

{
  "service": 1,
  "sub_service": "car_repair",
  "zone": 1,
  "base_fare": 10.00,
  "price_per_km": 2.50,
  "price_per_minute": 0.50,
  "minimum_fare": 15.00,
  "peak_hour_multiplier": 1.5,
  "peak_hours_start": "07:00:00",
  "peak_hours_end": "09:00:00",
  "is_active": true
}
```

#### List Provider Pricing
```http
GET /authentication/service-pricing/
Authorization: Token <provider_token>

# Filter by zone
GET /authentication/service-pricing/?zone=1

# Filter by service
GET /authentication/service-pricing/?service=1&is_active=true
```

### 3. Price Calculation

#### Calculate Ride Price
```http
POST /authentication/calculate-price/
Authorization: Token <your_token>
Content-Type: application/json

{
  "pickup_lat": 30.0444,
  "pickup_lng": 31.2357,
  "drop_lat": 30.0500,
  "drop_lng": 31.2400,
  "service_id": 1,
  "sub_service": "car_repair",
  "pickup_time": "2024-01-15T08:30:00Z"
}
```

**Response:**
```json
{
  "pricing_options": [
    {
      "provider_id": 1,
      "provider_name": "Ahmed's Service",
      "zone_name": "Downtown Cairo",
      "total_price": 25.75,
      "distance_km": 2.5,
      "estimated_duration_minutes": 5,
      "pricing_breakdown": {
        "base_fare": 10.00,
        "distance_cost": 6.25,
        "time_cost": 2.50,
        "service_fee": 0.00,
        "minimum_fare": 15.00,
        "peak_multiplier": 1.5
      }
    }
  ],
  "cheapest_option": {
    "provider_id": 1,
    "total_price": 25.75
  },
  "service_name": "Maintenance Service",
  "sub_service": "car_repair"
}
```

## Database Schema

### PricingZone Model
```python
class PricingZone(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    boundaries = models.JSONField()  # Array of {"lat": float, "lng": float}
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
```

### Enhanced ProviderServicePricing Model
```python
class ProviderServicePricing(models.Model):
    # Existing fields
    provider = models.ForeignKey(Provider)
    service = models.ForeignKey(Service)
    sub_service = models.CharField(max_length=50, blank=True, null=True)
    
    # New zone-based fields
    zone = models.ForeignKey(PricingZone, null=True, blank=True)
    base_fare = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    price_per_km = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    price_per_minute = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    minimum_fare = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    peak_hour_multiplier = models.DecimalField(max_digits=4, decimal_places=2, default=1.0)
    peak_hours_start = models.TimeField(null=True, blank=True)
    peak_hours_end = models.TimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    
    # Legacy fields (maintained for backward compatibility)
    application_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    service_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    delivery_fee_per_km = models.DecimalField(max_digits=10, decimal_places=2, default=0)
```

## Usage Examples

### 1. Setting Up Zones

First, create pricing zones for different areas:

```python
# Downtown zone
downtown_zone = PricingZone.objects.create(
    name="Downtown Cairo",
    description="Central business district with high demand",
    boundaries=[
        {"lat": 30.0444, "lng": 31.2357},
        {"lat": 30.0500, "lng": 31.2400},
        {"lat": 30.0450, "lng": 31.2450},
        {"lat": 30.0400, "lng": 31.2400}
    ],
    is_active=True
)

# Suburban zone
suburban_zone = PricingZone.objects.create(
    name="New Cairo",
    description="Suburban area with lower demand",
    boundaries=[
        {"lat": 30.0200, "lng": 31.4000},
        {"lat": 30.0300, "lng": 31.4100},
        {"lat": 30.0250, "lng": 31.4150},
        {"lat": 30.0150, "lng": 31.4050}
    ],
    is_active=True
)
```

### 2. Setting Up Provider Pricing

```python
# Downtown pricing (higher rates)
ProviderServicePricing.objects.create(
    provider=provider,
    service=maintenance_service,
    sub_service="car_repair",
    zone=downtown_zone,
    base_fare=15.00,
    price_per_km=3.00,
    price_per_minute=0.75,
    minimum_fare=20.00,
    peak_hour_multiplier=1.8,
    peak_hours_start=time(7, 0),
    peak_hours_end=time(9, 0),
    is_active=True
)

# Suburban pricing (lower rates)
ProviderServicePricing.objects.create(
    provider=provider,
    service=maintenance_service,
    sub_service="car_repair",
    zone=suburban_zone,
    base_fare=10.00,
    price_per_km=2.00,
    price_per_minute=0.50,
    minimum_fare=15.00,
    peak_hour_multiplier=1.3,
    peak_hours_start=time(7, 0),
    peak_hours_end=time(9, 0),
    is_active=True
)
```

### 3. Price Calculation Logic

The system automatically:
1. Determines which zone the pickup location falls into
2. Finds the appropriate pricing for that zone
3. Calculates distance and estimated duration
4. Applies peak hour multipliers if applicable
5. Ensures minimum fare requirements are met

### 4. Integration with Existing Ride System

The WebSocket consumers and ride history APIs have been updated to use the new pricing system while maintaining backward compatibility.

## Admin Interface

The Django admin interface has been enhanced with:
- **Pricing Zones Management**: Create and manage geographical zones
- **Enhanced Pricing Interface**: Organized fieldsets for zone-based vs legacy pricing
- **Filtering and Search**: Filter by zone, service, and active status
- **Visual Indicators**: Clear display of which pricing model is being used

## Migration Strategy

1. **Phase 1**: Deploy the new models and admin interface
2. **Phase 2**: Create initial pricing zones for major areas
3. **Phase 3**: Migrate existing providers to zone-based pricing
4. **Phase 4**: Gradually phase out legacy pricing fields

## Benefits

1. **Flexible Pricing**: Different rates for different areas
2. **Dynamic Pricing**: Peak hour multipliers for demand management
3. **Better Revenue**: Optimized pricing based on location and time
4. **Scalability**: Easy to add new zones and pricing models
5. **Backward Compatibility**: Existing implementations continue to work

## Future Enhancements

1. **Real-time Demand Pricing**: Adjust multipliers based on current demand
2. **Weather-based Pricing**: Higher rates during bad weather
3. **Event-based Pricing**: Special rates during events or holidays
4. **Machine Learning**: Predictive pricing based on historical data