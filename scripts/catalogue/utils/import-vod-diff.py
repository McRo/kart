#! /usr/bin/env python
# -*- coding=utf8 -*-

"""
Import VOD data (csv) to KART


Admitted rules
--------------
-
"""


import os
import sys
import re
import time

from difflib import SequenceMatcher
import pathlib
import logging
import pandas as pd
import pytz
from datetime import datetime
import json

from django.db.utils import IntegrityError
from django_countries import countries
from django.db.models.functions import Concat, Lower
from django.db.models import CharField, Value
from django.contrib.postgres.search import TrigramSimilarity
from django.core.exceptions import MultipleObjectsReturned, ObjectDoesNotExist

import yaml

from correction import Correction

import unidecode

# Shell Plus Django Imports (uncomment to use script in standalone mode, recomment before flake8)
import django
from django.conf import settings
# settings.configure(DEBUG=True)
# Add root to python path for standalone running
sys.path.append(str(pathlib.Path(__file__).parent.parent.absolute()))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "kart.settings")
django.setup()
################## end shell plus

from production.models import Artwork, Event, Film, Installation
from people.models import Artist
from diffusion.models import Award, MetaAward, Place
from school.models import Student, Promotion
from django.contrib.auth.models import User
from assets.models import Gallery, Medium

# Full width print of dataframe
pd.set_option('display.expand_frame_repr', False)


# TODO: Harmonise created and read files (merge.csv, ...)
dry_run = False  # No save() if True
DEBUG = True

# Set file location as current working directory
OLD_CWD = os.getcwd()
os.chdir(pathlib.Path(__file__).parent.absolute())


# Allow to lower data in query with '__lower'
CharField.register_lookup(Lower)

# Logging
logger = logging.getLogger('import_pano_data')
logger.setLevel(logging.DEBUG)
# clear the logs
open('import_csv.log', 'w').close()
# create file handler which logs even debug messages
fh = logging.FileHandler('import_csv.log')
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

# Load the Yaml config file
with open("import.yaml", 'r') as stream:
    try:
        conf=yaml.safe_load(stream)
        print(conf['exclude_columns'])
    except yaml.YAMLError as exc:
        print(exc)


##################################################
# Mappings btw csv fields and Kart's fields #
##################################################

csvkart_mapping = {
    'user' : {
        'email':'',
        'last_name':'Nom',
        'first_name':'Prénom',
    },

    'artist' : {
        'nickname':'Pseudo',
        'bio_fr':'',
        'bio_en':'',
    },

    'student' : {
        'promotion':'promotion',
    },

    'artwork' : {
        'type':'',
        'production_date':'Année',
        'title':'Titre',
        'subtitle':'',
        'duration':'(Durée) HH:MM:SS',
        'description_fr':'',
        'description_en':'',
        'thanks_fr':'',
        'partners_txt':'',
    }

}
# def testAwardsProcess():
#     """Stats stuff about the awards
#
#     Dummy code to get familiar with Kart"""
#     # ========= Stacked data: awards by events type ... ==============
#     import matplotlib.colors as mcolors
#     mcol = mcolors.CSS4_COLORS
#     mcol = list(mcol.values())
#     # mixing the colors with suficent gap to avoid too close colors
#     colss = [mcol[x+12] for x in range(len(mcol)-12) if x % 5 == 0]
#     # by type of event
#     awards.groupby(['event_year', 'event_type']).size(
#     ).unstack().plot(kind='bar', stacked=True, color=colss)
#     plt.show()
#
#
# def testArtworks():
#     """Get authors with artwork id
#
#     Dummy code to get familiar with Kart"""
#     # Get the data from csv
#     awards = pd.read_csv('awards.csv')
#     # Strip all data
#     awards = awards.applymap(lambda x: x.strip() if isinstance(x, str) else x)
#
#     # replace NA/Nan by 0
#     awards.artwork_id.fillna(0, inplace=True)
#
#     # Convert ids to int
#     awards.artwork_id = awards['artwork_id'].astype(int)
#
#     for id in awards.artwork_id:
#         # id must exist (!=0)@
#         if not id:
#             continue
#         prod = Production.objects.get(pk=id)
#         logger.info(prod.artwork.authors)


def dist2(item1, item2):
    """Return the distance between the 2 strings"""
    # print(f"dist2 {item1} versus {item2}")
    if not type(item1) == type(item2) == str:
        raise TypeError("Parameters should be str.")
    return round(SequenceMatcher(None, item1.lower(), item2.lower()).ratio(), 2)


