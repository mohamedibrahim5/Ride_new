# Ride Booking Sequence Diagrams

## Complete Customer Ride Booking Flow

```mermaid
sequenceDiagram
    participant C as Customer App
    participant API as Django API
    participant DB as PostgreSQL
    participant Redis as Redis Cache
    participant WS as WebSocket Server
    participant P as Provider App
    participant FCM as Firebase FCM
    participant SMS as SMS Service

    Note over C,SMS: 1. Authentication Phase
    C->>API: POST /authentication/login/
    API->>DB: Validate credentials
    DB-->>API: User data
    API->>FCM: Register device token
    API-->>C: Auth token + user profile

    Note over C,SMS: 2. Ride Request Phase
    C->>API: POST /authentication/book-ride/
    Note right of C: {lat, lng, drop_lat, drop_lng, service_id}
    
    API->>DB: Create RideStatus (pending)
    API->>DB: Get nearby providers
    API->>Redis: Cache ride request
    
    loop For each nearby provider
        API->>WS: Send ride request to provider
        WS->>P: WebSocket notification
        API->>FCM: Send push notification
    end
    
    API-->>C: Ride request created
    Note right of API: {ride_id, status: "pending"}

    Note over C,SMS: 3. Provider Response Phase
    P->>WS: Accept ride request
    Note right of P: {client_id, accepted: true}
    
    WS->>API: Process provider response
    API->>DB: Update ride status to "accepted"
    API->>DB: Set provider for ride
    API->>Redis: Update ride cache
    
    API->>WS: Broadcast acceptance
    WS->>C: Ride accepted notification
    API->>FCM: Send acceptance notification to customer
    
    Note over C,SMS: 4. Real-time Tracking Phase
    loop Provider location updates
        P->>WS: Send location update
        Note right of P: {location, heading}
        WS->>Redis: Update provider location
        WS->>C: Forward location to customer
    end

    Note over C,SMS: 5. Ride Progress Phase
    P->>API: POST /authentication/update-ride/
    Note right of P: {status: "starting"}
    API->>DB: Update ride status
    API->>WS: Broadcast status update
    WS->>C: Status update notification
    API->>FCM: Send status notification

    P->>API: POST /authentication/update-ride/
    Note right of P: {status: "arriving"}
    API->>DB: Update ride status
    API->>WS: Broadcast status update
    WS->>C: Status update notification

    P->>API: POST /authentication/update-ride/
    Note right of P: {status: "finished"}
    API->>DB: Update ride status
    API->>WS: Broadcast completion
    WS->>C: Ride completed notification
    API->>FCM: Send completion notification

    Note over C,SMS: 6. Rating Phase
    C->>API: POST /authentication/rides/{ride_id}/rate/
    Note right of C: {driver_rating: 5, comment: "Great service"}
    API->>DB: Create/Update rating
    API->>DB: Update provider average rating
    API-->>C: Rating saved successfully
```

## Provider Ride Acceptance Flow

```mermaid
sequenceDiagram
    participant P as Provider App
    participant WS as WebSocket Server
    participant API as Django API
    participant DB as PostgreSQL
    participant Redis as Redis Cache
    participant C as Customer App
    participant FCM as Firebase FCM

    Note over P,FCM: Provider receives ride request
    WS->>P: New ride request
    Note right of WS: {ride_id, client_name, pickup_location, service_price_info}
    
    P->>P: Display ride details to provider
    
    alt Provider accepts ride
        P->>WS: Send acceptance
        Note right of P: {client_id, accepted: true}
        
        WS->>API: Process acceptance with database lock
        API->>DB: SELECT FOR UPDATE ride status
        
        alt Ride still pending
            API->>DB: Update ride status to "accepted"
            API->>DB: Set provider_id
            API->>Redis: Update ride cache
            
            API->>WS: Broadcast acceptance
            WS->>C: Ride accepted notification
            API->>FCM: Send notification to customer
            
            WS-->>P: Acceptance confirmed
            Note right of WS: {status: "accepted", ride_id}
            
        else Ride already taken
            WS-->>P: Ride already handled
            Note right of WS: {error: "Ride already accepted"}
        end
        
    else Provider rejects ride
        P->>WS: Send rejection
        Note right of P: {client_id, accepted: false}
        
        WS->>API: Process rejection
        API->>DB: Log rejection (optional)
        
        WS-->>P: Rejection acknowledged
    end
```

