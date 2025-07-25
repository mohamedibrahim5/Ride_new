# Generated by Django 5.2.4 on 2025-07-23 23:41

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        (
            "authentication",
            "0029_pricingzone_providerservicepricing_base_fare_and_more",
        ),
    ]

    operations = [
        migrations.CreateModel(
            name="WhatsAppAPISettings",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "instance_id",
                    models.CharField(max_length=100, verbose_name="Instance ID"),
                ),
                ("token", models.CharField(max_length=255, verbose_name="Token")),
            ],
            options={
                "verbose_name": "WhatsApp API Settings",
                "verbose_name_plural": "WhatsApp API Settings",
            },
        ),
    ]
