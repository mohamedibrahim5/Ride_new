# Groups Admin Dashboard Setup

## Overview

The Groups model is now fully visible and enhanced in the Django admin dashboard at `http://0.0.0.0:8000/admin/`.

## Features

The Group admin interface now includes:

1. **Enhanced List View** - Shows:
   - Group name
   - Number of users in the group (clickable link to filtered users)
   - Number of permissions
   - Preview of permissions (first 5 permissions + count)

2. **Better Organization** - Fieldsets with clear sections:
   - Group Information
   - Users (with helpful instructions)
   - Permissions (with management command hint)

3. **Search & Filter** - Easy to find groups by name

## How to Access Groups in Admin

1. **Navigate to Admin Dashboard**
   - Go to: `http://0.0.0.0:8000/admin/`
   - Login with your admin credentials

2. **Find Groups**
   - Look for **"Groups"** under **"Authentication and Authorization"** section
   - You should see all groups listed with user counts and permission counts

3. **Create a New Group**
   - Click **"Add Group"** button
   - Enter a group name
   - Select permissions
   - Save

4. **Edit Existing Group**
   - Click on any group name
   - Modify permissions
   - See user count (click to view users in that group)

## Quick Setup: Create Super User Group

Use the management command to quickly create a group with all necessary permissions:

```bash
python manage.py create_superuser_group
```

Or create a restricted group with specific models:

```bash
python manage.py create_superuser_group --group-name "Restaurant Manager" --models user restaurantmodel order productrestaurant
```

## Assigning Users to Groups

There are two ways to assign users to groups:

### Method 1: Via Group Admin
1. Go to **Groups** in admin
2. Click on the group you want to edit
3. Use the instructions in the Users section

### Method 2: Via User Admin (Recommended)
1. Go to **Users** in admin
2. Select a user to edit
3. Find the **"Groups"** field (if available)
4. Select the group(s) you want
5. Save

### Method 3: Via Management Command
Create a custom management command or use Django shell:

```python
from django.contrib.auth.models import Group
from authentication.models import User

group = Group.objects.get(name='Super User')
user = User.objects.get(phone='1234567890')
user.groups.add(group)
```

## Viewing Users in a Group

In the Groups list view:
- Click on the user count (e.g., "5 users")
- This will filter the Users list to show only users in that group

## Troubleshooting

### Groups Not Showing

1. **Check Admin Registration**
   - Groups should be registered automatically
   - Check that you're logged in as a superuser or staff member

2. **Check Permissions**
   - Ensure your user has permission to view Groups
   - Superusers see everything by default

3. **Clear Cache**
   - Restart Django development server
   - Clear browser cache

### User Count Not Working

- User count uses Django's auth system
- If User model has `groups = None`, the count might not reflect correctly
- Check database directly: `SELECT * FROM auth_user_groups WHERE group_id = X`

### Permissions Not Showing

- Make sure models are registered in admin
- Run migrations: `python manage.py migrate`
- Use the management command to add permissions automatically

## Admin Interface Location

Groups will appear in Django admin under:
- **Section**: Authentication and Authorization
- **Model**: Groups
- **URL**: `/admin/auth/group/`

## Example: Complete Workflow

1. **Create Super User Group**
   ```bash
   python manage.py create_superuser_group
   ```

2. **View in Admin**
   - Go to `http://0.0.0.0:8000/admin/auth/group/`
   - See "Super User" group with permission count

3. **Assign Users**
   - Go to Users admin
   - Edit a user
   - Assign to "Super User" group

4. **Verify**
   - Go back to Groups
   - Click on "Super User"
   - Check user count has increased

## Next Steps

- Create custom groups for different roles
- Use restricted groups to limit model access
- Set up role-based permissions for your team

For more details, see:
- `CREATE_SUPERUSER_GROUP.md` - Creating groups with permissions
- `CREATE_RESTRICTED_SUPERUSER.md` - Creating restricted groups
- `EXAMPLES_RESTRICTED_ADMIN.py` - Code examples

