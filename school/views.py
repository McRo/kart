import datetime

from rest_framework import viewsets, permissions, filters, status
from rest_framework.response import Response

from drf_haystack.filters import HaystackAutocompleteFilter
from drf_haystack.viewsets import HaystackViewSet

from .permissions import IsOwnerOrAdmin

from people.models import Artist

from .models import Promotion, Student, StudentApplication, StudentApplicationSetup
from .serializers import (PromotionSerializer, StudentSerializer,
                          StudentAutocompleteSerializer, StudentApplicationSerializer
                          )

from .utils import (send_candidature_completed_email_to_user,
                    send_candidature_completed_email_to_admin,
                    send_candidature_complete_email_to_candidat
                    )


class PromotionViewSet(viewsets.ModelViewSet):
    queryset = Promotion.objects.all()
    serializer_class = PromotionSerializer
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)


class StudentViewSet(viewsets.ModelViewSet):
    queryset = Student.objects.all()
    serializer_class = StudentSerializer
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)


class StudentAutocompleteSearchViewSet(HaystackViewSet):
    index_models = [Student]
    serializer_class = StudentAutocompleteSerializer
    filter_backends = [HaystackAutocompleteFilter]
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)


class StudentApplicationViewSet(viewsets.ModelViewSet):
    queryset = StudentApplication.objects.all()
    serializer_class = StudentApplicationSerializer
    permission_classes = (permissions.IsAuthenticatedOrReadOnly, IsOwnerOrAdmin)
    filter_backends = (filters.SearchFilter, filters.DjangoFilterBackend, filters.OrderingFilter,)
    search_fields = ('artist__user__username',)
    filter_fields = ('application_completed',
                     'application_complete',
                     'selected_for_interview',
                     'physical_content',
                     'physical_content_received',
                     'selected',
                     'wait_listed',)
    ordering_fields = ('id',
                       'artist__user__last_name',
                       'artist__user__profile__nationality',)

    def create(self, request, *args, **kwargs):
        user = self.request.user
        # Chek if we can create application
        if self.candidature_hasexpired():
            errors = {'candidature': 'expired'}
            return Response(errors, status=status.HTTP_403_FORBIDDEN)
        # Check exist application fot this application session
        setup = StudentApplicationSetup.objects.filter(is_current_setup=True).first()
        user_application = StudentApplication.objects.filter(
            artist__user=user.id,
            promotion=setup.promotion
        ).first()

        if(not user_application):
            # take the artist
            user_artist = Artist.objects.filter(user=user.id).first()
            if not user_artist:
                # create it
                user_artist = Artist(user=user)
                user_artist.save()
            # create application
            user_application = StudentApplication(
                artist=user_artist,
                promotion=setup.promotion
            )
            user_application = user_application.save()
        # return app
        return user_application

    def list(self, request, *args, **kwargs):
        user = self.request.user

        if user.is_staff:
            queryset_application = StudentApplication.objects.all()
        else:
            queryset_application = StudentApplication.objects.filter(artist__user=user.id)

        serializer = StudentApplicationSerializer(queryset_application, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_202_ACCEPTED)
        # return super(self.__class__, self).list(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        user = self.request.user
        # candidate can't update candidature when she's expired, admin can !
        if self.candidature_hasexpired() and not user.is_staff:
            errors = {'candidature': 'expired'}
            return Response(errors, status=status.HTTP_403_FORBIDDEN)

        # send email when candidature to admin and USER (who click) is completed
        if(request.data.get('application_completed')):
            application = self.get_object()
            send_candidature_completed_email_to_user(request, user, application)
            send_candidature_completed_email_to_admin(request, user, application)

        # send email when to candidat when candidature is complete
        if(request.data.get('application_complete')):
            application = self.get_object()
            candidat = application.artist.user
            send_candidature_complete_email_to_candidat(request, candidat, application)
        # basic update
        return super(self.__class__, self).update(request, *args, **kwargs)

    def candidature_hasexpired(self):
        candidature_expiration_date = datetime.datetime.combine(
            StudentApplicationSetup.objects.filter(is_current_setup=True).first().candidature_date_end,
            datetime.datetime.min.time()
        )
        return candidature_expiration_date < datetime.datetime.now()

    def user_has_access(user):
        pass