def run_import() :
    """ Main function to call to trigger the import process """

    # Clean the csv from udesired data (TODO : csv path as argument)
    clean_csv("./Kart-TEASER_VOD.csv")







search_cache = {}

def getArtistByNames(firstname="", lastname="", pseudo="", listing=False): # TODO pseudo
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
    resp = getUserByNames(firstname, lastname, listing=listing)

    if resp and "user" in resp.keys() :
        arts = Artist.objects.filter(user__pk=resp['user'].id)
        if len(arts) > 1 :
            print("several artist")
            print("\n".join([f"{art},artist id : {art.id}, user id : {art.user.id}\n" for art in arts]))
        if arts and not listing :
            return arts[0]
        elif arts and not listing :
            return arts
    return False



def infoCSVeventTitles():
    """Display info about potentialy existing events in Kart

    Check if event names exist with a different case in Kart and display warning
    """
    eventsToCreate = pd.read_csv('./tmp/events_title.csv')

    for evt_title in eventsToCreate.NomFichier:
        # If a title already exist with different case
        exact = Event.objects.filter(title__iexact=evt_title)
        if exact:
            logger.warning(
                f"Event already exist with same name (but not same case) for {evt_title}:\n{exact}\n")

        # If a title already contains with different case
        contains = Event.objects.filter(title__icontains=evt_title)
        if contains:
            logger.warning(
                f"Event already exist with very approaching name (but not same case) for {evt_title}:\n{contains}\n")


def createEvents():
    """ Create (in Kart) the events listed in awards csv file

    1) Retrieve the data about the events listed in awards csv file
    2) Parse those data and prepare if for Event creation
    3) (optional) Check if meta event exits for the created event, creates it if needed
    """

    # Get the events from awards csv extended with title cleaning (merge.csv)
    events = pd.read_csv('./tmp/merge.csv')

    # Create/get the events in Kart
    for ind, event in events.iterrows():
        title = event.NomDefinitif
        # Starting dates are used only for the year info (default 01.01.XXX)
        starting_date = event.event_year
        # Convert the year to date
        starting_date = datetime.strptime(str(starting_date), '%Y')
        starting_date = pytz.timezone('Europe/Paris').localize(starting_date)

        # All events are associated with type festival
        # TODO: Add other choices to event ? Delete choices constraint ?
        type = "FEST"

        # If no title is defined, skip the event
        if str(title) in ["nan", ""]:
            continue

        # Check if meta event exists, if not, creates it
        evt = Event.objects.filter(
            title=title,
            type=type,
            main_event=True
        )
        # If event already exist
        if len(evt):
            # Arbitrarily use the first event of the queryset (may contain more than 1)
            # TODO: what if more than one ?
            evt = evt[0]
            created = False
        else:
            # Create the main event
            evt = Event(
                title=title,
                # default date to 1st jan 70, should be replaced by the oldest edition
                starting_date=datetime.strptime("01-01-70", "%d-%m-%y").date(),
                type=type,
                main_event=True
            )
            if not dry_run:
                evt.save()
            created = True

        if created:
            logger.info(f"META {title} was created")
        else:
            logger.info(f"META {title} was already in Kart")

        # Check if event exists, if not, creates it
        evt = Event.objects.filter(
            title=title,
            type=type,
            # just use the starting date for now
            # TODO: events with more details
            starting_date=starting_date
        )

        if len(evt):
            # Arbitrarily use the first event of the queryset
            evt = evt[0]
            created = False
        else:
            logger.info("obj is getting created")
            evt = Event(
                title=title,
                type=type,
                starting_date=starting_date
            )
            if not dry_run:
                evt.save()
            created = True

        if created:
            logger.info(f"{title} was created")
        else:
            logger.info(f"{title} was already in Kart")
        # Store the ids of newly created/already existing events in a csv
        events.loc[ind, 'event_id'] = evt.id
    events.to_csv('./tmp/events.csv', index=False)


