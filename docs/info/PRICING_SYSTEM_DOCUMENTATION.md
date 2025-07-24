# Enhanced Zone-Based Pricing System Documentation

## Overview

The enhanced pricing system now includes application fees and has been simplified by removing the provider dependency, making it a centralized pricing system that applies to all providers offering the same service in the same zone.

## Key Changes Made

### 1. **Removed Provider Dependency**
- **Why**: Having provider-specific pricing was creating complexity and inconsistency
- **Benefit**: Centralized pricing ensures fair and consistent rates for customers
- **Result**: One pricing rule per service/sub-service/zone combination

### 2. **Added Application Fees**
- **Platform Fee**: Fixed fee charged by the platform (e.g., 5.00 EGP)
- **Service Fee**: Additional service fee (e.g., 2.00 EGP)  
- **Booking Fee**: One-time booking fee (e.g., 3.00 EGP)

### 3. **Simplified Pricing Structure**
```
Total Price = (Base Fare + Distance Cost + Time Cost) × Peak Multiplier + Application Fees
Final Price = max(Total Price, Minimum Fare)
```

## New Pricing Model Structure

### Application Fees
```json
{
  "platform_fee": 5.00,     // Fixed platform commission
  "service_fee": 2.00,      // Service handling fee
  "booking_fee": 3.00       // One-time booking fee
}
```

### Zone-Based Pricing
```json
{
  "base_fare": 10.00,       // Starting price
  "price_per_km": 2.50,     // Per kilometer rate
  "price_per_minute": 0.50, // Per minute rate
  "minimum_fare": 15.00,    // Minimum total
  "peak_hour_multiplier": 1.5
}
```

## API Usage Examples

### 1. Create Centralized Pricing (Admin Only)
```http
POST /authentication/service-pricing/
Authorization: Token <admin_token>
Content-Type: application/json

{
  "service": 1,
  "sub_service": "car_repair",
  "zone": 1,
  "platform_fee": 5.00,
  "service_fee": 2.00,
  "booking_fee": 3.00,
  "base_fare": 10.00,
  "price_per_km": 2.50,
  "price_per_minute": 0.50,
  "minimum_fare": 20.00,
  "peak_hour_multiplier": 1.5,
  "peak_hours_start": "07:00:00",
  "peak_hours_end": "09:00:00"
}
```

### 2. Calculate Price with Application Fees
```http
POST /authentication/calculate-price/
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
  "service_name": "Maintenance Service",
  "sub_service": "car_repair",
  "zone_name": "Downtown Cairo",
  "total_price": 43.25,
  "distance_km": 2.5,
  "estimated_duration_minutes": 5,
  "pricing_breakdown": {
    "base_fare": 10.00,
    "distance_cost": 6.25,      // 2.5km × 2.50
    "time_cost": 2.50,          // 5min × 0.50
    "subtotal": 18.75,
    "peak_multiplier": 1.5,
    "subtotal_after_peak": 28.13, // 18.75 × 1.5
    "platform_fee": 5.00,
    "service_fee": 2.00,
    "booking_fee": 3.00,
    "total_with_fees": 38.13,
    "minimum_fare": 20.00,
    "final_total": 38.13
  }
}
```

## Real-World Pricing Example

**Scenario**: Car repair service in Downtown Cairo during peak hours

### Setup:
```json
{
  "zone": "Downtown Cairo",
  "service": "Maintenance Service",
  "sub_service": "car_repair",
  "base_fare": 15.00,
  "price_per_km": 3.00,
  "price_per_minute": 0.75,
  "platform_fee": 5.00,
  "service_fee": 3.00,
  "booking_fee": 2.00,
  "minimum_fare": 25.00,
  "peak_hour_multiplier": 1.8,
  "peak_hours": "07:00-09:00"
}
```

### Calculation:
- **Distance**: 4km
- **Duration**: 25 minutes  
- **Time**: 8:00 AM (peak hour)

**Step-by-step calculation:**
1. Base fare: 15.00 EGP
2. Distance cost: 4km × 3.00 = 12.00 EGP
3. Time cost: 25min × 0.75 = 18.75 EGP
4. Subtotal: 15.00 + 12.00 + 18.75 = 45.75 EGP
5. Peak multiplier: 45.75 × 1.8 = 82.35 EGP
6. Platform fee: 5.00 EGP
7. Service fee: 3.00 EGP
8. Booking fee: 2.00 EGP
9. **Total with fees**: 82.35 + 5.00 + 3.00 + 2.00 = 92.35 EGP
10. **Final price**: max(92.35, 25.00) = **92.35 EGP**

## Benefits of the New System

### 1. **Simplified Management**
- One pricing rule per service/zone combination
- No need to manage provider-specific pricing
- Easier to maintain consistency

### 2. **Transparent Application Fees**
- Clear breakdown of platform costs
- Separate service and booking fees
- Better revenue tracking

### 3. **Fair Pricing**
- All providers follow the same pricing rules
- Customers get consistent pricing
- No provider can undercut unfairly

### 4. **Centralized Control**
- Admin can adjust pricing for entire zones
- Quick response to market changes
- Better pricing strategy implementation

## Migration Impact

### Database Changes:
- ✅ Removed `provider` foreign key from ProviderServicePricing
- ✅ Added `platform_fee`, `service_fee`, `booking_fee` fields
- ✅ Removed legacy pricing fields
- ✅ Updated unique constraints

### API Changes:
- ✅ Simplified price calculation (no provider iteration)
- ✅ Enhanced pricing breakdown with application fees
- ✅ Updated WebSocket consumers
- ✅ Modified admin interface

### Backward Compatibility:
- ✅ All existing APIs continue to work
- ✅ Pricing calculation logic updated seamlessly
- ✅ Admin interface reflects new structure

This enhanced system provides better control, transparency, and fairness while simplifying the overall pricing management process.