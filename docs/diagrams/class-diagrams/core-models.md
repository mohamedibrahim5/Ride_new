# Core Models Class Diagram

## User Management Models

This diagram shows the core user management structure of the ride-sharing platform.

```mermaid
classDiagram
    class User {
        +id: BigAutoField
        +name: CharField
        +phone: CharField
        +email: EmailField
        +image: ImageField
        +role: CharField
        +location: PlainLocationField
        +location2_lat: FloatField
        +location2_lng: FloatField
        +average_rating: DecimalField
        +fcm_registration_id: CharField
        +device_type: CharField
        +is_active: BooleanField
        +last_login: DateTimeField
        +date_joined: DateTimeField
        +password: CharField
        +create_user()
        +create_superuser()
        +check_password()
        +set_password()
        +__str__()
    }

    class Customer {
        +id: BigAutoField
        +in_ride: BooleanField
        +__str__()
    }

    class Provider {
        +id: BigAutoField
        +services: ManyToManyField
        +sub_service: CharField
        +is_verified: BooleanField
        +in_ride: BooleanField
        +has_maintenance_service()
        +clean()
        +__str__()
    }

    class DriverProfile {
        +id: BigAutoField
        +license: CharField
        +status: CharField
        +is_verified: BooleanField
        +documents: FileField
        +__str__()
    }

    class DriverCar {
        +id: BigAutoField
        +type: CharField
        +model: CharField
        +number: CharField
        +color: CharField
        +image: ImageField
        +__str__()
    }

    class UserOtp {
        +id: BigAutoField
        +otp: CharField
        +__str__()
    }

    class UserPoints {
        +id: BigAutoField
        +points: PositiveIntegerField
        +__str__()
    }

    class CustomerPlace {
        +id: BigAutoField
        +location: PlainLocationField
        +__str__()
    }

    %% Relationships
    User "1" -- "1" Customer : has
    User "1" -- "1" Provider : has
    User "1" -- "1" UserOtp : has
    User "1" -- "1" UserPoints : has
    User "1" -- "many" CustomerPlace : owns
    Provider "1" -- "1" DriverProfile : has
    DriverProfile "1" -- "1" DriverCar : has

    %% Styling (Optional)
    classDef userClass fill:#e1f5fe
    classDef profileClass fill:#f3e5f5
    classDef utilityClass fill:#e8f5e8

    class User userClass
    class Customer,Provider,DriverProfile,DriverCar profileClass
    class UserOtp,UserPoints,CustomerPlace utilityClass

```

## Key Relationships

1. **User → Customer/Provider**: One-to-one relationship based on user role
2. **Provider → DriverProfile**: Optional one-to-one for providers who are drivers
3. **DriverProfile → DriverCar**: One-to-one relationship for vehicle information
4. **User → UserOtp**: One-to-one for OTP verification
5. **User → UserPoints**: One-to-one for loyalty points system
6. **User → CustomerPlace**: One-to-many for saved locations

## Business Rules

- Users can only have one role (Customer, Provider, or Admin)
- Only verified providers can accept rides
- Driver profiles are only for providers with transportation services
- Sub-services are only applicable for maintenance service providers
- OTP is required for account activation
