# -*- encoding: utf-8 -*-
from django.core.management.base import BaseCommand

from school.utils import candidature_close, send_candidature_not_finalized_to_candidats
from school.models import StudentApplication, StudentApplicationSetup


class Command(BaseCommand):
    help = 'Send emails to users who have not completed their application'

    def handle(self, *args, **options):
        # is the campaign open
        candidatures_open = not candidature_close()
        if not candidatures_open:
            print("Campaign is not open")
            return False

        # get the current campaign
        campaign = StudentApplicationSetup.objects.filter(is_current_setup=True).first()
        if not campaign:
            print("Campaign not found")
            return False

        all_applications = StudentApplication.objects.filter(campaign=campaign).count()
        # Candidat who havn't send application
        list_candidats = StudentApplication.objects.filter(campaign=campaign,
                                                           application_complete=False,
                                                           application_completed=False,
                                                           unselected=False,
                                                           selected=False,
                                                           ).values_list("artist__user__email")

        print(list_candidats)
        #
        str_question = "Vous allez envoyer un email à {} / {}? (y/n)".format(len(list_candidats), all_applications)
        confirm = input(str_question).lower().strip()

        if confirm != "y":
            print("Aucun email n'a été envoyé")
            return
        #
        mail_sent = send_candidature_not_finalized_to_candidats(self, campaign, list_candidats)
        if(mail_sent):
            print("Emails envoyés")
        else:
            print("Erreur email ")