def getISOname(countryName=None, simili=False):
    """Return the ISO3166 international value of `countryName`

    Parameters:
    - countryName  : (str) The name of a country
    - simili         : (bool) If True (default:False), use similarity to compare the names
    """
    # Process the US case (happens often!)
    if re.search('[EeéÉ]tats[ ]?-?[ ]?[Uu]nis', countryName):
        return "US"
    # Kosovo is not liste in django countries (2020)
    if re.search('kosovo', countryName, re.IGNORECASE):
        return 'XK'

    # General case
    if not simili:
        for code, name in list(countries):
            if name == countryName:
                return code
        return False
    else:
        # The dic holding the matches
        matchCodes = []
        for code, name in list(countries):
            dist = SequenceMatcher(None, str(countryName).lower(), name.lower()).ratio()
            # logger.info(f"DIST between {countryName} (unknown) and {name}: {dist}")
            if dist >= .95:
                matchCodes.append({'dist': dist, 'code': code})  # 1 ponctuation diff leads to .88
            if dist >= .85:
                cn1 = unidecode.unidecode(str(countryName))
                cn2 = unidecode.unidecode(name)
                dist2 = SequenceMatcher(None, cn1.lower(), cn2.lower()).ratio()
                if dist2 > dist:
                    logger.info(
                        f"""------------------- ACCENTUATION DIFF {countryName} vs {name}\n
                        Accents removed: {cn1} vs {cn2}: {dist2}""")
                    # 1 ponctuation diff leads to .88
                    matchCodes.append({'dist': dist2, 'code': code})
                else:
                    if DEBUG:
                        return code
                    cont = input(f"""
                                 NOT FOUND but {countryName} has a close match with {name}
                                 Should I keep it ? (Y/n):   """)
                    if re.search("NO?", cont, re.IGNORECASE):
                        continue
                    else:
                        return code

    # Sort the matches by similarity
    sorted(matchCodes, key=lambda i: i['dist'])
    try:
        # Return the code with the highest score
        return matchCodes[0]['code']
    except IndexError:
        return False



# TODO: Fill artwork in the event


def associateEventsPlaces():
    """Fill the place field of created events with the created places

    """

    # Get the events and places csv
    evt_places = pd.read_csv("./tmp/merge_events_places.csv")

    # Update the events with the place
    for ind, award in evt_places.iterrows():
        event_id = int(award.event_id)
        if str(award.place_id) != "nan":
            try:  # some events have no places specified
                place_id = int(award.place_id)
                evt = Event.objects.get(pk=event_id)
                evt.place_id = place_id
                if not dry_run:
                    evt.save()
                logger.info(evt)
            except ValueError as ve:
                logger.info("ve", ve, "award.place_id", award.place_id)


def safeGet(obj_class=None, default_index=None, force=False, **args):
    """Try to `get`the object in Kart. If models.MultipleObjectsReturned error, return the first oject returned
        or the one in index `default_index`

    Parameters:
    - objClass     : (Django obj) The class on which to apply the get function
    - default      : (int) The index of the queryset to return in case of MultipleObjectsReturned error.
                      '0' is used in case of IndexError
    - args         : the arguments of the get query
    - force        : (bool) Force the return of the whole queryset rather than just one object - Default: False

    Return:
    - obj          : (Django obj or bool) a unique object of `obj_class`matching the **args,
                       False if `ObjectDoesNotExist` is raised
    - filtered     : a boolean indicating if the returned obj was unique or from a >1 queryset
    """

    try:
        obj = obj_class.objects.get(**args)
        return obj, False

    # If the object does not exist, return False
    except ObjectDoesNotExist:
        return False, False

    # If multiple entries for the query, fallback on filter
    except MultipleObjectsReturned:
        objs = obj_class.objects.filter(**args)
        logger.info(f"The request of {args}  returned multiple entries for the class {obj_class}")

        if default_index:
            try:
                return objs[default_index], True
            except ValueError:
                return objs[0], True
        else:
            # Return the first object of the queryset
            return objs[0], True


def objExistPlus(obj_class=None, default_index=None, **args):
    """Return a True if one or more objects with `**args` parameters exist

    Parameters:
    - objClass     : (DjangoObject) The class on which to apply the get function
    - default      : (int) The index of the queryset to return in case of MultipleObjectsReturned error.
                      '0' is used in case of IndexError
    - args         : the arguments of the get query

    Return:
    - exists       : (bool)
    - multiple     : (int) the amount of existing object
    """

    objs, filtered = safeGet(obj_class, force=True, **args)
    if objs:
        return True, len(objs)
    else:
        return False,


