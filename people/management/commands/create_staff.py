# -*- encoding: utf-8 -*-
from django.core.management.base import BaseCommand
from django.template.defaultfilters import slugify
from school.models import StudentApplication
from django.utils.crypto import get_random_string

from django.contrib.auth.models import User
from people.models import Staff


class Command(BaseCommand):
    help = 'Create staff user like "Andy" "Wharhol" '

    def add_arguments(self, parser):
        parser.add_argument('firstname', type=str, help='Set fist name user')
        parser.add_argument('lastname', type=str, help='Set last name user')

    def handle(self, *args, **options):

        first_name = options['firstname']
        last_name = options['lastname']

        print first_name
        print last_name

        username = first_name.lower()[0]+slugify(last_name.lower())
        # try to get USER
        user = False
        created = False
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            user = User.objects.create_user(first_name=first_name,
                                            last_name=last_name,
                                            username=username,
                                            password=get_random_string())
            created = True
            print "User {0} created".format(user)


        if not created:
            print "User {0} already created".format(user)

        # try to create STAFF
        staff = False
        created = False
        try:
            staff = User.objects.get(username=username)
        except Staff.DoesNotExist:
            staff = Staff(user=user)
            staff.save()
            created = True

        if not created:
            print "Staff {0} created".format(staff)
        else:
            print "Staff {0} already created".format(staff)
