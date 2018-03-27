# from django.conf.urls import include, url
from django.urls import include, path, re_path

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin

from tastypie.api import Api
from rest_framework import routers
from rest_framework_jwt.views import obtain_jwt_token

from people.api import ArtistResource, StaffResource, OrganizationResource
from production.api import (
    InstallationResource, FilmResource,
    PerformanceResource, EventResource, ExhibitionResource,
    ItineraryResource, ArtworkResource, StaffTaskResource
)
from diffusion.api import PlaceResource
from school.api import PromotionResource, StudentResource, StudentApplicationResource

from people.views import (
    ArtistViewSet, UserViewSet, FresnoyProfileViewSet,
    StaffViewSet, OrganizationViewSet
)
from people import views as people_views

from school.views import (
    PromotionViewSet, StudentViewSet,
    StudentAutocompleteSearchViewSet, StudentApplicationViewSet
)
from production.views import (
    FilmViewSet, InstallationViewSet,
    PerformanceViewSet, FilmGenreViewSet,
    InstallationGenreViewSet, EventViewSet,
    ItineraryViewSet,
    CollaboratorViewSet, PartnerViewSet, OrganizationTaskViewSet
)
from diffusion.views import PlaceViewSet
from common.views import BTBeaconViewSet, WebsiteViewSet
from assets import views as assets_views
from assets.views import GalleryViewSet, MediumViewSet


admin.autodiscover()

v1_api = Api(api_name='v1')
v1_api.register(InstallationResource())
v1_api.register(FilmResource())
v1_api.register(PerformanceResource())
v1_api.register(EventResource())
v1_api.register(OrganizationResource())
v1_api.register(StaffTaskResource())
v1_api.register(PromotionResource())
v1_api.register(StudentResource())
v1_api.register(StudentApplicationResource())
v1_api.register(ArtistResource())
v1_api.register(StaffResource())
v1_api.register(PlaceResource())
v1_api.register(ExhibitionResource())
v1_api.register(ItineraryResource())
v1_api.register(ArtworkResource())

v2_api = routers.DefaultRouter(trailing_slash=False)
v2_api.register(r'people/user', UserViewSet)
v2_api.register(r'people/userprofile', FresnoyProfileViewSet)
v2_api.register(r'people/artist', ArtistViewSet)
v2_api.register(r'people/staff', StaffViewSet)
v2_api.register(r'people/organization', OrganizationViewSet)
v2_api.register(r'people/organization-staff', OrganizationTaskViewSet)
v2_api.register(r'school/promotion', PromotionViewSet)
v2_api.register(r'school/student', StudentViewSet)
v2_api.register(r'school/student-application', StudentApplicationViewSet)
v2_api.register(r'school/student/search', StudentAutocompleteSearchViewSet, base_name="school-student-search")
v2_api.register(r'production/film', FilmViewSet)
v2_api.register(r'production/event', EventViewSet)
v2_api.register(r'production/itinerary', ItineraryViewSet)
v2_api.register(r'production/film/genre', FilmGenreViewSet)
v2_api.register(r'production/installation', InstallationViewSet)
v2_api.register(r'production/installation/genre', InstallationGenreViewSet)
v2_api.register(r'production/performance', PerformanceViewSet)
v2_api.register(r'production/collaborator', CollaboratorViewSet)
v2_api.register(r'production/partner', PartnerViewSet)
v2_api.register(r'diffusion/place', PlaceViewSet)
v2_api.register(r'common/beacon', BTBeaconViewSet)
v2_api.register(r'common/website', WebsiteViewSet)
v2_api.register(r'assets/gallery', GalleryViewSet)
v2_api.register(r'assets/medium', MediumViewSet)


urlpatterns = [
                       path('v2/', include(v2_api.urls)),
                       path('v2/auth/', obtain_jwt_token),
                       re_path('account/activate/%s/$' % settings.PASSWORD_TOKEN,
                            people_views.activate, name='user-activate'),
                       # django user registration
                       path('v2/rest-auth/', include('rest_auth.urls')),
                       path('v2/rest-auth/registration/', include('rest_auth.registration.urls')),
                       # vimeo
                       path('v2/assets/vimeo/upload/token',
                           assets_views.vimeo_get_upload_token, name='vimeo-upload-token'),

                       # api v1
                       path('', include(v1_api.urls)),
                       path('grappelli/', include('grappelli.urls')),
                       # url(r'^markdownx/', include('markdownx.urls')),
                       # path('v1/doc/',
                       #     include('tastypie_swagger.urls', namespace='ifresnoy_tastypie_swagger'),
                       #     kwargs={"tastypie_api_module": "ifresnoy.urls.v1_api",
                       #             "namespace": "ifresnoy_tastypie_swagger"}),
                       path('admin/', admin.site.urls),
             ] \
             + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT) \
             + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
