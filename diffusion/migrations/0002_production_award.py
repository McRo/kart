# -*- coding: utf-8 -*-
# Generated by Django 1.11.21 on 2019-06-07 13:41
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django_countries.fields


class Migration(migrations.Migration):

    dependencies = [
        ('people', '0002_updatefresnoyprofile'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('production', '0007_task_and_organisation'),
        ('diffusion', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Diffusion',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ],
        ),
        migrations.CreateModel(
            name='MetaAward',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('label', models.CharField(max_length=255, null=True)),
                ('description', models.TextField(null=True)),
                ('type', models.CharField(choices=[(b'INDIVIDUAL', b'Individual'), (b'GROUP', b'Group'), (b'CAREER', b'Career'), (b'OTHER', b'Other')], max_length=10, null=True)),
                ('event', models.ForeignKey(help_text=b'Main Event', null=True, on_delete=django.db.models.deletion.CASCADE, related_name='meta_award', to='production.Event')),
                ('task', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='meta_award', to='production.StaffTask')),
            ],
        ),
        migrations.AddField(
            model_name='award',
            name='amount',
            field=models.CharField(blank=True, help_text=b'money, visibility, currency free', max_length=255),
        ),
        migrations.AddField(
            model_name='award',
            name='artist',
            field=models.ManyToManyField(blank=True, help_text=b'Staff or Artist', related_name='award', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='award',
            name='artwork',
            field=models.ManyToManyField(blank=True, related_name='award', to='production.Artwork'),
        ),
        migrations.AddField(
            model_name='award',
            name='date',
            field=models.DateField(null=True),
        ),
        migrations.AddField(
            model_name='award',
            name='event',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='award', to='production.Event'),
        ),
        migrations.AddField(
            model_name='award',
            name='ex_aequo',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='award',
            name='giver',
            field=models.ManyToManyField(blank=True, help_text=b'Who hands the arward', related_name='give_award', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='award',
            name='note',
            field=models.TextField(blank=True, help_text=b'Free note'),
        ),
        migrations.AddField(
            model_name='award',
            name='sponsor',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='award', to='people.Organization'),
        ),
        migrations.AddField(
            model_name='place',
            name='address',
            field=models.CharField(max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='place',
            name='city',
            field=models.CharField(blank=True, max_length=50),
        ),
        migrations.AddField(
            model_name='place',
            name='country',
            field=django_countries.fields.CountryField(default=b'', max_length=2),
        ),
        migrations.AddField(
            model_name='place',
            name='latitude',
            field=models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True),
        ),
        migrations.AddField(
            model_name='place',
            name='longitude',
            field=models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True),
        ),
        migrations.AddField(
            model_name='place',
            name='zipcode',
            field=models.CharField(blank=True, help_text=b'Code postal / Zipcode', max_length=10),
        ),
        migrations.AlterField(
            model_name='place',
            name='description',
            field=models.TextField(null=True),
        ),
        migrations.AlterField(
            model_name='place',
            name='organization',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='places', to='people.Organization'),
        ),
        migrations.AddField(
            model_name='award',
            name='meta_award',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='award', to='diffusion.MetaAward'),
        ),
    ]