def objExist(obj_class=None, default_index=None, **args):
    """Return a True if one or more objects with `**args` parameters exist

    Parameters:
    - objClass     : (DjangoObject) The class on which to apply the get function
    - default      : (int) The index of the queryset to return in case of MultipleObjectsReturned error.
                      '0' is used in case of IndexError
    - args         : the arguments of the get query

    Return:
    - exists       : (bool)
    """

    objs, filtered = safeGet(obj_class, force=True, **args)
    if objs:
        return True
    else:
        return False


def createAwards():
    """Create the awards listed in csv in Kart

    """
    print("**********************************\n***** Create AWARDS   ********\u*********************")
    # Load the events associated to places and artworks (generated by createPlaces())
    awards = pd.read_csv("./tmp/merge_events_places.csv")

    # Load the artists and associated artworks (generated by artworkCleaning())
    authors = pd.read_csv("./tmp/artworks_artists.csv")

    # Merge all the data in a dataframe
    total_df = pd.merge(awards, authors, how='left')
    total_df["notes"] = ""
    total_df.fillna('', inplace=True)
    cpt = 0

    # Check if artist are ok (not fully controled before ...)
    # if no artist_id, search by name in db
    for id, row in total_df[total_df['artist_id'] == ''].iterrows():
        art = getArtistByNames(firstname=row['artist_firstname'], lastname=row['artist_lastname'], listing=False)
        # if there is a match
        # dist == 2 is the maximum score for artist matching
        if art and art['dist'] == 2:
            # the id is stored in df
            total_df.loc[id, "artist_id"] = art['artist'].id

    for ind, award in total_df.iterrows():
        # init
        artwork_id = artist = False

        label = award.meta_award_label
        event_id = int(award.event_id)

        # An artwork id is required to create the award
        if (award.artwork_id):
            artwork_id = int(award.artwork_id)
        else:
            logger.warning(f"No idartwork for {award.artwork_title}")
            continue

        if (award.artist_id):
            artist = Artist.objects.get(pk=int(award.artist_id))
        else:
            cpt += 1
            print("NO ID ARTIST ", label, event_id)

        # try:
        #     print("award.artist_id",int(award.artist_id))
        # except ValueError:
        #     print("------------------>", award.artist_id)
        note = award.meta_award_label_details

        description = award.meta_award_label_details
        if pd.isna(award.meta_award_label_details):
            description = ''

        # GET THE META-eventsToCreate
        # Retrieve the Kart title of the event
        event, filt = safeGet(Event, pk=event_id)
        mevent, filt = safeGet(Event, title=event.title, main_event=True)

        # GET OR CREATE THE META-AWARD
        # Check if award exists in Kart, otherwise creates it
        maward, filt = safeGet(MetaAward, label=f"{label}", event=mevent.id)

        if maward:
            logger.info(f"MetaAward {label} exist in Kart")
        else:
            maward = MetaAward(
                label=f"{label}",
                event=mevent,
                description=description,
                type="INDIVIDUAL"  # indivudal by default, no related info in csv
            )
            print(f"label {maward.label}, event {mevent}, description {description}")
            if not dry_run:
                maward.save()
            logger.info(f"\"{maward}\" created ")

        # GET OR CREATE THE AWARDS
        new_aw, filt = safeGet(Award,
                               meta_award=maward.id,
                               artwork=artwork_id,
                               event=event.id,
                               # artists = artist_id
                               )
        logger.setLevel(logging.WARNING)
        if new_aw:
            logger.info(f"{new_aw} exist in Kart")
            try:
                new_aw.artist.add(artist.id)
            except IntegrityError:
                # logger.warning(f"Artist_id: {artist} caused an IntegrityError")
                pass
            except AttributeError:
                # logger.warning(f"Artist_id: {artist} caused an AttributeError")
                pass
            if not dry_run:
                new_aw.save()
        else:
            new_aw = Award(
                meta_award=maward,
                event=event,
                date=event.starting_date,
                note=note
            )
            try:
                if not dry_run:
                    new_aw.save()
                    new_aw.artwork.add(artwork_id)
                    new_aw.save()
                    print(f"{new_aw}  created")
            except ValueError:
                # logger.warning(f"Artist_id: {artist} caused an IntegrityError")
                pass
        # print("CPT", cpt)

# Fonctions à lancer dans l'ordre chronologique
# WARNING: eventCleaning and artworkCleaning should not be used !! (Natalia, head of diffusion, already
# validated diffusion/utils/import_awards/events_title.csv and diffusion/utils/import_awards/artworks_artists.csv)

