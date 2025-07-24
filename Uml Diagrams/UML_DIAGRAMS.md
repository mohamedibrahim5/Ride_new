# UML Diagrams - Ride Sharing & Food Delivery Platform

This document contains comprehensive UML diagrams for the ride-sharing and food delivery platform, organized by diagram type and system component.

## Table of Contents

1. [Class Diagrams](#class-diagrams)
2. [Use Case Diagrams](#use-case-diagrams)
3. [Sequence Diagrams](#sequence-diagrams)
4. [Activity Diagrams](#activity-diagrams)
5. [Component Diagrams](#component-diagrams)
6. [Deployment Diagrams](#deployment-diagrams)
7. [State Diagrams](#state-diagrams)

---

## Class Diagrams

### 1. Core User Management Class Diagram

```mermaid
classDiagram
    class User {
        id: BigAutoField
        name: CharField
        phone: CharField
        email: EmailField
        image: ImageField
        role: CharField
        location: PlainLocationField
        location2_lat: FloatField
        location2_lng: FloatField
        average_rating: DecimalField
        fcm_registration_id: CharField
        device_type: CharField
        is_active: BooleanField
        last_login: DateTimeField
        date_joined: DateTimeField
    }

    class Customer {
        id: BigAutoField
        user: OneToOneField
        in_ride: BooleanField
    }

    class Provider {
        id: BigAutoField
        user: OneToOneField
        services: ManyToManyField
        sub_service: CharField
        is_verified: BooleanField
        in_ride: BooleanField
    }

    class DriverProfile {
        id: BigAutoField
        provider: OneToOneField
        license: CharField
        status: CharField
        is_verified: BooleanField
        documents: FileField
    }

    class DriverCar {
        id: BigAutoField
        driver_profile: OneToOneField
        type: CharField
        model: CharField
        number: CharField
        color: CharField
        image: ImageField
    }

    class UserOtp {
        id: BigAutoField
        user: OneToOneField
        otp: CharField
    }

    User --> Customer : has 1
    User --> Provider : has 1
    User --> UserOtp : has 1
    Provider --> DriverProfile : has 1
    DriverProfile --> DriverCar : has 1

```

### 2. Service Management Class Diagram

```mermaid
classDiagram
    class Service {
        id: BigAutoField
        name: CharField
        created_at: DateTimeField
    }

    class ServiceImage {
        id: BigAutoField
        service: ForeignKey
        image: ImageField
    }

    class PricingZone {
        id: BigAutoField
        name: CharField
        description: TextField
        boundaries: JSONField
        is_active: BooleanField
        created_at: DateTimeField
    }

    class ProviderServicePricing {
        id: BigAutoField
        service: ForeignKey
        sub_service: CharField
        zone: ForeignKey
        platform_fee: DecimalField
        service_fee: DecimalField
        booking_fee: DecimalField
        base_fare: DecimalField
        price_per_km: DecimalField
        price_per_minute: DecimalField
        minimum_fare: DecimalField
        peak_hour_multiplier: DecimalField
        peak_hours_start: TimeField
        peak_hours_end: TimeField
        is_active: BooleanField
    }

    class RideStatus {
        id: BigAutoField
        client: ForeignKey
        provider: ForeignKey
        service: ForeignKey
        status: CharField
        pickup_lat: FloatField
        pickup_lng: FloatField
        drop_lat: FloatField
        drop_lng: FloatField
        created_at: DateTimeField
    }

    class Rating {
        id: BigAutoField
        ride: OneToOneField
        driver_rating: PositiveSmallIntegerField
        customer_rating: PositiveSmallIntegerField
        driver_comment: TextField
        customer_comment: TextField
        created_at: DateTimeField
        updated_at: DateTimeField
    }

    Service o-- ServiceImage : has
    Service o-- ProviderServicePricing : pricing
    PricingZone o-- ProviderServicePricing : zone
    RideStatus --> Rating : has 1
    Service o-- RideStatus : has many

```

### 3. E-commerce Class Diagram

```mermaid
classDiagram
    class Product {
        id: BigAutoField
        provider: ForeignKey
        name: CharField
        description: TextField
        display_price: PositiveIntegerField
        stock: PositiveIntegerField
        is_active: BooleanField
        created_at: DateTimeField
        updated_at: DateTimeField
    }

    class ProductImage {
        id: BigAutoField
        product: ForeignKey
        image: ImageField
    }

    class Purchase {
        id: BigAutoField
        customer: ForeignKey
        product: ForeignKey
        money_spent: PositiveIntegerField
        quantity: PositiveIntegerField
        status: CharField
        created_at: DateTimeField
    }

    class UserPoints {
        id: BigAutoField
        user: OneToOneField
        points: PositiveIntegerField
    }

    Product o-- ProductImage : has
    Product o-- Purchase : purchases
    Customer o-- Purchase : purchases
    User --> UserPoints : has 1

```

### 4. Car Rental Class Diagram

```mermaid
classDiagram
    class CarAgency {
        id: BigAutoField
        provider: ForeignKey
        model: CharField
        brand: CharField
        color: CharField
        price_per_hour: DecimalField
        available: BooleanField
        image: ImageField
        created_at: DateTimeField
    }

    class CarAvailability {
        id: BigAutoField
        car: ForeignKey
        start_time: DateTimeField
        end_time: DateTimeField
    }

    class CarRental {
        id: BigAutoField
        customer: ForeignKey
        car: ForeignKey
        start_datetime: DateTimeField
        end_datetime: DateTimeField
        total_price: DecimalField
        status: CharField
        created_at: DateTimeField
    }

    Provider o-- CarAgency : owns
    CarAgency o-- CarAvailability : available at
    CarAgency o-- CarRental : rented in
    Customer o-- CarRental : rents

```

---

## Use Case Diagrams

### 1. Customer Use Cases

```mermaid
graph TB
    Customer((Customer))
    
    Customer --> UC1[Register Account]
    Customer --> UC2[Login]
    Customer --> UC3[Update Profile]
    Customer --> UC4[Book Ride]
    Customer --> UC5[Track Ride]
    Customer --> UC6[Cancel Ride]
    Customer --> UC7[Rate Driver]
    Customer --> UC8[View Ride History]
    Customer --> UC9[Order Food]
    Customer --> UC10[Rent Car]
    Customer --> UC11[Browse Products]
    Customer --> UC12[Make Purchase]
    Customer --> UC13[Manage Points]
    Customer --> UC14[Receive Notifications]
    
    subgraph "Authentication System"
        UC1
        UC2
        UC3
    end
    
    subgraph "Ride Management"
        UC4
        UC5
        UC6
        UC7
        UC8
    end
    
    subgraph "E-commerce"
        UC11
        UC12
        UC13
    end
```

### 2. Provider/Driver Use Cases

```mermaid
graph TB
    Provider((Provider/Driver))
    
    Provider --> UC15[Register as Provider]
    Provider --> UC16[Setup Driver Profile]
    Provider --> UC17[Add Vehicle Information]
    Provider --> UC18[Accept Ride Requests]
    Provider --> UC19[Update Ride Status]
    Provider --> UC20[Update Location]
    Provider --> UC21[Rate Customer]
    Provider --> UC22[Manage Services]
    Provider --> UC23[Set Pricing]
    Provider --> UC24[Manage Products]
    Provider --> UC25[Manage Car Rentals]
    Provider --> UC26[View Earnings]
    
    subgraph "Provider Setup"
        UC15
        UC16
        UC17
        UC22
        UC23
    end
    
    subgraph "Ride Operations"
        UC18
        UC19
        UC20
        UC21
    end
    
    subgraph "Business Management"
        UC24
        UC25
        UC26
    end
```

### 3. Admin Use Cases

```mermaid
graph TB
    Admin((Admin))
    
    Admin --> UC27[Manage Users]
    Admin --> UC28[Verify Providers]
    Admin --> UC29[Manage Services]
    Admin --> UC30[Configure Pricing Zones]
    Admin --> UC31[Monitor System]
    Admin --> UC32[Generate Reports]
    Admin --> UC33[Manage Notifications]
    Admin --> UC34[System Configuration]
    
    subgraph "User Management"
        UC27
        UC28
    end
    
    subgraph "System Configuration"
        UC29
        UC30
        UC34
    end
    
    subgraph "Monitoring & Reports"
        UC31
        UC32
        UC33
    end
```

---

## Sequence Diagrams

### 1. Customer Ride Booking Sequence

```mermaid
sequenceDiagram
    participant C as Customer
    participant API as API Server
    participant WS as WebSocket
    participant P as Provider
    participant DB as Database
    participant FCM as FCM Service

    C->>API: POST /book-ride/
    API->>DB: Create RideStatus
    API->>WS: Broadcast ride request
    WS->>P: Send ride notification
    API-->>C: Ride request created
    
    P->>WS: Accept ride
    WS->>API: Process acceptance
    API->>DB: Update ride status
    API->>FCM: Send notification to customer
    WS-->>C: Ride accepted notification
    
    P->>API: Update status to "starting"
    API->>DB: Update ride status
    API->>WS: Broadcast status update
    WS-->>C: Status update notification
    
    P->>WS: Send location updates
    WS-->>C: Real-time location
    
    P->>API: Update status to "finished"
    API->>DB: Update ride status
    API->>WS: Broadcast completion
    WS-->>C: Ride completed notification
    
    C->>API: Rate driver
    API->>DB: Save rating
    API-->>C: Rating saved
```

### 2. User Authentication Sequence

```mermaid
sequenceDiagram
    participant U as User
    participant API as API Server
    participant SMS as SMS Service
    participant DB as Database
    participant FCM as FCM Service

    U->>API: POST /register/
    API->>SMS: Send OTP
    SMS-->>U: OTP via SMS
    API->>DB: Create user (inactive)
    API-->>U: Registration successful

    U->>API: POST /verify-otp/
    API->>DB: Verify OTP
    API->>DB: Activate user
    API->>DB: Create auth token
    API-->>U: Token + verification success

    U->>API: POST /login/
    API->>DB: Validate credentials
    API->>FCM: Register device
    API-->>U: Auth token + login success
```

### 3. Product Purchase Sequence

```mermaid
sequenceDiagram
    participant C as Customer
    participant API as API Server
    participant DB as Database
    participant P as Provider

    C->>API: GET /products/
    API->>DB: Fetch products
    API-->>C: Product list

    C->>API: POST /purchases/
    API->>DB: Check product availability
    API->>DB: Check stock
    API->>DB: Create purchase
    API->>DB: Update product stock
    API-->>C: Purchase created

    API->>P: Notify new order
    P->>API: Update order status
    API->>DB: Update purchase status
    API->>C: Status update notification
```

---

## Activity Diagrams

### 1. Ride Booking Process

```mermaid
flowchart TD
    Start([Customer opens app]) --> Login{Logged in?}
    Login -->|No| Auth[Authentication Process]
    Auth --> Login
    Login -->|Yes| Location[Get current location]
    Location --> Destination[Select destination]
    Destination --> Service[Choose service type]
    Service --> Request[Send ride request]
    Request --> Wait[Wait for provider response]
    
    Wait --> Response{Provider responds?}
    Response -->|Accept| Accepted[Ride accepted]
    Response -->|Reject| Wait
    Response -->|Timeout| Timeout[Request timeout]
    Timeout --> Retry{Retry?}
    Retry -->|Yes| Request
    Retry -->|No| Cancel[Cancel request]
    
    Accepted --> Track[Track ride progress]
    Track --> Status{Ride status?}
    Status -->|Starting| Track
    Status -->|Arriving| Track
    Status -->|Finished| Payment[Process payment]
    Status -->|Cancelled| Cancel
    
    Payment --> Rate[Rate driver]
    Rate --> End([End])
    Cancel --> End
```

### 2. Provider Ride Acceptance Process

```mermaid
flowchart TD
    Start([Provider online]) --> Listen[Listen for ride requests]
    Listen --> Notification{New ride request?}
    Notification -->|No| Listen
    Notification -->|Yes| Display[Display ride details]
    Display --> Decision{Accept ride?}
    Decision -->|No| Reject[Reject ride]
    Decision -->|Yes| Accept[Accept ride]
    
    Reject --> Listen
    Accept --> Navigate[Navigate to pickup]
    Navigate --> Pickup[Arrive at pickup]
    Pickup --> StartRide[Start ride]
    StartRide --> UpdateLocation[Update location continuously]
    UpdateLocation --> Destination[Navigate to destination]
    Destination --> Complete[Complete ride]
    Complete --> Rate[Rate customer]
    Rate --> Available[Set status to available]
    Available --> Listen
```

---

## Component Diagrams

### 1. System Architecture Components

```mermaid
graph TB
    subgraph "Client Layer"
        Mobile[Mobile Apps]
        Web[Web Client]
        Admin[Admin Panel]
    end
    
    subgraph "API Gateway"
        LB[Load Balancer]
        Nginx[Nginx Reverse Proxy]
    end
    
    subgraph "Application Layer"
        Django[Django REST API]
        WS[WebSocket Server]
        Celery[Celery Workers]
        Beat[Celery Beat]
    end
    
    subgraph "Data Layer"
        PostgreSQL[(PostgreSQL)]
        Redis[(Redis Cache)]
        Media[File Storage]
    end
    
    subgraph "External Services"
        FCM[Firebase FCM]
        SMS[SMS Service]
        WhatsApp[WhatsApp API]
    end
    
    Mobile --> LB
    Web --> LB
    Admin --> LB
    LB --> Nginx
    Nginx --> Django
    Nginx --> WS
    Django --> PostgreSQL
    Django --> Redis
    Django --> Media
    WS --> Redis
    Celery --> Redis
    Beat --> Celery
    Django --> FCM
    Django --> SMS
    Django --> WhatsApp
```

### 2. Authentication Component

```mermaid
graph TB
    subgraph "Authentication Module"
        AuthAPI[Authentication API]
        TokenMgr[Token Manager]
        OTPService[OTP Service]
        UserMgr[User Manager]
    end
    
    subgraph "External Auth Services"
        SMS[SMS Gateway]
        FCM[FCM Service]
    end
    
    subgraph "Data Storage"
        UserDB[(User Database)]
        TokenDB[(Token Storage)]
        OTPCache[(OTP Cache)]
    end
    
    AuthAPI --> TokenMgr
    AuthAPI --> OTPService
    AuthAPI --> UserMgr
    OTPService --> SMS
    TokenMgr --> FCM
    UserMgr --> UserDB
    TokenMgr --> TokenDB
    OTPService --> OTPCache
```

---

## Deployment Diagrams

### 1. Production Deployment Architecture

```mermaid
graph TB
    subgraph "Load Balancer Tier"
        LB[Nginx Load Balancer]
    end
    
    subgraph "Application Tier"
        App1[Django App Server 1]
        App2[Django App Server 2]
        WS1[WebSocket Server 1]
        WS2[WebSocket Server 2]
    end
    
    subgraph "Worker Tier"
        Worker1[Celery Worker 1]
        Worker2[Celery Worker 2]
        Beat[Celery Beat Scheduler]
        Flower[Flower Monitor]
    end
    
    subgraph "Database Tier"
        PG_Master[(PostgreSQL Master)]
        PG_Slave[(PostgreSQL Slave)]
        Redis_Master[(Redis Master)]
        Redis_Slave[(Redis Slave)]
    end
    
    subgraph "Storage Tier"
        FileStorage[File Storage]
        Backup[Backup Storage]
    end
    
    subgraph "Monitoring"
        Logs[Log Aggregation]
        Metrics[Metrics Collection]
        Alerts[Alert Manager]
    end
    
    LB --> App1
    LB --> App2
    LB --> WS1
    LB --> WS2
    
    App1 --> PG_Master
    App2 --> PG_Master
    App1 --> Redis_Master
    App2 --> Redis_Master
    
    PG_Master --> PG_Slave
    Redis_Master --> Redis_Slave
    
    Worker1 --> Redis_Master
    Worker2 --> Redis_Master
    Beat --> Redis_Master
    
    App1 --> FileStorage
    App2 --> FileStorage
    
    PG_Master --> Backup
    FileStorage --> Backup
    
    App1 --> Logs
    App2 --> Logs
    Worker1 --> Metrics
    Worker2 --> Metrics
    Metrics --> Alerts
```

### 2. Development Environment

```mermaid
graph TB
    subgraph "Development Environment"
        Dev[Developer Machine]
        Docker[Docker Compose]
    end
    
    subgraph "Local Services"
        Django[Django Dev Server]
        Redis[Redis Container]
        PostgreSQL[PostgreSQL Container]
        Celery[Celery Worker]
        Flower[Flower UI]
    end
    
    subgraph "External Services"
        FCM[Firebase FCM]
        SMS[SMS Service]
    end
    
    Dev --> Docker
    Docker --> Django
    Docker --> Redis
    Docker --> PostgreSQL
    Docker --> Celery
    Docker --> Flower
    
    Django --> FCM
    Django --> SMS
    Django --> PostgreSQL
    Django --> Redis
    Celery --> Redis
```

---

## State Diagrams

### 1. Ride Status State Machine

```mermaid
stateDiagram-v2
    [*] --> Pending : Customer books ride
    
    Pending --> Accepted : Provider accepts
    Pending --> Cancelled : Customer cancels or timeout
    
    Accepted --> Starting : Provider starts journey
    Accepted --> Cancelled : Customer/Provider cancels
    
    Starting --> Arriving : Provider en route to pickup
    Starting --> Cancelled : Ride cancelled
    
    Arriving --> InProgress : Customer picked up
    Arriving --> Cancelled : Ride cancelled
    
    InProgress --> Finished : Destination reached
    InProgress --> Cancelled : Ride cancelled
    
    Finished --> [*] : Ride completed
    Cancelled --> [*] : Ride terminated
    
    note right of Pending : Waiting for provider response
    note right of Accepted : Provider confirmed
    note right of Starting : Provider moving to pickup
    note right of Arriving : Provider at pickup location
    note right of InProgress : Ride in progress
    note right of Finished : Ride completed successfully
    note right of Cancelled : Ride terminated
```

### 2. User Account State Machine

```mermaid
stateDiagram-v2
    [*] --> Registered : User registers
    
    Registered --> Verified : OTP verified
    Registered --> Expired : OTP expires
    
    Expired --> Registered : Resend OTP
    
    Verified --> Active : First login
    
    Active --> Suspended : Admin action
    Active --> Inactive : User deactivates
    
    Suspended --> Active : Admin reactivates
    Inactive --> Active : User reactivates
    
    Active --> Deleted : User deletes account
    Suspended --> Deleted : Admin deletes
    
    Deleted --> [*] : Account removed
    
    note right of Registered : Account created, awaiting verification
    note right of Verified : Phone number verified
    note right of Active : Account active and usable
    note right of Suspended : Temporarily disabled
    note right of Inactive : User disabled
    note right of Deleted : Account permanently removed
```

### 3. Purchase Order State Machine

```mermaid
stateDiagram-v2
    [*] --> Pending : Customer places order
    
    Pending --> Confirmed : Provider confirms
    Pending --> Cancelled : Customer/Provider cancels
    
    Confirmed --> InProgress : Provider starts processing
    Confirmed --> Cancelled : Order cancelled
    
    InProgress --> Completed : Order fulfilled
    InProgress --> Cancelled : Order cancelled
    
    Completed --> [*] : Order finished
    Cancelled --> [*] : Order terminated
    
    note right of Pending : Awaiting provider confirmation
    note right of Confirmed : Provider accepted order
    note right of InProgress : Order being processed
    note right of Completed : Order successfully delivered
    note right of Cancelled : Order terminated
```

---

## Diagram Usage Guidelines

### When to Use Each Diagram Type

1. **Class Diagrams**: Use for understanding system structure, relationships between entities, and database design.

2. **Use Case Diagrams**: Use for requirements gathering, stakeholder communication, and system scope definition.

3. **Sequence Diagrams**: Use for understanding interaction flows, API design, and debugging complex processes.

4. **Activity Diagrams**: Use for business process modeling, workflow design, and user journey mapping.

5. **Component Diagrams**: Use for system architecture planning, deployment planning, and team coordination.

6. **Deployment Diagrams**: Use for infrastructure planning, DevOps setup, and scalability planning.

7. **State Diagrams**: Use for modeling entity lifecycles, business rule validation, and status management.

---

*Last Updated: July 2025*
*Version: 1.0*
