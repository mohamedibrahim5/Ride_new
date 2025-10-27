"""
Example command to create a restricted superuser group with only specific models visible.
This is a helper command that shows how to create groups with limited model access.
"""
from django.core.management.base import BaseCommand
from django.core.management import call_command


class Command(BaseCommand):
    help = 'Creates a restricted superuser group with only specific models visible'

    def add_arguments(self, parser):
        parser.add_argument(
            '--group-name',
            type=str,
            default='Restricted Super User',
            help='Name of the group to create',
        )

    def handle(self, *args, **options):
        group_name = options['group_name']
        
        # Define which models should be visible to this restricted superuser
        # Modify this list to include only the models you want visible
        visible_models = [
            # Authentication - only users and providers
            'user', 'provider', 'customer',
            # Products - only restaurant products
            'productrestaurant', 'productcategory',
            # Points
            'userpoints',
            # Restaurant models - only main models
            'restaurantmodel', 'order', 'orderitem',
            # Coupons
            'couponrestaurant',
            # Notifications
            'notification',
        ]
        
        self.stdout.write(
            self.style.SUCCESS(f'Creating restricted group "{group_name}" with limited models...')
        )
        
        # Call the main create_superuser_group command with specific models
        call_command(
            'create_superuser_group',
            group_name=group_name,
            models=visible_models
        )
        
        self.stdout.write('')
        self.stdout.write(
            self.style.SUCCESS(
                f'✓ Restricted group "{group_name}" created successfully!\n'
                f'  Models visible: {", ".join(visible_models)}\n'
                f'  Note: To hide models from this group in admin, use RestrictedModelAdminMixin\n'
                f'  See CREATE_SUPERUSER_GROUP.md for details.'
            )
        )

