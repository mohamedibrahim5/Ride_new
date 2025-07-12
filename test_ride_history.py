#!/usr/bin/env python3
"""
Test script for the ride history API endpoint.
This demonstrates how to use the GET endpoint for retrieving ride history.
"""

import requests
import json
from datetime import datetime, timedelta

# Configuration
BASE_URL = "http://localhost:8000/api/auth/"  # Adjust this to your server URL
TOKEN = "your_auth_token_here"  # Replace with actual token

def test_ride_history():
    """Test the ride history functionality"""
    
    # Headers for authenticated requests
    headers = {
        "Authorization": f"Token {TOKEN}",
        "Content-Type": "application/json"
    }
    
    print("Testing Ride History API...")
    
    # Test 1: Get all ride history
    print("\n1. Getting all ride history...")
    try:
        response = requests.get(
            f"{BASE_URL}rides/history/",
            headers=headers
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Ride history retrieved successfully!")
            print(f"Total rides: {data.get('count', 0)}")
            print(f"Statistics: {data.get('statistics', {})}")
            
            # Show first few rides
            results = data.get('results', [])
            if results:
                print(f"\nFirst ride details:")
                first_ride = results[0]
                print(f"  ID: {first_ride.get('id')}")
                print(f"  Status: {first_ride.get('status')}")
                print(f"  Created: {first_ride.get('created_at')}")
                print(f"  Ride Type: {first_ride.get('ride_type')}")
        else:
            print("❌ Failed to get ride history!")
            print(f"Error: {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")

def test_ride_history_filters():
    """Test ride history with different filters"""
    
    headers = {
        "Authorization": f"Token {TOKEN}",
        "Content-Type": "application/json"
    }
    
    print("\n2. Testing ride history filters...")
    
    # Test filters
    filters = [
        {"ride_type": "customer", "description": "Customer rides only"},
        {"ride_type": "driver", "description": "Driver rides only"},
        {"status": "finished", "description": "Completed rides only"},
        {"status": "cancelled", "description": "Cancelled rides only"},
    ]
    
    for filter_params in filters:
        description = filter_params.pop("description")
        print(f"\nTesting: {description}")
        print(f"Parameters: {filter_params}")
        
        try:
            response = requests.get(
                f"{BASE_URL}rides/history/",
                headers=headers,
                params=filter_params
            )
            
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                count = data.get('count', 0)
                print(f"✅ Found {count} rides matching criteria")
                
                # Show statistics
                stats = data.get('statistics', {})
                if stats:
                    print(f"  Statistics: {stats}")
            else:
                print("❌ Filter test failed!")
                print(f"Error: {response.text}")
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Request failed: {e}")

def test_ride_history_date_range():
    """Test ride history with date range filter"""
    
    headers = {
        "Authorization": f"Token {TOKEN}",
        "Content-Type": "application/json"
    }
    
    print("\n3. Testing ride history with date range...")
    
    # Get date range for last 30 days
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    
    params = {
        "start_date": start_date,
        "end_date": end_date
    }
    
    print(f"Date range: {start_date} to {end_date}")
    
    try:
        response = requests.get(
            f"{BASE_URL}rides/history/",
            headers=headers,
            params=params
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            count = data.get('count', 0)
            print(f"✅ Found {count} rides in date range")
            
            # Show statistics
            stats = data.get('statistics', {})
            if stats:
                print(f"  Statistics: {stats}")
        else:
            print("❌ Date range test failed!")
            print(f"Error: {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")

def test_ride_history_pagination():
    """Test ride history pagination"""
    
    headers = {
        "Authorization": f"Token {TOKEN}",
        "Content-Type": "application/json"
    }
    
    print("\n4. Testing ride history pagination...")
    
    params = {
        "page": 1,
        "page_size": 5
    }
    
    try:
        response = requests.get(
            f"{BASE_URL}rides/history/",
            headers=headers,
            params=params
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            count = data.get('count', 0)
            results = data.get('results', [])
            next_page = data.get('next')
            
            print(f"✅ Pagination test successful!")
            print(f"Total rides: {count}")
            print(f"Rides on this page: {len(results)}")
            print(f"Next page available: {next_page is not None}")
            
            if results:
                print(f"First ride ID: {results[0].get('id')}")
                print(f"Last ride ID: {results[-1].get('id')}")
        else:
            print("❌ Pagination test failed!")
            print(f"Error: {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")

def test_ride_history_details():
    """Test getting detailed ride information"""
    
    headers = {
        "Authorization": f"Token {TOKEN}",
        "Content-Type": "application/json"
    }
    
    print("\n5. Testing ride history details...")
    
    try:
        response = requests.get(
            f"{BASE_URL}rides/history/",
            headers=headers,
            params={"page_size": 1}  # Get just one ride for detailed inspection
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            results = data.get('results', [])
            
            if results:
                ride = results[0]
                print("✅ Detailed ride information:")
                print(f"  Ride ID: {ride.get('id')}")
                print(f"  Status: {ride.get('status')}")
                print(f"  Created: {ride.get('created_at')}")
                print(f"  Ride Type: {ride.get('ride_type')}")
                
                # Client info
                client = ride.get('client', {})
                if client:
                    print(f"  Client: {client.get('name')} ({client.get('phone')})")
                
                # Provider info
                provider = ride.get('provider', {})
                if provider:
                    print(f"  Provider: {provider.get('name')} ({provider.get('phone')})")
                
                # Service info
                service = ride.get('service', {})
                if service:
                    print(f"  Service: {service.get('name')}")
                
                # Pricing info
                pricing = ride.get('service_price_info', {})
                if pricing:
                    print(f"  Total Price: ${pricing.get('total_price', 0)}")
                    print(f"  Distance: {pricing.get('distance_km', 0)} km")
                
                # Rating info
                rating = ride.get('rating_info', {})
                if rating:
                    print(f"  Has Rating: {rating.get('has_rating', False)}")
                    if rating.get('has_rating'):
                        print(f"  Driver Rating: {rating.get('driver_rating')}")
                        print(f"  Customer Rating: {rating.get('customer_rating')}")
            else:
                print("No rides found for detailed inspection")
        else:
            print("❌ Details test failed!")
            print(f"Error: {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")

if __name__ == "__main__":
    print("🚀 Ride History API Tests")
    print("=" * 50)
    
    # Run all tests
    test_ride_history()
    test_ride_history_filters()
    test_ride_history_date_range()
    test_ride_history_pagination()
    test_ride_history_details()
    
    print("\n" + "=" * 50)
    print("✅ All ride history tests completed!") 