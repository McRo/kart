# Generated by Django 3.2.15 on 2023-06-07 14:55

import common.utils
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('production', '0011_ordering_productionorganizationtask'),
        ('people', '0006_languagesfield_newversion'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('assets', '0004_gallery_deletion'),
        ('school', '0010_studentapp_waitlist_position_and_ine_number'),
    ]

    operations = [
        migrations.AddField(
            model_name='promotion',
            name='picture',
            field=models.ImageField(blank=True, upload_to=common.utils.make_filepath),
        ),
        migrations.AddField(
            model_name='student',
            name='mention',
            field=models.TextField(blank=True, help_text='Mention', null=True),
        ),
        migrations.CreateModel(
            name='ScienceStudent',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('discipline', models.CharField(blank=True, max_length=50, null=True)),
                ('student', models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name='science_student', to='school.student')),
            ],
        ),
        migrations.CreateModel(
            name='PhdStudent',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('thesis_object', models.CharField(blank=True, max_length=150, null=True)),
                ('thesis_file', models.FileField(blank=True, help_text='thesis pdf file', null=True, upload_to=common.utils.make_filepath)),
                ('director', models.ForeignKey(blank=True, on_delete=django.db.models.deletion.PROTECT, related_name='phd_student', to=settings.AUTH_USER_MODEL)),
                ('student', models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name='phd_student', to='school.student')),
                ('university', models.ForeignKey(blank=True, on_delete=django.db.models.deletion.PROTECT, related_name='phd_student', to='people.organization')),
            ],
        ),
        migrations.CreateModel(
            name='TeachingArtist',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('presentation_text_fr', models.TextField(blank=True, help_text='General orientation text (not only bio) in FRENCH', null=True)),
                ('presentation_text_en', models.TextField(blank=True, help_text='General orientation text (not only bio) in ENGLISH', null=True)),
                ('artist', models.OneToOneField(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='teacher', to='people.artist')),
                ('artworks_supervision', models.ManyToManyField(blank=True, related_name='mentoring', to='production.Artwork')),
                ('pictures_gallery', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='teachingartist_pictures', to='assets.gallery')),
            ],
        ),
    ]