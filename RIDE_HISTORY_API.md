# Ride History API Documentation

## Overview

The Ride History API allows authenticated users (both drivers and customers) to retrieve their ride history with detailed information including ratings, pricing, and statistics.

## Endpoint

```
GET /api/auth/rides/history/
```

## Authentication

This endpoint requires authentication. Include the user's token in the Authorization header:

```
Authorization: Token your_auth_token_here
```

## Query Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `status` | string | No | Filter rides by status (pending, accepted, starting, arriving, finished, cancelled) |
| `ride_type` | string | No | Filter by ride type (customer, driver) |
| `start_date` | string | No | Filter rides from this date (YYYY-MM-DD format) |
| `end_date` | string | No | Filter rides until this date (YYYY-MM-DD format) |
| `page` | integer | No | Page number for pagination |
| `page_size` | integer | No | Number of rides per page |

## Response Format

### Success Response (200 OK)

```json
{
    "count": 25,
    "next": "http://localhost:8000/api/auth/rides/history/?page=2",
    "previous": null,
    "results": [
        {
            "id": 123,
            "client": {
                "id": 1,
                "name": "John Doe",
                "phone": "+1234567890",
                "email": "john@example.com",
                "image": "/media/user/images/profile.jpg",
                "role": "CU",
                "location": "30.0444,31.2357",
                "location2_lat": 30.0444,
                "location2_lng": 31.2357,
                "average_rating": 4.5
            },
            "provider": {
                "id": 2,
                "name": "Driver Smith",
                "phone": "+0987654321",
                "email": "driver@example.com",
                "image": "/media/user/images/driver.jpg",
                "role": "PR",
                "location": "30.0444,31.2357",
                "location2_lat": 30.0444,
                "location2_lng": 31.2357,
                "average_rating": 4.8
            },
            "service": {
                "id": 1,
                "name": "Transportation"
            },
            "status": "finished",
            "pickup_lat": 30.0444,
            "pickup_lng": 31.2357,
            "drop_lat": 30.0555,
            "drop_lng": 31.2468,
            "created_at": "2024-01-15T10:30:00Z",
            "service_price_info": {
                "application_fee": 5.00,
                "service_price": 15.00,
                "delivery_fee_per_km": 2.50,
                "distance_km": 2.5,
                "delivery_fee_total": 6.25,
                "total_price": 26.25
            },
            "rating_info": {
                "driver_rating": 5,
                "customer_rating": 4,
                "driver_comment": "Great customer!",
                "customer_comment": "Excellent service",
                "has_rating": true
            },
            "ride_type": "customer"
        }
    ],
    "statistics": {
        "total_rides": 25,
        "completed_rides": 20,
        "cancelled_rides": 3,
        "driver_earnings": 0,
        "customer_spent": 0,
        "completion_rate": 80.0
    }
}
```

### Error Responses

#### 401 Unauthorized

```json
{
    "detail": "Authentication credentials were not provided."
}
```

#### 403 Forbidden

```json
{
    "detail": "You do not have permission to perform this action."
}
```

## Examples

### Example 1: Get All Ride History

```bash
curl -X GET \
  http://localhost:8000/api/auth/rides/history/ \
  -H "Authorization: Token your_token_here"
```

### Example 2: Get Only Customer Rides

```bash
curl -X GET \
  "http://localhost:8000/api/auth/rides/history/?ride_type=customer" \
  -H "Authorization: Token your_token_here"
```

### Example 3: Get Only Driver Rides

```bash
curl -X GET \
  "http://localhost:8000/api/auth/rides/history/?ride_type=driver" \
  -H "Authorization: Token your_token_here"
```

### Example 4: Get Completed Rides Only

```bash
curl -X GET \
  "http://localhost:8000/api/auth/rides/history/?status=finished" \
  -H "Authorization: Token your_token_here"
```

### Example 5: Get Rides from Date Range

```bash
curl -X GET \
  "http://localhost:8000/api/auth/rides/history/?start_date=2024-01-01&end_date=2024-01-31" \
  -H "Authorization: Token your_token_here"
```

### Example 6: Get Paginated Results

```bash
curl -X GET \
  "http://localhost:8000/api/auth/rides/history/?page=2&page_size=10" \
  -H "Authorization: Token your_token_here"
```

## JavaScript Examples

### Using Fetch API

```javascript
// Get ride history
async function getRideHistory(params = {}) {
    const queryString = new URLSearchParams(params).toString();
    const url = `/api/auth/rides/history/${queryString ? '?' + queryString : ''}`;
    
    const response = await fetch(url, {
        method: 'GET',
        headers: {
            'Authorization': `Token ${token}`,
            'Content-Type': 'application/json',
        }
    });
    
    if (response.ok) {
        const data = await response.json();
        console.log('Ride history:', data);
        return data;
    } else {
        const error = await response.json();
        console.error('Failed to get ride history:', error);
        throw error;
    }
}

// Usage examples
getRideHistory(); // Get all rides
getRideHistory({ ride_type: 'customer' }); // Get customer rides only
getRideHistory({ status: 'finished' }); // Get completed rides only
getRideHistory({ 
    start_date: '2024-01-01', 
    end_date: '2024-01-31' 
}); // Get rides from date range
```

