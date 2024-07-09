
from django.contrib.postgres.search import TrigramSimilarity
import sys
import os
import re
import unidecode
import pathlib

# # Shell Plus Django Imports (uncomment to use script in standalone mode, recomment before flake8)
import django
# Add root to python path for standalone running
sys.path.append(str(pathlib.Path(__file__).parent.parent.absolute()))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "kart.settings")
django.setup()
# Load user model
from django.contrib.auth.models import User
from django.db.models.functions import Concat, Lower
from django.db.models import CharField, Value

# Import our models
from production.models import Artwork, Event
from people.models import Artist
from diffusion.models import Award, MetaAward, Place
from school.models import Student
import logging
import pytz
from utils.kart_tools import *


# Logging
logger = logging.getLogger('import_awards')
logger.setLevel(logging.DEBUG)
# clear the logs
open('awards.log', 'w').close()
# create file handler which logs even debug messages
fh = logging.FileHandler('awards.log')
fh.setLevel(logging.DEBUG)
# create console handler with a higher log level
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
# create formatter and add it to the handlers
formatter1 = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter1)
formatter2 = logging.Formatter('%(message)s')
ch.setFormatter(formatter2)
# add the handlers to the logger
logger.addHandler(fh)
logger.addHandler(ch)
#####

# Timezone
tz = pytz.timezone('Europe/Paris')

# Clear terminal
os.system('clear')

search_cache = {}


# Allow to lower data in query with '__lower'
CharField.register_lookup(Lower)

