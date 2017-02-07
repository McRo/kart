import os
from django.contrib.auth.models import User
from ifresnoy import settings


def make_filepath(instance, filename):
    """
    Generate a unique filename for any upload (fix problems with
    accents and such).
    """

    carry_on = True
    while carry_on:
        new_filename = "{0}.{1}".format(User.objects.make_random_password(48),
                                        filename.split('.')[-1])
        path = "{0}/{1}/{2}".format(
            instance.__class__._meta.app_label,
            instance.__class__.__name__.lower(),
            new_filename
        )
        carry_on = os.path.isfile(os.path.join(settings.MEDIA_ROOT, path))

    return path
