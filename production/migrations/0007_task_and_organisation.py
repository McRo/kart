# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('production', '0006_FilmFormat'),
    ]

    operations = [
        migrations.AlterField(
            model_name='productionorganizationtask',
            name='production',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='organization_tasks', to='production.Production'),
        ),
        migrations.AlterField(
            model_name='productionstafftask',
            name='production',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='staff_tasks', to='production.Production'),
        ),
    ]
