# Generated by Django 2.2.6 on 2020-01-08 11:01

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('common', '0002_beacon_x_y'),
    ]

    operations = [
        migrations.AlterField(
            model_name='btbeacon',
            name='uuid',
            field=models.UUIDField(unique=True),
        ),
        migrations.AlterField(
            model_name='website',
            name='language',
            field=models.CharField(choices=[('FR', 'Français'), ('EN', 'English')], max_length=2),
        ),
    ]