def getArtistByNames(firstname="", lastname="", pseudo="", listing=False):  # TODO pseudo
    """Retrieve the closest artist from the first and last names given

    Parameters:
    - firstname: (str) Firstname to look for
    - lastname : (str) Lastname to look for
    - pseudo   : (str) Pseudo to look for
    - listing  : (bool) If True, return a list of matching artists (Default, return the closest)

    Return:
    - artistObj    : (Django obj / bool) The closest artist object found in Kart. False if no match.
    - dist         : (float) Distance with the given names
    """

    # If no lastname no pseudo
    if not any([lastname, pseudo]):
        logger.info(
            f"\n** getArtistByNames **\nAt least a lastname or a pseudo is required.\nAborting research. {firstname}")
        return False

    # If data not string
    # print([x for x in [firstname,lastname,pseudo]])
    if not all([type(x) == str for x in [firstname, lastname, pseudo]]):
        logger.info(
            "\n** getArtistByNames **\nfirstname,lastname,pseudo must be strings")
        return False

    # List of artists that could match
    art_l = []

    # Clean names from accents to
    if lastname:
        # lastname_accent = lastname
        lastname = unidecode.unidecode(lastname).lower()
    if firstname:
        # firstname_accent = firstname
        firstname = unidecode.unidecode(firstname).lower()
    if pseudo:
        # pseudo_accent = pseudo
        pseudo = unidecode.unidecode(pseudo).lower()
    fullname = f"{firstname} {lastname}"

    # Cache
    fullkey = f'{firstname} {lastname} {pseudo}'
    try:
        # logger.warning("cache", search_cache[fullkey])
        return search_cache[fullkey] if listing else search_cache[fullkey][0]
    except Exception as e:
        pass

    # SEARCH WITH LASTNAME then FIRSTNAME
    # First filter by lastname similarity
    guessArtLN = Artist.objects.prefetch_related('user'
                                                 ).annotate(
        # Concat the full name "first last" to detect misclassifications like: "Hee Won -- Lee" where Hee Won is first
        # name but can be stored as "Hee  -- Won Lee"
        search_name=Concat('user__first_name__unaccent__lower',
                           Value(' '), 'user__last_name__unaccent__lower')
    ).annotate(
        similarity=TrigramSimilarity('search_name', fullname),
    ).filter(
        similarity__gt=0.3
    ).order_by('-similarity')

    # Refine results
    if guessArtLN:
        # TODO: Optimize by checking a same artist does not get tested several times
        for artist_kart in guessArtLN:

            # Clear accents (store a version with accents for further accents issue detection)
            kart_lastname_accent = artist_kart.user.last_name
            kart_lastname = unidecode.unidecode(kart_lastname_accent).lower()
            kart_firstname_accent = artist_kart.user.first_name
            kart_firstname = unidecode.unidecode(kart_firstname_accent).lower()
            # kart_fullname_accent = artist_kart.search_name
            kart_fullname = f"{kart_firstname} {kart_lastname}".lower()

            dist_full = dist2(kart_fullname, fullname)

            # logger.warning('match ',kart_fullname , dist2(kart_fullname,fullname), fullname,kart_fullname == fullname)
            # In case of perfect match ...
            if dist_full > .9:
                if kart_fullname == fullname:
                    # store the artist in potential matches with extreme probability (2)
                    # and continue with next candidate
                    art_l.append({"artist": artist_kart, 'dist': 2})
                    continue
                # Check if Kart and candidate names are exactly the same
                elif kart_lastname != lastname or kart_firstname != firstname:

                    logger.warning(f"""Fullnames globally match {fullname} but not in first and last name correspondences:
                    Kart       first: {kart_firstname} last: {kart_lastname}
                    candidate  first: {firstname} last: {lastname}
                                            """)
                    art_l.append({"artist": artist_kart, 'dist': dist_full*2})
                    # ### Control for accents TODO still necessary ?
                    #
                    # accent_diff = kart_lastname_accent != lastname_accent or \
                    #               kart_firstname_accent != firstname_accent
                    # if accent_diff: logger.warning(f"""\
                    #                 Accent or space problem ?
                    #                 Kart: {kart_firstname_accent} {kart_lastname_accent}
                    #                 Candidate: {firstname_accent} {lastname_accent} """)
                    continue

            # Control for blank spaces

            if kart_lastname.find(" ") >= 0 or lastname.find(" ") >= 0:
                # Check distance btw lastnames without spaces
                if dist2(kart_lastname.replace(" ", ""), lastname.replace(" ", "")) < .9:
                    bef = f"\"{kart_lastname}\" <> \"{lastname}\""
                    logger.warning(f"whitespace problem ? {bef}")

            if kart_firstname.find(" ") >= 0 or firstname.find(" ") >= 0:
                # Check distance btw firstnames without spaces
                if dist2(kart_firstname.replace(" ", ""), firstname.replace(" ", "")) < .9:
                    bef = f"\"{kart_firstname}\" <> \"{firstname}\""
                    logger.warning(f"whitespace problem ? {bef}")
            ###

            # Artists whose lastname is the candidate's with similar firstname

            # Distance btw the lastnames
            dist_lastname = dist2(kart_lastname, lastname)

            # try to find by similarity with firstname
            guessArtFN = Artist.objects.prefetch_related('user').annotate(
                similarity=TrigramSimilarity('user__first_name__unaccent', firstname),
            ).filter(user__last_name=lastname, similarity__gt=0.8).order_by('-similarity')

            # if artist whose lastname is the candidate's with similar firstname names are found
            if guessArtFN:

                # Check artists with same lastname than candidate and approaching firstname
                for artistfn_kart in guessArtFN:
                    kart_firstname = unidecode.unidecode(artistfn_kart.user.first_name)
                    # Dist btw candidate firstname and a similar found in Kart
                    dist_firstname = dist2(f"{kart_firstname}", f"{firstname}")
                    # Add the candidate in potential matches add sum the distances last and firstname
                    art_l.append({"artist": artistfn_kart, 'dist': dist_firstname+dist_lastname})

                    # Distance evaluation with both first and last name at the same time
                    dist_name = dist2(f"{kart_firstname} {kart_lastname}",
                                      f"{firstname} {lastname}")
                    # Add the candidate in potential matches add double the name_dist (to score on 2)
                    art_l.append({"artist": artistfn_kart, 'dist': dist_name*2})

            else:
                # If no close firstname found, store with the sole dist_lastname (unlikely candidate)
                art_l.append({"artist": artist_kart, 'dist': dist_lastname})

        # Take the highest distance score
        art_l.sort(key=lambda i: i['dist'], reverse=True)

        # Return all results if listing is true, return the max otherwise
        if listing:
            search_cache[fullkey] = art_l
            return art_l
        else:
            search_cache[fullkey] = [art_l[0]]
            return art_l[0]
    else:
        # research failed
        search_cache[fullkey] = False

        return False
    #####

# print(getArtistByNames('Marin', 'Martini'))
