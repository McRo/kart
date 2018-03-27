from django.db import models

from people.models import Organization


class Place(models.Model):
    """
    Some place belonging to an organization
    """
    name = models.CharField(max_length=255)
    description = models.TextField()

    organization = models.ForeignKey(Organization, related_name='places', on_delete=models.PROTECT)

    def __unicode__(self):
        return '{0} ({1})'.format(self.name, self.organization)


class Award(models.Model):
    """
    Awards given to artworks & such.
    """
    pass
    # event
    # artwork
    # -> award (textfield)
