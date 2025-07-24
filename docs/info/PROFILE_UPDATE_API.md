# Profile Update API Documentation

## Overview

The Profile Update API allows authenticated users to update their profile information including name, email, image, and location. This endpoint supports PATCH requests for partial updates.

## Endpoint

```
PATCH /api/auth/profile/update/
```

## Authentication

This endpoint requires authentication. Include the user's token in the Authorization header:

```
Authorization: Token your_auth_token_here
```

## Request Format

### JSON Request

For text-only updates (name, email, location):

```http
PATCH /api/auth/profile/update/
Content-Type: application/json
Authorization: Token your_auth_token_here

{
    "name": "Updated User Name",
    "email": "updated.email@example.com",
    "location": "30.0444,31.2357"
}
```

### Multipart Form Data Request

For updates including image uploads:

```http
PATCH /api/auth/profile/update/
Authorization: Token your_auth_token_here

Content-Type: multipart/form-data

name: Updated User Name
email: updated.email@example.com
location: 30.0444,31.2357
image: [binary file data]
```

## Request Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `name` | string | No | User's display name |
| `email` | string | No | User's email address |
| `image` | file | No | Profile image file |
| `location` | string | No | Location in "latitude,longitude" format |

### Location Format

The location should be provided in string format: `"30.0444,31.2357"` (latitude,longitude)

The system will automatically parse the location string and update both the `location` field and the `location2_lat`/`location2_lng` fields to keep them synchronized.

## Response Format

### Success Response (200 OK)

```json
{
    "id": 1,
    "name": "Updated User Name",
    "phone": "+1234567890",
    "email": "updated.email@example.com",
    "image": "/media/user/images/profile_image.jpg",
    "role": "CU",
    "location": "30.0444,31.2357",
    "location2_lat": 30.0444,
    "location2_lng": 31.2357,
    "average_rating": 4.5
}
```

### Error Responses

#### 400 Bad Request - Invalid Location Format

```json
{
    "location": ["Invalid location format. Use 'latitude,longitude'"]
}
```

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

### Example 1: Update Name and Email

```bash
curl -X PATCH \
  http://localhost:8000/api/auth/profile/update/ \
  -H "Authorization: Token your_token_here" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "John Doe",
    "email": "john.doe@example.com"
  }'
```

### Example 2: Update Location

```bash
curl -X PATCH \
  http://localhost:8000/api/auth/profile/update/ \
  -H "Authorization: Token your_token_here" \
  -H "Content-Type: application/json" \
  -d '{
    "location": "30.0444,31.2357"
  }'
```

**Note:** When you update the location, the system automatically updates both the `location` field and the `location2_lat`/`location2_lng` fields to keep them synchronized.

### Example 3: Update Profile Image

```bash
curl -X PATCH \
  http://localhost:8000/api/auth/profile/update/ \
  -H "Authorization: Token your_token_here" \
  -F "name=John Doe" \
  -F "email=john.doe@example.com" \
  -F "image=@/path/to/profile_image.jpg"
```

### Example 4: Update All Fields

```bash
curl -X PATCH \
  http://localhost:8000/api/auth/profile/update/ \
  -H "Authorization: Token your_token_here" \
  -F "name=John Doe" \
  -F "email=john.doe@example.com" \
  -F "location=30.0444,31.2357" \
  -F "image=@/path/to/profile_image.jpg"
```

## JavaScript Examples

### Using Fetch API