# WARNING: this function requires a human validation and overrides `events_title.csv` & `merge.csv`
# eventCleaning()
# WARNING: this function requires a human validation and overrides `artworks_title.csv` & `merge.csv`
# artworkCleaning()

# logger.setLevel(logging.CRITICAL)
# dry_run = True
# #
# # # createEvents()
# # # createPlaces()
# # # associateEventsPlaces()
# createAwards()
# #
#
# art = getArtistByNames(firstname="Daphné", lastname="Hérétakis", pseudo=None, listing=False)
# print('\n')
# print(art['artist'].id)



#   _____ _      ______          _   _
#  / ____| |    |  ____|   /\   | \ | |
# | |    | |    | |__     /  \  |  \| |
# | |    | |    |  __|   / /\ \ | . ` |
# | |____| |____| |____ / ____ \| |\  |
#  \_____|______|______/_/    \_\_| \_|
#
# TODO Database cleanings :
# - strip : remove leading / trailing spaces in string fields

def get_names_from_name(name) :
    """ Extract and return first and lastname from webform string """

    # Extract the uppercase string to get the lastname (TODO : should separate columns in webform)
    # List from string with space separator
    nn = [unkown for unkown in name.split(' ')]

    # Init lists
    firstname = list()
    lastname = list()

    # Set lastname when string is fully uppercased, firstname otherwise
    # strip strings as leading space may occur
    for unknown in nn :
        is_all_uppercase = [letter.isupper() for letter in unknown if letter.isalpha()]
        if all(is_all_uppercase) :
            lastname += [unknown]
        else :
            firstname += [unknown]

    # Convert lists to strings
    firstname = (" ".join(firstname)).strip()
    lastname = (" ".join(lastname)).strip()
    return firstname, lastname


import re, html
def clean_tags(html_code="") :
    """ Remove html tags from html_code and return the subsequent text"""

    if 'nan' == str(html_code) : return None

    tag_re = re.compile(r'(<!--.*?-->|<[^>]*>)')

    # Remove well-formed tags, fixing mistakes by legitimate users
    no_tags = tag_re.sub('', html_code)

    # Clean up anything else by escaping
    ready_for_web = html.escape(no_tags)

    return ready_for_web

def create_or_update(obj_type=None, properties=None, save=False) :
    """ Return an object of type obj_type populated with properties.
        If the object already exists, update it with, if not create it.

        Parameters :
        - obj_type          :    (str) type of kart obj to create
        - properties        :    (str) associated properties
        - save  (optional)  :    (str) If true, save the object in db - default : False
    """

    # -*- coding: utf-8 -*-
    try :
        obj = eval(f'{obj_type}({properties})')
        print("obj ", obj)
    except Exception as e :
        print("e" ,e)


def shouldCorrect() :
    """ Indicate when a correction is needed whether in kart data or csv data"""
    pass



def usernamize(fn="", ln="", check_duplicate=False) :
    """ Return a username from first and lastname.

    params:
    fn              : (str) Firstname
    ln              : (str) Lastname
    check_duplicate : (boo) If true, verify if username do not already exist in db, increment suffix if needed (default=False).

    e.g. :
    fn = "Andy"
    ln = "Wharol"
    computed username : "awarhol"
    if awarhol already taken, compute "awarhol2", if "awarhol2" exists, compute "awarhol3" and so on ...
    """

    # Check if multipart firstname
    fn_l = re.split('\W+',fn)

    # Extract first letter of each fn part
    fn_l = [part[0].lower() for part in fn_l if part.isalpha()]

    # Lower lastname and remove non alpha chars
    ln_l = [letter.lower() for letter in ln if letter.isalnum()]

    # Concat strings
    username = "".join(fn_l) + "".join(ln_l)

    # Remove any special characters
    username = unidecode.unidecode(username)

    # Trim at 10 characters
    username = username[:10]

    if check_duplicate :
        # Check if username is already taken, add 2, 3, 4 ... until its unique
        # Init suffix
        i = 2
        while objExist(User,default_index=None,username=username) :
            username = usernamize(firstname, lastname) + f"{i}"
            i+=1

    return username


