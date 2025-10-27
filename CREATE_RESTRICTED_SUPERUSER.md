# Creating Restricted Superuser Groups

This guide explains how to create superuser groups that can only see specific models in the Django admin interface.

## Overview

There are two ways to restrict which models a superuser group can see:

1. **Permissions-based**: Only grant permissions for specific models
2. **Visibility-based**: Use the `RestrictedModelAdminMixin` to hide models from admin interface

## Method 1: Create Group with Selected Models Only

### Basic Usage

Create a group with only specific models:

```bash
python manage.py create_superuser_group --group-name "Restricted Admin" --models user provider customer product restaurantmodel order
```

### Exclude Specific Models

Create a group with all models except some:

```bash
python manage.py create_superuser_group --group-name "Admin No Config" --exclude-models pricingzone whatsappapisettings platformsettings
```

### Example: Restaurant Manager Group

```bash
python manage.py create_superuser_group \
  --group-name "Restaurant Manager" \
  --models restaurantmodel productrestaurant productcategory order orderitem couponrestaurant user customer
```

## Method 2: Hide Models Using RestrictedModelAdminMixin

### Step 1: Apply the Mixin to Admin Classes

Edit `authentication/admin.py` and add the mixin to restrict visibility:

```python
from authentication.admin_mixins import RestrictedModelAdminMixin

# Example: Only show RestaurantModel to Super User group
@admin.register(RestaurantModel)
class RestaurantModelAdmin(RestrictedModelAdminMixin, admin.ModelAdmin):
    visible_to_super_user_only = True  # Only Super User group can see
    # ... rest of your admin configuration ...

# Example: Show to multiple groups
@admin.register(ProductRestaurant)
class ProductRestaurantAdmin(RestrictedModelAdminMixin, admin.ModelAdmin):
    visible_groups = ['Super User', 'Restaurant Manager']  # Multiple groups
    # ... rest of your admin configuration ...
```

### Step 2: Create the Restricted Group

```bash
# Create group with limited permissions
python manage.py create_superuser_group --group-name "Restricted Admin" --models user provider restaurantmodel order

# Or use the helper command
python manage.py create_restricted_superuser_group --group-name "Restricted Admin"
```

## Complete Example

Let's create a "Restaurant Manager" group that can only see restaurant-related models:

### 1. Create the Group

```bash
python manage.py create_superuser_group \
  --group-name "Restaurant Manager" \
  --models \
    user customer provider \
    restaurantmodel productrestaurant productcategory \
    order orderitem couponrestaurant \
    notification
```

### 2. (Optional) Restrict Model Visibility in Admin

Edit `authentication/admin.py`:

```python
from authentication.admin_mixins import RestrictedModelAdminMixin

# Make RestaurantModel only visible to Restaurant Manager group
@admin.register(RestaurantModel)
class RestaurantModelAdmin(RestrictedModelAdminMixin, admin.ModelAdmin):
    visible_groups = ['Super User', 'Restaurant Manager']
    # ... existing configuration ...
```

### 3. Assign Users to the Group

1. Go to http://0.0.0.0:8000/admin/
2. Navigate to **Groups**
3. Find "Restaurant Manager" group
4. Add users to this group

## Available Models

Here are all available models you can include:

### Authentication
- `user`, `userotp`, `provider`, `customer`, `driverprofile`, `drivercar`, `drivercarimage`, `customerplace`

### Products
- `product`, `productimage`, `productrestaurant`, `productimagerestaurant`, `productcategory`

### Points & Purchases
- `userpoints`, `purchase`, `carpurchase`

### Car Rentals
- `caragency`, `caravailability`, `carrental`, `carsalelisting`, `carsaleimage`

### Services
- `service`, `subservice`, `serviceimage`, `nameofcar`, `providerservicepricing`

### Ride
- `ridestatus`, `rating`

### Configurations
- `pricingzone`, `whatsappapisettings`, `platformsettings`

### Coupons
- `coupon`, `couponrestaurant`

### Notifications
- `notification`

### Scheduled Ride
- `scheduledride`, `scheduledriderating`

### Restaurant Models
- `restaurantmodel`, `workingday`, `order`, `orderitem`, `cart`, `cartitem`, `reviewrestaurant`, `offerrestaurant`, `deliveryaddress`, `invoice`, `restaurantreportsproxy`

## Troubleshooting

### Models Not Showing Up

1. **Check permissions**: Make sure the group has permissions for the model
   ```bash
   python manage.py create_superuser_group --group-name "Your Group" --models yourmodel
   ```

2. **Check user assignment**: User must be assigned to the group and have `is_staff=True`

3. **Check mixin configuration**: If using `RestrictedModelAdminMixin`, verify the `visible_groups` setting

### Permission Denied Errors

- Ensure users have `is_staff=True`
- Verify the group has the correct permissions
- Check that the model admin doesn't have additional restrictions

## Commands Summary

```bash
# Full superuser group (all models)
python manage.py create_superuser_group

# Custom group with specific models
python manage.py create_superuser_group --group-name "Group Name" --models model1 model2 model3

# Group excluding some models
python manage.py create_superuser_group --group-name "Group Name" --exclude-models model1 model2

# Pre-configured restricted group
python manage.py create_restricted_superuser_group --group-name "Restricted Admin"
```

