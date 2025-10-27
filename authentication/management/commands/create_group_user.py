"""
Management command to create a user for a specific group with username and password.
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group
from authentication.models import User
from django.db import connection


class Command(BaseCommand):
    help = 'Creates a user and assigns them to a group'

    def add_arguments(self, parser):
        parser.add_argument(
            '--group-name',
            type=str,
            required=True,
            help='Name of the group to assign the user to',
        )
        parser.add_argument(
            '--name',
            type=str,
            required=True,
            help='Full name of the user',
        )
        parser.add_argument(
            '--phone',
            type=str,
            required=True,
            help='Phone number (username) for the user',
        )
        parser.add_argument(
            '--password',
            type=str,
            required=True,
            help='Password for the user',
        )
        parser.add_argument(
            '--email',
            type=str,
            default='',
            help='Email address (optional)',
        )
        parser.add_argument(
            '--role',
            type=str,
            default='AD',
            help='User role (default: AD for Admin)',
        )
        parser.add_argument(
            '--staff',
            action='store_true',
            help='Make user a staff member (required for admin access)',
        )

    def handle(self, *args, **options):
        group_name = options['group_name']
        name = options['name']
        phone = options['phone']
        password = options['password']
        email = options.get('email', '')
        role = options.get('role', 'AD')
        is_staff = options.get('staff', True)
        
        try:
            # Get or create the group
            try:
                group = Group.objects.get(name=group_name)
            except Group.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'Group "{group_name}" does not exist.')
                )
                self.stdout.write('Available groups:')
                for g in Group.objects.all():
                    self.stdout.write(f'  - {g.name}')
                return
            
            # Check if user already exists
            if User.objects.filter(phone=phone).exists():
                self.stdout.write(
                    self.style.WARNING(f'User with phone {phone} already exists.')
                )
                return
            
            # Create the user
            user = User.objects.create_user(
                phone=phone,
                password=password,
                name=name,
                email=email,
                role=role,
                is_staff=is_staff,
                is_active=True
            )
            
            # Add user to group
            with connection.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO auth_user_groups (user_id, group_id) VALUES (%s, %s)",
                    [user.id, group.id]
                )
                connection.commit()
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'✓ Successfully created user "{name}" ({phone}) and added to group "{group_name}"'
                )
            )
            self.stdout.write(f'  - Phone (username): {phone}')
            self.stdout.write(f'  - Password: {password}')
            self.stdout.write(f'  - Group: {group_name}')
            self.stdout.write(f'  - Staff: {is_staff}')
            self.stdout.write('')
            self.stdout.write(
                self.style.SUCCESS(
                    f'User can now login at http://0.0.0.0:8000/admin/ '
                    f'with phone: {phone} and the password you provided.'
                )
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error: {str(e)}')
            )
            raise

