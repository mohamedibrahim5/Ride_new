# Generated by Django 5.2 on 2025-06-27 21:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("authentication", "0018_provider_sub_service"),
    ]

    operations = [
        migrations.AlterField(
            model_name="provider",
            name="sub_service",
            field=models.CharField(
                blank=True, max_length=50, null=True, verbose_name="Sub Service"
            ),
        ),
    ]
