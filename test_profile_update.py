#!/usr/bin/env python3
"""
Test script for the new profile update functionality.
This demonstrates how to use the PATCH endpoint for updating user profiles.
"""

import requests
import json

# Configuration
BASE_URL = "http://localhost:8000/api/auth/"  # Adjust this to your server URL
TOKEN = "your_auth_token_here"  # Replace with actual token

def test_profile_update():
    """Test the profile update functionality"""
    
    # Headers for authenticated requests
    headers = {
        "Authorization": f"Token {TOKEN}",
        "Content-Type": "application/json"
    }
    
    # Test data for profile update
    update_data = {
        "name": "Updated User Name",
        "email": "updated.email@example.com",
        "location": "30.0444,31.2357",  # Cairo coordinates
        "location2_lat": 30.0444,
        "location2_lng": 31.2357
    }
    
    print("Testing Profile Update...")
    print(f"Update data: {json.dumps(update_data, indent=2)}")
    
    try:
        # Make PATCH request to update profile
        response = requests.patch(
            f"{BASE_URL}profile/update/",
            headers=headers,
            json=update_data
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ Profile update successful!")
            print("Updated profile data:")
            print(json.dumps(response.json(), indent=2))
        else:
            print("❌ Profile update failed!")
            print(f"Error: {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")

def test_profile_update_with_image():
    """Test profile update with image upload"""
    
    headers = {
        "Authorization": f"Token {TOKEN}"
        # Note: Don't set Content-Type for multipart/form-data
    }
    
    # Test data with image
    update_data = {
        "name": "User with Image",
        "email": "user.with.image@example.com",
        "location": "30.0444,31.2357"
    }
    
    # Prepare files for upload (replace with actual image path)
    files = {
        'image': ('profile_image.jpg', open('path/to/your/image.jpg', 'rb'), 'image/jpeg')
    }
    
    print("Testing Profile Update with Image...")
    
    try:
        response = requests.patch(
            f"{BASE_URL}profile/update/",
            headers=headers,
            data=update_data,
            files=files
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ Profile update with image successful!")
            print("Updated profile data:")
            print(json.dumps(response.json(), indent=2))
        else:
            print("❌ Profile update with image failed!")
            print(f"Error: {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")

def test_invalid_location_format():
    """Test profile update with invalid location format"""
    
    headers = {
        "Authorization": f"Token {TOKEN}",
        "Content-Type": "application/json"
    }
    
    # Invalid location format
    update_data = {
        "name": "Test User",
        "location": "invalid_location_format"
    }
    
    print("Testing Profile Update with Invalid Location...")
    
    try:
        response = requests.patch(
            f"{BASE_URL}profile/update/",
            headers=headers,
            json=update_data
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 400:
            print("✅ Correctly rejected invalid location format!")
            print(f"Error message: {response.text}")
        else:
            print("❌ Should have rejected invalid location format!")
            print(f"Response: {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")

if __name__ == "__main__":
    print("🚀 Profile Update API Tests")
    print("=" * 50)
    
    # Run tests
    test_profile_update()
    print("\n" + "=" * 50)
    
    # Uncomment to test image upload (requires actual image file)
    # test_profile_update_with_image()
    # print("\n" + "=" * 50)
    
    test_invalid_location_format()
    print("\n" + "=" * 50)
    
    print("✅ All tests completed!") 