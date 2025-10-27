"""
Django management command to create a superuser group with permissions
for Authentication, Products, Points, Purchases, Car Rentals, Services,
Ride, Configurations, Coupons, Notifications, Scheduled Rides, and Restaurant models.
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.db import transaction


class Command(BaseCommand):
    help = 'Creates a superuser group with permissions for specified models'

    def add_arguments(self, parser):
        parser.add_argument(
            '--group-name',
            type=str,
            default='Super User',
            help='Name of the group to create (default: Super User)',
        )
        parser.add_argument(
            '--models',
            type=str,
            nargs='+',
            help='Specific models to include (space-separated). If not provided, all models will be included.',
        )
        parser.add_argument(
            '--exclude-models',
            type=str,
            nargs='+',
            help='Models to exclude (space-separated).',
        )

    def handle(self, *args, **options):
        group_name = options['group_name']
        selected_models = options.get('models')
        exclude_models = options.get('exclude_models', [])
        
        # Define all available models (all in authentication app)
        # These are the model names as they appear in Django ContentType (lowercase, no spaces)
        all_available_models = [
            # Authentication models
            'user', 'userotp', 'provider', 'customer', 'driverprofile',
            'drivercar', 'drivercarimage', 'customerplace',
            # Products
            'product', 'productimage', 'productrestaurant',
            'productimagerestaurant', 'productcategory',
            # Points
            'userpoints',
            # Purchases
            'purchase', 'carpurchase',
            # Car Rentals
            'caragency', 'caravailability', 'carrental',
            'carsalelisting', 'carsaleimage',
            # Services
            'service', 'subservice', 'serviceimage',
            'nameofcar', 'providerservicepricing',
            # Ride
            'ridestatus', 'rating',
            # Configurations
            'pricingzone', 'whatsappapisettings', 'platformsettings',
            # Coupons
            'coupon', 'couponrestaurant',
            # Notifications
            'notification',
            # Scheduled Ride
            'scheduledride', 'scheduledriderating',
            # Restaurant models
            'restaurantmodel', 'workingday', 'order', 'orderitem',
            'cart', 'cartitem', 'reviewrestaurant', 'offerrestaurant',
            'deliveryaddress', 'invoice', 'restaurantreportsproxy',
        ]
        
        # Determine which models to use
        if selected_models:
            # Use only specified models
            models_to_permission = [m.lower() for m in selected_models]
            self.stdout.write(f'Using specified models: {", ".join(models_to_permission)}')
        else:
            # Use all available models
            models_to_permission = all_available_models.copy()
        
        # Exclude specified models
        if exclude_models:
            exclude_models_lower = [m.lower() for m in exclude_models]
            models_to_permission = [m for m in models_to_permission if m.lower() not in exclude_models_lower]
            self.stdout.write(f'Excluding models: {", ".join(exclude_models_lower)}')
        
        # Remove duplicates while preserving order
        unique_models = list(dict.fromkeys(models_to_permission))
        
        try:
            with transaction.atomic():
                # Create or get the group
                group, created = Group.objects.get_or_create(name=group_name)
                
                if created:
                    self.stdout.write(
                        self.style.SUCCESS(f'Successfully created group "{group_name}"')
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(f'Group "{group_name}" already exists. Updating permissions...')
                    )
                
                # Clear existing permissions
                group.permissions.clear()
                
                # Collect all permissions for the specified models
                permissions_added = 0
                permissions_not_found = []
                
                for model_name in unique_models:
                    try:
                        # Get content type for the model
                        # Try different variations of the model name
                        content_type = None
                        model_variations = [
                            model_name.lower(),
                            model_name,
                            model_name.replace('_', ''),
                        ]
                        
                        for variation in model_variations:
                            try:
                                content_type = ContentType.objects.get(
                                    app_label='authentication',
                                    model=variation
                                )
                                break
                            except ContentType.DoesNotExist:
                                continue
                        
                        if not content_type:
                            # Try to find by searching all content types
                            all_cts = ContentType.objects.filter(app_label='authentication')
                            for ct in all_cts:
                                if ct.model.lower() == model_name.lower():
                                    content_type = ct
                                    break
                        
                        if content_type:
                            # Get all permissions for this model (add, change, delete, view)
                            model_perms = Permission.objects.filter(
                                content_type=content_type
                            )
                            
                            # Add permissions to group
                            for perm in model_perms:
                                group.permissions.add(perm)
                                permissions_added += 1
                                
                            self.stdout.write(
                                f'  ✓ Added permissions for {model_name}'
                            )
                        else:
                            permissions_not_found.append(model_name)
                            self.stdout.write(
                                self.style.WARNING(
                                    f'  ✗ Model "{model_name}" not found'
                                )
                            )
                        
                    except Exception as e:
                        permissions_not_found.append(model_name)
                        self.stdout.write(
                            self.style.WARNING(
                                f'  ✗ Error for "{model_name}": {str(e)}'
                            )
                        )
                
                # Summary
                self.stdout.write('')
                self.stdout.write(
                    self.style.SUCCESS(
                        f'✓ Successfully configured group "{group_name}"'
                    )
                )
                self.stdout.write(f'  - Permissions added: {permissions_added}')
                
                if permissions_not_found:
                    self.stdout.write(
                        self.style.WARNING(
                            f'  - Models not found: {", ".join(permissions_not_found)}'
                        )
                    )
                
                self.stdout.write('')
                self.stdout.write(
                    self.style.SUCCESS(
                        f'You can now assign users to the "{group_name}" group '
                        f'in the Django admin interface to grant them these permissions.'
                    )
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error: {str(e)}')
            )
            raise

