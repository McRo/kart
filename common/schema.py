from graphene_django import DjangoObjectType
from .models import Website
import graphene


class WebsiteType(DjangoObjectType):
    class Meta:
        model = Website


class Query(graphene.ObjectType):

    website = graphene.Field(WebsiteType, id=graphene.ID(required=True))
    websites = graphene.List(WebsiteType, url=graphene.String())

    def resolve_websites(self, info, url=None):
        qs = Website.objects.all()
        if url is not None:
            qs = qs.filter(url__icontains=url)
        return qs