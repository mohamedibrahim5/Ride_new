# Service Management Class Diagram

## Service and Pricing Models

This diagram shows the service management and pricing structure of the platform.

```mermaid
classDiagram

%% Classes
class Service {
  +id
  +name
  +created_at
  +__str__()
}

class ServiceImage {
  +id
  +image
  +__str__()
}

class PricingZone {
  +id
  +name
  +description
  +boundaries
  +is_active
  +created_at
  +contains_point()
  +__str__()
}

class ProviderServicePricing {
  +id
  +sub_service
  +platform_fee
  +service_fee
  +booking_fee
  +base_fare
  +price_per_km
  +price_per_minute
  +minimum_fare
  +peak_hour_multiplier
  +peak_hours_start
  +peak_hours_end
  +is_active
  +created_at
  +updated_at
  +calculate_price()
  +get_pricing_for_location()
  +clean()
  +save()
  +__str__()
}

class RideStatus {
  +id
  +status
  +pickup_lat
  +pickup_lng
  +drop_lat
  +drop_lng
  +created_at
  +can_be_rated_by()
  +__str__()
}

class Rating {
  +id
  +driver_rating
  +customer_rating
  +driver_comment
  +customer_comment
  +created_at
  +updated_at
  +__str__()
}

class Notification {
  +id
  +title
  +message
  +notification_type
  +data
  +is_read
  +created_at
  +mark_as_read()
  +__str__()
}

%% Relationships
Service --> ServiceImage : has
Service --> ProviderServicePricing : has
Service --> RideStatus : used in
PricingZone --> ProviderServicePricing : used in
RideStatus --> Rating : rated by
RideStatus --> Service : of
RideStatus --> User : by client/provider
Rating --> RideStatus : rates
Notification --> User : for
```

## Pricing Calculation Flow

```mermaid
flowchart TD
    A[Ride Request] --> B{Zone-based pricing available?}
    B -->|Yes| C[Get zone pricing]
    B -->|No| D[Get default pricing]
    
    C --> E[Calculate base price]
    D --> E
    
    E --> F[Add distance cost]
    F --> G[Add time cost]
    G --> H{Peak hours?}
    
    H -->|Yes| I[Apply peak multiplier]
    H -->|No| J[Add application fees]
    I --> J
    
    J --> K[Apply minimum fare]
    K --> L[Final Price]
    
    style A fill:#e1f5fe
    style L fill:#c8e6c9
```

## Key Features

### Zone-Based Pricing
- Geographic zones with polygon boundaries
- Different pricing for different areas
- Point-in-polygon algorithm for zone detection

### Dynamic Pricing
- Peak hour multipliers
- Time and distance-based calculation
- Minimum fare guarantees
- Application fees (platform, service, booking)

### Service Management
- Multiple services per provider
- Sub-services for specialized offerings
- Service-specific pricing rules

### Rating System
- Bidirectional rating (driver ↔ customer)
- Comments and numerical ratings
- Average rating calculation
