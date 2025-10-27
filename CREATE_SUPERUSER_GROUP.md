# Super User Group Setup Instructions

This document explains how to create a superuser group in Django admin with permissions for all the specified models.

## Overview

A management command has been created to automatically set up a "Super User" group with permissions for:
- **Authentication**: User, UserOtp, Provider, Customer, DriverProfile, DriverCar, DriverCarImage, CustomerPlace
- **Products**: Product, ProductImage, ProductRestaurant, ProductImageRestaurant, ProductCategory
- **Points**: UserPoints
- **Purchases**: Purchase, CarPurchase
- **Car Rentals**: CarAgency, CarAvailability, CarRental, CarSaleListing, CarSaleImage
- **Services**: Service, SubService, ServiceImage, NameOfCar, ProviderServicePricing
- **Ride**: RideStatus, Rating
- **Configurations**: PricingZone, WhatsAppAPISettings, PlatformSettings
- **Coupons**: Coupon, CouponRestaurant
- **Notifications**: Notification
- **Scheduled Ride**: ScheduledRide, ScheduledRideRating
- **Restaurant Models**: RestaurantModel, WorkingDay, Order, OrderItem, Cart, CartItem, ReviewRestaurant, OfferRestaurant, DeliveryAddress, Invoice, RestaurantReportsProxy

## Steps to Create the Super User Group

### 1. Activate your virtual environment (if you have one)
```bash
source .venv/bin/activate
# or
source .venv1/bin/activate
# or
source .venv-1/bin/activate
```

### 2. Run the management command
```bash
python manage.py create_superuser_group
```

You can also specify a custom group name:
```bash
python manage.py create_superuser_group --group-name "Custom Group Name"
```

### 3. Assign users to the group in Django Admin

1. Go to http://0.0.0.0:8000/admin/
2. Navigate to **Groups** under **Authentication and Authorization**
3. Find the "Super User" group
4. Click on it to edit
5. In the **Users** section, select the users you want to add to this group
6. Click **Save**

## Alternative: Manual Setup via Django Admin

If you prefer to set up the group manually:

1. Go to http://0.0.0.0:8000/admin/auth/group/
2. Click **Add Group**
3. Name it "Super User"
4. In the **Permissions** section, search for and add permissions for all the models listed above
5. Assign users to the group

## Verifying the Setup

After running the command, you should see output like:
```
Successfully created group "Super User"
  ✓ Added permissions for user
  ✓ Added permissions for provider
  ✓ Added permissions for product
  ... (and so on)
  
✓ Successfully configured group "Super User"
  - Permissions added: XXX
```

## Notes

- The management command automatically clears and updates permissions if the group already exists
- All permissions (add, change, delete, view) are granted for each model
- Users added to this group will have full access to manage all the specified models
- The Group admin interface has been customized to show permission counts for easier management

## Troubleshooting

If you encounter issues:

1. **Missing dependencies**: Make sure all dependencies are installed:
   ```bash
   pip install -r requirements.txt
   ```

2. **Database not migrated**: Run migrations first:
   ```bash
   python manage.py migrate
   ```

3. **Model not found warnings**: Some models might not exist or might be commented out. The command will continue and skip those models.

## Files Created

- `/authentication/management/commands/create_superuser_group.py` - The management command
- Custom Group admin registration in `/authentication/admin.py`