```javascript
// Update profile with JSON data
async function updateProfile(profileData) {
    const response = await fetch('/api/auth/profile/update/', {
        method: 'PATCH',
        headers: {
            'Authorization': `Token ${token}`,
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(profileData)
    });
    
    if (response.ok) {
        const updatedProfile = await response.json();
        console.log('Profile updated:', updatedProfile);
    } else {
        const error = await response.json();
        console.error('Update failed:', error);
    }
}

// Update profile with image upload
async function updateProfileWithImage(formData) {
    const response = await fetch('/api/auth/profile/update/', {
        method: 'PATCH',
        headers: {
            'Authorization': `Token ${token}`,
            // Don't set Content-Type for multipart/form-data
        },
        body: formData
    });
    
    if (response.ok) {
        const updatedProfile = await response.json();
        console.log('Profile updated:', updatedProfile);
    } else {
        const error = await response.json();
        console.error('Update failed:', error);
    }
}

// Usage examples
updateProfile({
    name: 'John Doe',
    email: 'john.doe@example.com',
    location: '30.0444,31.2357'
});

// For image upload
const formData = new FormData();
formData.append('name', 'John Doe');
formData.append('email', 'john.doe@example.com');
formData.append('image', imageFile);
updateProfileWithImage(formData);
```

### Using Axios

```javascript
import axios from 'axios';

// Update profile with JSON data
const updateProfile = async (profileData) => {
    try {
        const response = await axios.patch('/api/auth/profile/update/', profileData, {
            headers: {
                'Authorization': `Token ${token}`,
                'Content-Type': 'application/json',
            }
        });
        console.log('Profile updated:', response.data);
        return response.data;
    } catch (error) {
        console.error('Update failed:', error.response.data);
        throw error;
    }
};

// Update profile with image upload
const updateProfileWithImage = async (formData) => {
    try {
        const response = await axios.patch('/api/auth/profile/update/', formData, {
            headers: {
                'Authorization': `Token ${token}`,
                'Content-Type': 'multipart/form-data',
            }
        });
        console.log('Profile updated:', response.data);
        return response.data;
    } catch (error) {
        console.error('Update failed:', error.response.data);
        throw error;
    }
};
```

## Python Examples

### Using Requests

```python
import requests

# Update profile with JSON data
def update_profile(token, profile_data):
    headers = {
        'Authorization': f'Token {token}',
        'Content-Type': 'application/json'
    }
    
    response = requests.patch(
        'http://localhost:8000/api/auth/profile/update/',
        headers=headers,
        json=profile_data
    )
    
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f'Update failed: {response.text}')

# Update profile with image upload
def update_profile_with_image(token, profile_data, image_path):
    headers = {
        'Authorization': f'Token {token}'
    }
    
    with open(image_path, 'rb') as image_file:
        files = {'image': image_file}
        response = requests.patch(
            'http://localhost:8000/api/auth/profile/update/',
            headers=headers,
            data=profile_data,
            files=files
        )
    
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f'Update failed: {response.text}')

# Usage
profile_data = {
    'name': 'John Doe',
    'email': 'john.doe@example.com',
    'location': '30.0444,31.2357'
}

try:
    updated_profile = update_profile(token, profile_data)
    print('Profile updated:', updated_profile)
except Exception as e:
    print('Error:', e)
```

## Notes

1. **Partial Updates**: This endpoint supports partial updates. You only need to include the fields you want to update.

2. **Image Upload**: When uploading images, use `multipart/form-data` format. The image will be stored in the `user/images/` directory.

3. **Location Validation**: The location must be in the format "latitude,longitude" (e.g., "30.0444,31.2357").

4. **Read-only Fields**: The following fields are read-only and cannot be updated:
   - `id`
   - `phone`
   - `role`
   - `average_rating`

5. **Authentication**: Users can only update their own profile. The endpoint automatically uses the authenticated user's profile.

## Error Handling

The API provides detailed error messages for various scenarios:

- **Invalid location format**: When the location string doesn't match the expected format
- **Authentication errors**: When no valid token is provided
- **Permission errors**: When the user doesn't have permission to perform the action
- **Validation errors**: When the provided data doesn't meet the validation requirements

## Testing

You can test the API using the provided test script:

```bash
python test_profile_update.py
```

Make sure to update the `BASE_URL` and `TOKEN` variables in the test script before running it. 