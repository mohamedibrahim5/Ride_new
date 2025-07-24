# Core Models Class Diagram

## User Management Models

This diagram shows the core user management structure of the ride-sharing platform.

```mermaid
classDiagram
    class User {
        <<AbstractUser>>
        +id: BigAutoField
        +name: CharField[30]
        +phone: CharField[20] {unique}
        +email: EmailField
        +image: ImageField
        +role: CharField[2] {CU|PR|AD}
        +location: PlainLocationField
        +location2_lat: FloatField
        +location2_lng: FloatField
        +average_rating: DecimalField[3,2]
        +fcm_registration_id: CharField[255]
        +device_type: CharField[10] {android|ios}
        +is_active: BooleanField
        +last_login: DateTimeField
        +date_joined: DateTimeField
        +password: CharField[128]
        --
        +create_user(phone, password, **extra_fields)
        +create_superuser(phone, password, **extra_fields)
        +check_password(password): bool
        +set_password(password): void
        +__str__(): str
    }

    class Customer {
        +id: BigAutoField
        +user: OneToOneField→User
        +in_ride: BooleanField
        --
        +__str__(): str
    }

    class Provider {
        +id: BigAutoField
        +user: OneToOneField→User
        +services: ManyToManyField→Service
        +sub_service: CharField[50]
        +is_verified: BooleanField
        +in_ride: BooleanField
        --
        +has_maintenance_service(): bool
        +clean(): void
        +__str__(): str
    }

    class DriverProfile {
        +id: BigAutoField
        +provider: OneToOneField→Provider
        +license: CharField[20] {unique}
        +status: CharField[20] {available|in_ride}
        +is_verified: BooleanField
        +documents: FileField
        --
        +__str__(): str
    }

    class DriverCar {
        +id: BigAutoField
        +driver_profile: OneToOneField→DriverProfile
        +type: CharField[20]
        +model: CharField[20]
        +number: CharField[20]
        +color: CharField[20]
        +image: ImageField
        --
        +__str__(): str
    }

    class UserOtp {
        +id: BigAutoField
        +user: OneToOneField→User
        +otp: CharField[20]
        --
        +__str__(): str
    }

    class UserPoints {
        +id: BigAutoField
        +user: OneToOneField→User
        +points: PositiveIntegerField
        --
        +__str__(): str
    }

    class CustomerPlace {
        +id: BigAutoField
        +customer: ForeignKey→User
        +location: PlainLocationField
        --
        +__str__(): str
    }

    %% Relationships
    User ||--|| Customer : "1:1"
    User ||--|| Provider : "1:1"
    User ||--|| UserOtp : "1:1"
    User ||--|| UserPoints : "1:1"
    User ||--o{ CustomerPlace : "1:*"
    Provider ||--|| DriverProfile : "1:1"
    DriverProfile ||--|| DriverCar : "1:1"

    %% Styling
    classDef userClass fill:#e1f5fe
    classDef profileClass fill:#f3e5f5
    classDef utilityClass fill:#e8f5e8

    class User userClass
    class Customer profileClass
    class Provider profileClass
    class DriverProfile profileClass
    class DriverCar profileClass
    class UserOtp utilityClass
    class UserPoints utilityClass
    class CustomerPlace utilityClass
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