## Price Calculation Sequence

```mermaid
sequenceDiagram
    participant C as Customer App
    participant API as Django API
    participant DB as PostgreSQL
    participant Pricing as Pricing Service
    participant Maps as Maps API

    C->>API: POST /authentication/calculate-price/
    Note right of C: {pickup_lat, pickup_lng, drop_lat, drop_lng, service_id}
    
    API->>DB: Get service details
    DB-->>API: Service information
    
    API->>DB: Get pricing zones
    DB-->>API: Active pricing zones
    
    API->>Pricing: Determine zone for pickup location
    Pricing->>Pricing: Point-in-polygon calculation
    Pricing-->>API: Matching zone (if any)
    
    API->>DB: Get pricing for service/zone
    DB-->>API: Pricing configuration
    
    API->>Maps: Calculate distance and duration
    Maps-->>API: Route information
    
    API->>Pricing: Calculate total price
    Note right of Pricing: Base fare + distance cost + time cost + fees
    
    alt Peak hours check
        Pricing->>Pricing: Check if current time is peak
        Pricing->>Pricing: Apply peak multiplier
    end
    
    Pricing->>Pricing: Apply minimum fare rule
    Pricing-->>API: Final price breakdown
    
    API-->>C: Price calculation result
    Note right of API: {total_price, breakdown, distance_km, duration_minutes}
```

## Error Handling Sequences

### Ride Request Timeout

```mermaid
sequenceDiagram
    participant C as Customer App
    participant API as Django API
    participant DB as PostgreSQL
    participant WS as WebSocket Server
    participant Scheduler as Celery Beat

    C->>API: POST /authentication/book-ride/
    API->>DB: Create ride request
    API->>Scheduler: Schedule timeout task (5 minutes)
    API-->>C: Ride request created
    
    Note over Scheduler: 5 minutes later...
    
    Scheduler->>API: Execute timeout task
    API->>DB: Check ride status
    
    alt Ride still pending
        API->>DB: Update status to "cancelled"
        API->>WS: Broadcast cancellation
        WS->>C: Ride timeout notification
        API-->>Scheduler: Timeout processed
    else Ride already accepted
        API-->>Scheduler: No action needed
    end
```

### Provider Disconnection Handling

```mermaid
sequenceDiagram
    participant P as Provider App
    participant WS as WebSocket Server
    participant API as Django API
    participant DB as PostgreSQL
    participant C as Customer App

    Note over P: Provider loses connection during active ride
    
    WS->>WS: Detect connection loss
    WS->>API: Provider disconnected event
    
    API->>DB: Get active rides for provider
    DB-->>API: Active ride information
    
    alt Ride in progress
        API->>DB: Log disconnection event
        API->>C: Provider connection lost notification
        
        Note over API: Wait for reconnection (2 minutes)
        
        alt Provider reconnects
            P->>WS: Reconnect with auth token
            WS->>API: Provider reconnected
            API->>C: Provider reconnected notification
        else Provider doesn't reconnect
            API->>DB: Mark ride as problematic
            API->>C: Contact support notification
        end
    end
```

## Key Features Demonstrated

1. **Atomic Operations**: Database locks prevent race conditions
2. **Real-time Communication**: WebSocket for instant updates
3. **Fault Tolerance**: Timeout handling and reconnection logic
4. **Scalability**: Async processing and caching
5. **User Experience**: Immediate feedback and status updates
6. **Business Logic**: Complex pricing calculations and zone detection