# Generated by Django 2.2.6 on 2020-01-21 15:18

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('assets', '0003_migration_to_django2'),
    ]

    operations = [
        migrations.AlterField(
            model_name='medium',
            name='gallery',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='media', to='assets.Gallery'),
        ),
    ]
