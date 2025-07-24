# Ride Sharing & Food Delivery API Documentation

## Table of Contents
1. [Overview](#overview)
2. [Base URL](#base-url)
3. [Authentication](#authentication)
4. [User Roles](#user-roles)
5. [API Endpoints](#api-endpoints)
6. [Complete User Flows](#complete-user-flows)
7. [Error Handling](#error-handling)
8. [WebSocket Support](#websocket-support)

## Overview

This API provides a comprehensive ride-sharing and food delivery platform with the following features:
- User authentication and registration
- Ride booking and management
- Food delivery services
- Car rental services
- E-commerce functionality
- Real-time location tracking
- Push notifications

## Base URL

```
http://localhost:8000
```

## Authentication

The API uses Token-based authentication. Include the token in the Authorization header:

```
Authorization: Token <your_token_here>
```

## User Roles

- **CU (Customer)**: End users who can book rides, order food, and rent cars
- **PR (Provider)**: Service providers who can offer rides, food delivery, and car rentals
- **DR (Driver)**: Drivers who can accept ride requests

## API Endpoints

### Authentication Endpoints

#### 1. User Registration
**POST** `/authentication/register/`

Register a new user (Customer or Provider).

**Request Body:**
```json
{
  "name": "John Doe",
  "phone": "1234567890",
  "password": "securepassword",
  "role": "CU",  // "CU" for Customer, "PR" for Provider
  "location": "30.0444,31.2357",
  "email": "john@example.com",
  "image": "file_upload"  // Optional
}
```

**Response:**
```json
{
  "id": 1,
  "name": "John Doe",
  "phone": "1234567890",
  "email": "john@example.com",
  "role": "CU",
  "location": "30.0444,31.2357",
  "is_active": false
}
```

#### 2. User Login
**POST** `/authentication/login/`

Authenticate user and receive access token.

**Request Body:**
```json
{
  "phone": "1234567890",
  "password": "securepassword"
}
```

**Response:**
```json
{
  "token": "your_access_token_here",
  "is_verified": true
}
```

#### 3. Send OTP
**POST** `/authentication/send-otp/`

Send OTP to user's phone number for verification.

**Request Body:**
```json
{
  "phone": "1234567890"
}
```

#### 4. Verify OTP
**POST** `/authentication/verify-otp/`

Verify OTP and activate user account.

**Request Body:**
```json
{
  "phone": "1234567890",
  "otp": "123456"
}
```

**Response:**
```json
{
  "token": "your_access_token_here",
  "message": "OTP verified successfully"
}
```

#### 5. Reset Password
**POST** `/authentication/reset-password/`

Reset user password using OTP.

**Headers:** `Authorization: Token <token>`

**Request Body:**
```json
{
  "otp": "123456",
  "password": "newpassword",
  "confirm_password": "newpassword"
}
```

#### 6. Change Password
**POST** `/authentication/change-password/`

Change user password (requires current password).

**Headers:** `Authorization: Token <token>`

**Request Body:**
```json
{
  "old_password": "currentpassword",
  "password": "newpassword",
  "confirm_password": "newpassword"
}
```

#### 7. User Profile
**GET/PATCH** `/authentication/profile/`

Get or update user profile information.

**Headers:** `Authorization: Token <token>`

**Response:**
```json
{
  "id": 1,
  "user": {
    "id": 1,
    "name": "John Doe",
    "phone": "1234567890",
    "email": "john@example.com",
    "role": "CU",
    "location": "30.0444,31.2357"
  },
  "in_ride": false,
  "current_ride": null
}
```

#### 8. Logout
**POST** `/authentication/logout/`

Logout user and invalidate token.

**Headers:** `Authorization: Token <token>`

#### 9. Delete User
**POST** `/authentication/delete/`

Delete user account.

**Headers:** `Authorization: Token <token>`

**Request Body:**
```json
{
  "password": "currentpassword"
}
```

#### 10. FCM Device Registration
**POST** `/authentication/fcm-device/`

Register device for push notifications.

**Headers:** `Authorization: Token <token>`

**Request Body:**
```json
{
  "registration_id": "fcm_device_token",
  "device_type": "android"  // "android" or "ios"
}
```

### Service Management

#### 11. Services
**GET/POST** `/authentication/services/`

Manage available services (Admin only).

**GET Response:**
```json
[
  {
    "id": 1,
    "name": "Food Delivery"
  },
  {
    "id": 2,
    "name": "Ride Sharing"
  }
]
```

### Provider Management

#### 12. Providers
**GET/POST/PATCH/DELETE** `/authentication/providers/`

Manage provider profiles and services.

**GET Response:**
```json
[
  {
    "id": 1,
    "user": {
      "id": 2,
      "name": "Provider Name",
      "phone": "9876543210",
      "role": "PR"
    },
    "services": [
      {
        "id": 1,
        "name": "Food Delivery"
      }
    ],
    "is_verified": true,
    "in_ride": false
  }
]
```

**PATCH Request Body:**
```json
{
  "service_ids": [1, 2]  // Assign services to provider
}
```

#### 13. Driver Profiles
**GET/POST/PATCH/DELETE** `/authentication/driver-profiles/`

Manage driver profiles.

**POST Request Body:**
```json
{
  "provider": 1,
  "license": "DRIVER-LICENSE-123",
  "status": "available",
  "is_verified": true
}
```

#### 14. Driver Cars
**GET/POST/PATCH/DELETE** `/authentication/driver-cars/`

Manage driver vehicle information.

**POST Request Body (multipart/form-data):**
```json
{
  "driver_profile": 1,
  "type": "Sedan",
  "model": "Toyota Camry",
  "number": "ABC123",
  "color": "Red",
  "license": "CAR-LICENSE-123",
  "image": "file_upload"
}
```

### Customer Management

#### 15. Customer Places
**GET/POST/PATCH/DELETE** `/authentication/customer-places/`

Manage customer saved locations.

**POST Request Body:**
```json
{
  "location": "30.0444,31.2357"
}
```

### Ride Management

#### 16. Request Provider
**POST** `/authentication/request-provider/`

Request a provider for a specific service.

**Headers:** `Authorization: Token <token>`

**Request Body:**
```json
{
  "service_id": 1,
  "lat": 30.0444,
  "lng": 31.2357
}
```

#### 17. Start Ride Request
**POST** `/authentication/start-ride/`

Start a new ride request.

**Headers:** `Authorization: Token <token>`

**Request Body:**
```json
{
  "service_id": 1,
  "pickup_lat": 30.0444,
  "pickup_lng": 31.2357,
  "drop_lat": 30.0500,
  "drop_lng": 31.2400
}
```

#### 18. Book Ride
**POST** `/authentication/book-ride/`

Book a ride with specific details.

**Headers:** `Authorization: Token <token>`

**Request Body:**
```json
{
  "lat": 30.0444,
  "lng": 31.2357,
  "drop_lat": 30.0500,
  "drop_lng": 31.2400,
  "service_id": 1,
  "ride_type": "two_way"  // "one_way" or "two_way"
}
```

#### 19. Provider Ride Response
**POST** `/authentication/ride/respond/`

Provider accepts or rejects a ride request.

**Headers:** `Authorization: Token <token>`

**Request Body:**
```json
{
  "ride_id": 1,
  "action": "accept"  // "accept" or "reject"
}
```

#### 20. Update Ride Status
**POST** `/authentication/update-ride/`

Update ride status (starting, arriving, finished, cancelled).

**Headers:** `Authorization: Token <token>`

**Request Body:**
```json
{
  "ride_id": 1,
  "status": "starting"  // "pending", "accepted", "starting", "arriving", "finished", "cancelled"
}
```

### E-commerce Features

#### 21. Products
**GET/POST/PATCH/DELETE** `/authentication/products/`

Manage products for online store.

**GET Response:**
```json
[
  {
    "id": 1,
    "name": "Product Name",
    "description": "Product description",
    "display_price": 100,
    "stock": 50,
    "is_active": true,
    "provider_name": "Store Name",
    "images": [
      {
        "id": 1,
        "image": "image_url"
      }
    ]
  }
]
```

**POST Request Body:**
```json
{
  "name": "Product Name",
  "description": "Product description",
  "display_price": 100,
  "stock": 50,
  "is_active": true
}
```

#### 22. Upload Product Image
**POST** `/authentication/products/{id}/upload-image/`

Upload image for a product.

**Headers:** `Authorization: Token <token>`

**Request Body (multipart/form-data):**
```json
{
  "image": "file_upload"
}
```

#### 23. Purchases
**GET/POST/PATCH** `/authentication/purchases/`

Manage customer purchases.

**POST Request Body:**
```json
{
  "product": 1,
  "quantity": 2
}
```

**Response:**
```json
{
  "id": 1,
  "product": 1,
  "product_name": "Product Name",
  "customer_name": "Customer Name",
  "money_spent": 200,
  "quantity": 2,
  "status": "pending",
  "created_at": "2024-01-01T12:00:00Z"
}
```

#### 24. User Points
**GET/PATCH** `/authentication/points/`

Manage user loyalty points.

**GET Response:**
```json
{
  "points": 150
}
```

**POST** `/authentication/points/charge/`

Charge points for purchases.

**Request Body:**
```json
{
  "points": 50
}
```

### Car Rental Features

#### 25. Car Agencies
**GET/POST/PATCH/DELETE** `/authentication/cars/`

Manage car rental agencies.

**GET Response:**
```json
[
  {
    "id": 1,
    "provider": 1,
    "model": "Toyota Camry",
    "brand": "Toyota",
    "color": "Red",
    "price_per_hour": 25.00,
    "available": true,
    "image": "image_url",
    "actual_free_times": [
      {
        "start_time": "2024-01-01T10:00:00Z",
        "end_time": "2024-01-01T18:00:00Z"
      }
    ]
  }
]
```

**POST Request Body:**
```json
{
  "model": "Toyota Camry",
  "brand": "Toyota",
  "color": "Red",
  "price_per_hour": 25.00,
  "available": true,
  "image": "file_upload"
}
```

#### 26. Car Availability
**GET/POST/PATCH/DELETE** `/authentication/availability/`

Manage car availability slots.

**POST Request Body:**
```json
{
  "car": 1,
  "start_time": "2024-01-01T10:00:00Z",
  "end_time": "2024-01-01T18:00:00Z"
}
```

**POST** `/authentication/availability/bulk_create/`

Create multiple availability slots.

**Request Body:**
```json
{
  "car": 1,
  "slots": [
    {
      "start_time": "2024-01-01T10:00:00Z",
      "end_time": "2024-01-01T18:00:00Z"
    }
  ]
}
```

#### 27. Car Rentals
**GET/POST/PATCH** `/authentication/rentals/`

Manage car rental bookings.

**POST Request Body:**
```json
{
  "car": 1,
  "start_datetime": "2024-01-01T10:00:00Z",
  "end_datetime": "2024-01-01T18:00:00Z"
}
```

**Response:**
```json
{
  "id": 1,
  "customer": 1,
  "car": 1,
  "start_datetime": "2024-01-01T10:00:00Z",
  "end_datetime": "2024-01-01T18:00:00Z",
  "total_price": 200.00,
  "status": "pending",
  "created_at": "2024-01-01T09:00:00Z"
}
```

## Complete User Flows

### Customer Ride Booking Flow

1. **Register as Customer**
   ```bash
   POST /authentication/register/
   {
     "name": "John Doe",
     "phone": "1234567890",
     "password": "password123",
     "role": "CU",
     "location": "30.0444,31.2357"
   }
   ```

2. **Verify OTP**
   ```bash
   POST /authentication/verify-otp/
   {
     "phone": "1234567890",
     "otp": "123456"
   }
   ```

3. **Login**
   ```bash
   POST /authentication/login/
   {
     "phone": "1234567890",
     "password": "password123"
   }
   ```

4. **Book a Ride**
   ```bash
   POST /authentication/book-ride/
   Authorization: Token <token>
   {
     "lat": 30.0444,
     "lng": 31.2357,
     "drop_lat": 30.0500,
     "drop_lng": 31.2400,
     "service_id": 1,
     "ride_type": "one_way"
   }
   ```

5. **Monitor Ride Status**
   ```bash
   GET /authentication/profile/
   Authorization: Token <token>
   ```

### Provider Service Flow

1. **Register as Provider**
   ```bash
   POST /authentication/register/
   {
     "name": "Provider Name",
     "phone": "9876543210",
     "password": "password123",
     "role": "PR",
     "location": "30.0444,31.2357"
   }
   ```

2. **Assign Services**
   ```bash
   PATCH /authentication/providers/{provider_id}/
   Authorization: Token <token>
   {
     "service_ids": [1, 2]
   }
   ```

3. **Create Driver Profile**
   ```bash
   POST /authentication/driver-profiles/
   Authorization: Token <token>
   {
     "provider": 1,
     "license": "DRIVER-LICENSE-123",
     "status": "available",
     "is_verified": true
   }
   ```

4. **Add Vehicle**
   ```bash
   POST /authentication/driver-cars/
   Authorization: Token <token>
   # multipart/form-data with vehicle details and image
   ```

5. **Accept Ride Requests**
   ```bash
   POST /authentication/ride/respond/
   Authorization: Token <token>
   {
     "ride_id": 1,
     "action": "accept"
   }
   ```

### Food Delivery Flow

1. **Customer Orders Food**
   ```bash
   POST /authentication/book-ride/
   Authorization: Token <token>
   {
     "lat": 30.0444,
     "lng": 31.2357,
     "drop_lat": 30.0500,
     "drop_lng": 31.2400,
     "service_id": 1,  # Food delivery service
     "ride_type": "one_way"
   }
   ```

2. **Provider Accepts Delivery**
   ```bash
   POST /authentication/ride/respond/
   Authorization: Token <token>
   {
     "ride_id": 1,
     "action": "accept"
   }
   ```

3. **Update Delivery Status**
   ```bash
   POST /authentication/update-ride/
   Authorization: Token <token>
   {
     "ride_id": 1,
     "status": "starting"
   }
   ```

### E-commerce Flow

1. **Browse Products**
   ```bash
   GET /authentication/products/
   Authorization: Token <token>
   ```

2. **Make Purchase**
   ```bash
   POST /authentication/purchases/
   Authorization: Token <token>
   {
     "product": 1,
     "quantity": 2
   }
   ```

3. **Use Points**
   ```bash
   POST /authentication/points/charge/
   Authorization: Token <token>
   {
     "points": 50
   }
   ```

### Car Rental Flow

1. **Browse Available Cars**
   ```bash
   GET /authentication/cars/
   Authorization: Token <token>
   ```

2. **Book Car Rental**
   ```bash
   POST /authentication/rentals/
   Authorization: Token <token>
   {
     "car": 1,
     "start_datetime": "2024-01-01T10:00:00Z",
     "end_datetime": "2024-01-01T18:00:00Z"
   }
   ```

## Error Handling

The API returns standard HTTP status codes:

- **200**: Success
- **201**: Created
- **400**: Bad Request
- **401**: Unauthorized
- **403**: Forbidden
- **404**: Not Found
- **500**: Internal Server Error

Error responses include:
```json
{
  "error": "Error message",
  "field_errors": {
    "field_name": ["Specific error message"]
  }
}
```

## WebSocket Support

The platform supports real-time communication via WebSocket connections for:
- Live ride status updates
- Real-time location tracking
- Instant notifications
- Chat functionality

WebSocket URL: `ws://localhost:8000/ws/`

## Rate Limiting

API endpoints are rate-limited to prevent abuse:
- Authentication endpoints: 5 requests per minute
- General endpoints: 100 requests per minute
- File uploads: 10 requests per minute

## File Uploads

Supported file types:
- Images: JPG, PNG, GIF (max 5MB)
- Documents: PDF (max 10MB)

## Environment Variables

Required environment variables:
```
DEBUG=True
SECRET_KEY=your_secret_key
DATABASE_URL=your_database_url
REDIS_URL=your_redis_url
FCM_SERVER_KEY=your_fcm_server_key
SMS_API_KEY=your_sms_api_key
```

## Testing

Use the provided Postman collection (`food_delivery_flow.postman_collection.json`) for testing all endpoints and flows.

## Support

For API support and questions, contact the development team or refer to the project documentation. 