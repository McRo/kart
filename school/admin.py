# -*- encoding: utf-8 -*-
from django.contrib import admin
from django.db import models
from django.db.models import Min

from pagedown.widgets import AdminPagedownWidget

from .models import (
    Promotion,
    Student,
    StudentApplication,
    StudentApplicationSetup,
    AdminStudentApplication,
    PhdStudent,
    ScienceStudent,
    VisitingStudent,
    TeachingArtist,
)


class StudentAdmin(admin.ModelAdmin):
    list_display = ("__str__", "number", "promotion", "graduate")
    search_fields = ("number", "artist__user__first_name", "artist__user__last_name", "artist__nickname")

    formfield_overrides = {
        models.TextField: {"widget": AdminPagedownWidget},
    }

    raw_id_fields = ('artist', 'user', 'promotion')
    autocomplete_lookup_fields = {'fk': ['artist', 'user', 'promotion']}


class StudentApplicationAdmin(admin.ModelAdmin):
    search_fields = [
        "artist__user__first_name",
        "artist__user__last_name",
    ]

    def _get_name(self, obj):
        if obj.artist:
            return obj.artist.user.get_full_name()

    _get_name.short_description = "Nom"

    list_display = (
        "campaign",
        "_get_name",
        "current_year_application_count",
        "remark",
    )


class StudentApplicationSetupAdmin(admin.ModelAdmin):

    def _get_name(self, obj):
        return obj.artist.user.get_full_name()

    list_display = (
        "name",
        "is_current_setup",
    )


@admin.register(TeachingArtist)
class TeachingArtistAdmin(admin.ModelAdmin):
    search_fields = [
        "artist__user__first_name",
        "artist__user__last_name",
        "artist__nickname",
    ]
    list_display = (
        "artist",
        "years",
    )
    # filter_vertical = ("artworks_supervision",)
    raw_id_fields = ('artist', 'pictures_gallery', 'artworks_supervision')
    autocomplete_lookup_fields = {
        'fk': [
            'artist',
            'pictures_gallery',
        ],
        'm2m': [
            'artworks_supervision',
        ],
    }

    def years(self, obj):
        # return the years of the supervision in a string separated by comma
        # get years of artwork supervisions
        years = obj.artworks_supervision.values_list('production_date__year', flat=True).distinct()
        # avoid duplicates and sort years
        years = sorted(set(years))
        return ", ".join(str(year - 1) + " - " + str(year) for year in years)

    years.short_description = 'Années de supervision'
    # sort by years of artwork supervisions
    years.admin_order_field = 'min_supervision_year'

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        # sort by the minimum year of artwork supervisions to avoid duplicates when sorting by years of supervision
        queryset = queryset.annotate(min_supervision_year=Min("artworks_supervision__production_date__year"))
        return queryset


@admin.register(AdminStudentApplication)
class AdminStudentApplicationAdmin(admin.ModelAdmin):
    search_fields = [
        "application__artist__user__first_name",
        "application__artist__user__last_name",
        "application__artist__nickname",
    ]
    ordering = ["-id", "-application__created_on__year", "application__artist__user__last_name"]

    def candidat(self, obj):
        if obj.application and obj.application.artist:
            return obj.application.artist.__str__()

    def year(self, obj):
        if obj.application and obj.application.campaign:
            return obj.application.campaign.promotion.starting_year

    list_display = (
        "id",
        "candidat",
        "year",
        "selected",
        "wait_listed",
    )


class PhdStudentAdmin(admin.ModelAdmin):
    # search without accents and case insensitive
    search_fields = [
        "student__artist__user__first_name__unaccent__icontains",
        "student__artist__user__last_name__unaccent__icontains",
        "student__artist__nickname__unaccent__icontains",
        "directors__first_name__unaccent__icontains",
        "directors__last_name__unaccent__icontains",
    ]
    list_display = (
        "__str__",
        "direction",
        "university",
        "defended",
    )
    ordering = ("student",)
    raw_id_fields = ('directors',)
    autocomplete_lookup_fields = {
        'm2m': [
            'directors',
        ]
    }

    admin.display(boolean=True)

    def direction(self, obj):
        return ", ".join([str(director) for director in obj.directors.all()])

    @admin.display(boolean=True)
    def defended(self, obj):
        return obj.thesis_file.name != ""


@admin.register(Promotion)
class PromotionAdmin(admin.ModelAdmin):
    search_fields = ['starting_year', 'name']
    list_display = (
        'years',
        'name',
    )
    list_display_links = ["name"]
    ordering = ('starting_year',)

    def years(self, obj):
        return "{0} - {1}".format(obj.starting_year, obj.ending_year)

    years.short_description = 'Années'


@admin.register(VisitingStudent)
class VisitingStudentAdmin(admin.ModelAdmin):
    search_fields = [
        "artist__user__first_name",
        "artist__user__last_name",
        "artist__nickname",
    ]
    list_display = (
        "artist",
        "reason",
    )


admin.site.register(StudentApplication, StudentApplicationAdmin)
admin.site.register(StudentApplicationSetup, StudentApplicationSetupAdmin)
admin.site.register(Student, StudentAdmin)
admin.site.register(PhdStudent, PhdStudentAdmin)
admin.site.register(ScienceStudent)
