# Core Models Class Diagram

## User Management Models

This diagram shows the core user management structure of the ride-sharing platform.

```mermaid
classDiagram
    class User {
        +BigAutoField id
        +CharField name
        +CharField phone
        +EmailField email
        +ImageField image
        +CharField role
        +PlainLocationField location
        +FloatField location2_lat
        +FloatField location2_lng
        +DecimalField average_rating
        +CharField fcm_registration_id
        +CharField device_type
        +BooleanField is_active
        +DateTimeField last_login
        +DateTimeField date_joined
        +CharField password
        +create_user()
        +create_superuser()
        +check_password()
        +set_password()
        +__str__()
    }

    class Customer {
        +BigAutoField id
        +BooleanField in_ride
        +__str__()
    }

    class Provider {
        +BigAutoField id
        +CharField sub_service
        +BooleanField is_verified
        +BooleanField in_ride
        +has_maintenance_service()
        +clean()
        +__str__()
    }

    class DriverProfile {
        +BigAutoField id
        +CharField license
        +CharField status
        +BooleanField is_verified
        +FileField documents
        +__str__()
    }

    class DriverCar {
        +BigAutoField id
        +CharField type
        +CharField model
        +CharField number
        +CharField color
        +ImageField image
        +__str__()
    }

    class UserOtp {
        +BigAutoField id
        +CharField otp
        +__str__()
    }

    class UserPoints {
        +BigAutoField id
        +PositiveIntegerField points
        +__str__()
    }

    class CustomerPlace {
        +BigAutoField id
        +PlainLocationField location
        +__str__()
    }

    %% Relationships
    User "1" -- "1" Customer : has
    User "1" -- "1" Provider : has
    User "1" -- "1" UserOtp : has
    User "1" -- "1" UserPoints : has
    User "1" -- "many" CustomerPlace : owns
    Provider "1" -- "1" DriverProfile : has
    DriverProfile "1" -- "1" DriverCar : owns


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