def clean_csv(csv_path, dest='./') :
    """ Clean the csv from undesired data and store a cleaned csv with validated data from Kart when data already exists in Kart.

    :param csv_path: str, path to the csv file
    :param dest: str, path to the destination csv file, optional


    """

    # Log the function call
    logger.info(f"FUNCTION : clean_csv - START")

    # Load the csv to dataframe
    csv_df = pd.read_csv(csv_path, skiprows=2, encoding='utf8')

    # Get rid of empty cols
    csv_df.drop(csv_df.columns[conf['exclude_columns']], axis=1,inplace=True)

    # Convert cols names to Kart when possible, strip anyway
    csv_df.columns = [csv2kart(col.strip()) for col in csv_df.columns]


    # Data filtering and extraction from the csv
    for index, row in csv_df.iterrows() :

        # Clean the nan's
        for k,v in row.items():
            if 'nan' == str(v)  :
                # logger.info(f'found nan ! : {k} {row[k]} - {v}')
                row[k] = None

        # Parsing of the title  e.g. Le vieil enfant film de Felipe Esparza - 2020 (id: 1297)
        title = row.title

        # Extract id artw
        pat = re.compile('\(id: (\d+)\)')
        match = re.search(pat, title)

        if match :
            id = match[1]
            # print("ID artw extracted", id)
            aw = Artwork.objects.get(pk=id)
            # print("aw ", aw)
        # if id can't be extracted, use diffusion title
        else :
            logger.warning(f"Can't extract id from {title}")
            # print('>>>',row['Titre diffusion'])
            # print('>>>',row['Remarques'])

            # Try to get the artw by title
            bytitle = getArtworkByTitle(row['Titre diffusion'])
            if bytitle :
                logger.warning(f"################# by title ,{title}, {bytitle}")
            print('\n\n')
        continue

        # Get artist from KART
        #arts = getArtistByNames(firstname=row['first_name'], lastname=row['last_name'])

        # Associated artworks in Kart
        # artws = Artwork.objects.filter(authors = arts)
        # print("artws",artws)


        #############################################################################################
        continue
        exit()
        #############################################################################################
        # Init user
        user = None

        # First, try to retrieve the user from Kart from first and last names
        firstname, lastname = get_names_from_name(row["nom_prenom"])

        # Fill new firstname and lastname columns in csv
        clean_df.loc[index,'firstname'] = firstname
        clean_df.loc[index,'lastname'] = lastname

        # User obj to created / updated
        user_dict = dict (
                    username    =   "",
                    first_name  =   firstname,
                    last_name   =   lastname,
                    email       =   row[kart2webf('user','email')],
                    password    =   ""
                )

        # Prepare the creation of an artist object
        artist_dict = dict (
                    nickname    =   row[kart2webf('artist', 'nickname')],
                    bio_fr      =   row[kart2webf('artist', 'bio_fr')],
                    bio_en      =   row[kart2webf('artist', 'bio_en')],
                    )

        # Prepare the creation of a student object
        promo_name = row[kart2webf('student', 'promotion')]
        promotion  = getPromoByName(promo_name)
        student_dict = dict (
                    promotion  = promotion
                    )

        # Prepare the creation of an artwork object
        artwork_dict =  dict (
                title            =   row[kart2webf('artwork', 'title')],
                subtitle         =   row[kart2webf('artwork', 'subtitle')],
                description_fr   =   row[kart2webf('artwork', 'description_fr')],
                description_en   =   row[kart2webf('artwork', 'description_en')],
                thanks_fr        =   row[kart2webf('artwork', 'thanks_fr')],
        )

        ##########
        #  USER  #
        ##########

        logger.info(f"User recherché : prénom > {firstname}, nom > {lastname}")

        # Try to retrieve the artist from Kart from first and last names
        userSearch = getUserByNames(lastname=lastname, firstname=firstname, dist_min=1.8)

        # If csv user match in Kart (dist = similarity btw csv last and firstnames and Kart's)
        if userSearch :

            # Get the user object from search
            user = userSearch['user']

            logger.info(f"User found {userSearch}")

            # Add user to existing users list
            existing_users += [user]

            # Set user_found col in csv
            clean_df.loc[index,'user_found'] = True
            clean_df.loc[index,'user_id'] = user.id
        else :
            # if no user match in Kart, create it
            clean_df.loc[index,'user_found'] = False
            clean_df.loc[index,'artist_found'] = False
            clean_df.loc[index,'student_found'] = False
            logger.info("Not found in Kart, add to create list.")
            # Add the index of the row to the list of users to create
            missing_users += [user]

            # Username from first and last names
            username = usernamize(firstname, lastname, check_duplicate=True)

            # Assign username
            user_dict['username'] = username

            user = User(**user_dict)

            # Save user
            if not dry_run :
                user.save()


        ###########
        # ARTISTS #
        ###########

        # Init
        artist = None

        ########################################
        # TODO : script de recherche de doublons
        # Search by similarity with nickname
        # nickname = row[kart2webf('artist', 'nickname')]
        #
        # # Get the artist by closest nickname
        # guessArtistNN = Artist.objects.annotate(
        #     similarity=TrigramSimilarity('nickname__unaccent', nickname),
        # ).filter(nickname=nickname, similarity__gt=0.8).order_by('-similarity')
        #
        # # List potential duplicated artist (same nickname, diff user)
        # potential_duplicates = list()
        #
        # # If artists with close nickname is found
        # if guessArtistNN :
        #     logger.info(f"guess nickname {row[kart2webf('artist', 'nickname')]} <--> {guessArtistNN[0].user.id} --------------- {user.id}")
        #     # For each artist found with similar nicknames, check the associated user.id
        #     for match in guessArtistNN :
        #         potential_duplicates += [{'id_artist':match.id, 'id_user':user.id}]
        #     # If more than 1 artist have the same nickname ...
        #     if len(potential_duplicates)>1 :
        #         # ... that means that 2 or more artists share the same nickname
        #         logger.info(f"Houston we've got a problem {potential_duplicates}")
        #         for dupli in potential_duplicates :
        #             for dupli2 in potential_duplicates :
        #                 if dupli['id_user'] == dupli2['id_user'] :
        #                     logger.info(f" !! 1 user ({dupli['id_user']}) is 2 artists ({dupli2['id_artist']}) with same nickname ({nickname}) at the same time !!")
        ##########################################

        # Check if artist object is associated with user
        try :
            # Get the artist with matching user id
            artist = Artist.objects.get(user__pk=user.id)

            logger.info(f"Associated artist found {artist}")

            # Add artist to existing artists list
            existing_artists += [artist]

            # Check artist_found in csv
            clean_df.loc[index,'artist_found'] = True

            # Fill artist_id in df
            clean_df.loc[index,'artist_id'] = artist.id

        except :  # If no associated artist found,
            # Provide user.id to artist dict
            artist_dict['user_id'] = user.id

            # Create an artist from dict
            artist = Artist(**artist_dict)

            # Check artist_found in csv
            clean_df.loc[index,'artist_found'] = False

            #  Add artist to missing artists
            missing_artists += [artist]

        # Save artist
        if not dry_run :
            artist.save()

        ############
        # STUDENTS #
        ############

        # Init
        student = None
        print("promotion", promotion)
        print("user__pk=user.id", user.id, artist.id)
        if promotion :  # Create a student only when promotion is defined (otherwise invited )
            # Check if student object is associated with user
            try :
                # Get the student with matching user and artist ids
                student = Student.objects.get(user__pk=user.id, artist__pk=artist.id)

                logger.info(f"Associated student found {artist}")

                # Add student to existing students list
                existing_students += [student]

                # Check student_found in csv
                clean_df.loc[index,'student_found'] = True
                clean_df.loc[index,'student_id'] = student.id

            except :  # If no associated student found

                # Fill student_dict
                student_dict['user']    =   user
                student_dict['artist']  =   artist

                # Create an student from dict
                student = Student(**student_dict)

                # Check student_found in csv
                clean_df.loc[index,'student_found'] = False

                #  Add student to missing students
                missing_students += [student]

                # Save student
                if not dry_run :
                    student.save()
            print("student.id", student.id)

        ############
        # ARTWORKS #
        ############

        # init artwork
        artwork = None


        # Check if aw not already in Kart (should not !)
        # Try to retrieve artworks from Kart with user in authors

        # Get the artworks associated to the current user
        aw_kart = Artwork.objects.filter(authors=artist)

        if aw_kart :
            # If an aw is found, we compare with the csv title
            for aw in aw_kart :
                aw_csv = row[kart2webf('artwork','title')]

                logger.info(f" simi {aw.title}, aw_csv : {aw_csv}" )

                if dist2(aw.title, aw_csv ) >.8 :
                    logger.info(f"\tAssociated artworks in Kart : {aw.title}")
                    logger.info(f"\t                     in csv : {row[kart2webf('artwork','title')]}")
                    logger.info(f"----> {dist2(aw.title, row[kart2webf('artwork','title')])}")
                    artwork = aw
                    # Check artwork_found in csv
                    clean_df.loc[index,'artwork_found'] = True
                    clean_df.loc[index,'artwork_id'] = artwork.id
                    break

        if not artwork :
            logger.info("No related artwork in Kart")

            # Timetag the aw as today
            now = datetime.now()
            artwork_dict['production_date'] = now

            # Romano : " je mets le 01/01/2021"

            # Get the type from csv
            aw_type = row['type']

            if "installation" == aw_type.lower() or "performance" == aw_type.lower() :
                    print("installation")
                    artwork = Installation (**artwork_dict)

            if "film" == aw_type.lower() :

                    duration = str(row[kart2webf('artwork', 'duration')])

                    if 'nan' == duration : duration = None
                    artwork_dict['duration'] = duration
                    artwork = Film (**artwork_dict)




            # Save artwork
            if not dry_run :
                artwork.save()

            # Add author to the artwork
            artwork.authors.add(artist)

            # Save artwork
            if not dry_run :
                artwork.save()

        print("duration", row[kart2webf('artwork', 'duration')])

        # Dream theme -> external json file
        dream_l += [{artwork.id :row['dream_theme']}]

        # Remove potential html tags
        partners_txt = clean_tags(row[kart2webf('artwork', 'partners_txt')])
        partners_l += [{artwork.id : partners_txt}]



    exit()



    # # Check if artist object exists from existing users
    # print("Checking existing artists in existing users...")
    # for user in existing_users :
    #     artist = Artist.objects.get(user__pk=user.id)
    #
    # # Check if artist object exists from users to create (should not !)
    # print("Checking existing artists in missing users...")
    # for user in missing_users :
    #     try :
    #         artist = Artist.objects.get(user__pk=user.id)
    #     except :
    #         print("Not an artist : ",user)
    #         pass

        # Explore the first artist (révisions :) !)
        # artist = existing_users[0]

        ############
        # STUDENTS #
        ############
        # promotion   =   getPromoByName(row[kart2webf('student','promotion')]),
            # try :
            #     student = Student.objects.get(pk=artist.student.id)
            #     print('student', student)
            # except :
            #     print("Not a student : ",user)
            #     pass
    # print(csv_df)
    # cols containing "_id"
    cols = [col for col in csv_df.columns if '_id' in col]
    clean_df[cols] = csv_df[cols].fillna(0)
    clean_df[cols] = csv_df[cols].astype(int)
    clean_df.to_csv('clean.csv',index=False)
    exit()




    # Artwork process
    # Check if artwork already exists
    # for title in csv["titre"] :
    #     print('title', title)
    #     aw = getArtworkByTitle(title)
    #     if title is None : print(aw,"\n")



    # print(artist.user)
    # print(artist.student.__dict__)

    # PROMO
    # {'_state': <django.db.models.base.ModelState object at 0x1233b6050>, 'id': 25, 'name': 'Jonas Mekas', 'starting_year': 2019, 'ending_year': 2021}


    # STUDENT
    # {'_state': <django.db.models.base.ModelState object at 0x11b953e90>, 'id': 535, 'number': '2019-209', 'promotion_id': 25, 'graduate': False, 'user_id': 1513, 'artist_id': 1493}


    # ARTIST
    # {'_state': , 'id': 1493, 'user_id': 1513, 'nickname': '', 'bio_short_fr': '', 'bio_short_en': '', 'bio_fr': '', 'bio_en': '', 'updated_on': , 'twitter_account': '', 'facebook_profile': '', 'search_name': 'Inès Sieulle', 'similarity': 0.625, '_prefetched_objects_cache': {}}

    # USER
    # {'_state':, 'id': 1513, 'password': '', 'last_login': datetime.datetime(2019, 4, 23, 13, 22, 48, tzinfo=<UTC>), 'is_superuser': , 'username': 'inessieulle', 'first_name': 'Inès', 'last_name': 'Sieulle', 'email': 'ines.sieulle@gmail.com', 'is_staff': False, 'is_active': True, 'date_joined': }

    # Identify the promotion
    promo = Promotion.objects.get(pk=artist.student.promotion_id)
    print(promo.__dict__)
    student_mapping = {
        'promotion':'',
    }


        # logger.info("\n\n")
    # Log the function call
    logger.info(f"FUNCTION : clean_csv - STOP")


if __name__ == "__main__" :
    run_import()