### Using Axios

```javascript
import axios from 'axios';

// Get ride history
const getRideHistory = async (params = {}) => {
    try {
        const response = await axios.get('/api/auth/rides/history/', {
            headers: {
                'Authorization': `Token ${token}`,
                'Content-Type': 'application/json',
            },
            params: params
        });
        console.log('Ride history:', response.data);
        return response.data;
    } catch (error) {
        console.error('Failed to get ride history:', error.response.data);
        throw error;
    }
};

// Usage
getRideHistory({ ride_type: 'driver', status: 'finished' });
```

## Python Examples

### Using Requests

```python
import requests

def get_ride_history(token, params=None):
    headers = {
        'Authorization': f'Token {token}',
        'Content-Type': 'application/json'
    }
    
    response = requests.get(
        'http://localhost:8000/api/auth/rides/history/',
        headers=headers,
        params=params
    )
    
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f'Failed to get ride history: {response.text}')

# Usage examples
# Get all rides
all_rides = get_ride_history(token)

# Get customer rides only
customer_rides = get_ride_history(token, {'ride_type': 'customer'})

# Get completed rides
completed_rides = get_ride_history(token, {'status': 'finished'})

# Get rides from date range
date_range_rides = get_ride_history(token, {
    'start_date': '2024-01-01',
    'end_date': '2024-01-31'
})
```

## Response Fields Explanation

### Ride Object Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | integer | Unique ride ID |
| `client` | object | Customer information |
| `provider` | object | Driver information |
| `service` | object | Service information |
| `status` | string | Ride status (pending, accepted, starting, arriving, finished, cancelled) |
| `pickup_lat` | float | Pickup location latitude |
| `pickup_lng` | float | Pickup location longitude |
| `drop_lat` | float | Drop location latitude |
| `drop_lng` | float | Drop location longitude |
| `created_at` | string | Ride creation timestamp |
| `service_price_info` | object | Pricing information |
| `rating_info` | object | Rating information |
| `ride_type` | string | Whether user is "customer" or "driver" in this ride |

### Service Price Info Fields

| Field | Type | Description |
|-------|------|-------------|
| `application_fee` | float | Base application fee |
| `service_price` | float | Service price |
| `delivery_fee_per_km` | float | Delivery fee per kilometer |
| `distance_km` | float | Total distance in kilometers |
| `delivery_fee_total` | float | Total delivery fee |
| `total_price` | float | Total ride price |

### Rating Info Fields

| Field | Type | Description |
|-------|------|-------------|
| `driver_rating` | integer | Driver rating (1-5) |
| `customer_rating` | integer | Customer rating (1-5) |
| `driver_comment` | string | Driver's comment |
| `customer_comment` | string | Customer's comment |
| `has_rating` | boolean | Whether the ride has been rated |

### Statistics Fields

| Field | Type | Description |
|-------|------|-------------|
| `total_rides` | integer | Total number of rides |
| `completed_rides` | integer | Number of completed rides |
| `cancelled_rides` | integer | Number of cancelled rides |
| `driver_earnings` | float | Total earnings (for drivers) |
| `customer_spent` | float | Total amount spent (for customers) |
| `completion_rate` | float | Percentage of completed rides |

## Filtering Options

### By Status

- `pending`: Rides waiting for driver acceptance
- `accepted`: Rides accepted by driver
- `starting`: Rides that have started
- `arriving`: Driver is arriving at pickup location
- `finished`: Completed rides
- `cancelled`: Cancelled rides

### By Ride Type

- `customer`: Rides where the user is the customer
- `driver`: Rides where the user is the driver

### By Date Range

Use `start_date` and `end_date` parameters in YYYY-MM-DD format to filter rides by creation date.

## Pagination

The API supports pagination with the following parameters:

- `page`: Page number (starts from 1)
- `page_size`: Number of rides per page (default: 10)

## Notes

1. **Authentication**: Users can only see their own ride history.

2. **Ride Type**: The `ride_type` field indicates whether the authenticated user was the customer or driver in each ride.

3. **Statistics**: The statistics are calculated based on the filtered results, not all rides.

4. **Pricing**: Service price information is calculated based on the provider's pricing settings and ride distance.

5. **Ratings**: Rating information is only available for completed rides.

6. **Performance**: The API uses database optimization with `select_related` and `prefetch_related` for efficient queries.

## Error Handling

The API provides detailed error messages for various scenarios:

- **Authentication errors**: When no valid token is provided
- **Permission errors**: When the user doesn't have permission to perform the action
- **Validation errors**: When query parameters are invalid

## Testing

You can test the API using curl, Postman, or any HTTP client. Make sure to:

1. Include a valid authentication token
2. Use the correct query parameters for filtering
3. Handle pagination for large datasets 