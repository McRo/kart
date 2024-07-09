#! /usr/bin/env python
# -*- coding=utf8 -*-

"""
Import VOD data (csv) to KART
======== NO SPELL/SIMILARITY CHECK THE DATA ! ==============
Artwork id is used as sole reference.
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
import unidecode

# local modules
from correction import Correction
from csv_utils import getArtworkByTitle, getDiffGallery, is_url

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
DRY_RUN = False  # No save() if True
DEBUG = True

# Set script file location as current working directory
OLD_CWD = os.getcwd()
os.chdir(pathlib.Path(__file__).parent.absolute())

# Allow to lower data in query with '__lower' in psql requests
CharField.register_lookup(Lower)

# Logging
logger = logging.getLogger('import_pano_data')

# Minimum level of message to trigger logging
logger.setLevel(logging.DEBUG)

# clear the logs
open('import_csv.log', 'w').close()

# create file handler which logs even debug messages
fh = logging.FileHandler('import_csv.log')
# Minimum level of message to trigger logging in filehandler
fh.setLevel(logging.DEBUG)

# create console handler with a higher log level
ch = logging.StreamHandler()
# Minimum level of message to trigger logging in console
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

# Load the Yaml config file : csvkart_mapping, excluded columns ...
with open("import.yaml", 'r') as stream:
    try:
        # load the data from yml file
        conf=yaml.safe_load(stream)
    except yaml.YAMLError as exc:
        print(exc)

# Log the csv data that were not added to Kart
open("not_added.yaml", 'w+')


##################################################
# Mappings btw csv fields and Kart's fields #
##################################################

def run_import(csv_path) :
    """ Main function to call to trigger the import process

        Args :
            csv_path (str) : The path of the csv to load
        Returns :
            None
    """

    # Try to read the csv file to validate the path (FileNotFoundError otherwise)
    cf = open(csv_path, 'r')

    # Clean the csv from udesired data
    clean_csv(csv_path)



def clean_csv(csv_path, dest='./') :
    """ Clean the csv from undesired data and store a cleaned csv with validated data from Kart when data already exists in Kart.

    args:
        csv_path (str)  : path to the csv file
        dest (str)      : path to the destination csv file, optional


    """

    # Log the function call
    logger.info(f"FUNCTION : clean_csv - START\n")

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

        # Diffusion title
        title_diff = row['Titre diffusion']

        # Parsing of the title  e.g. Le vieil enfant film de Felipe Esparza - 2020 (id: 1297)
        title = row.title

        # Extract id artw
        pat = re.compile('\(id: (\d+)\)')
        match = re.search(pat, title)

        # if id can be extracted
        if match :
            id = match[1]

            # Instantiate the aw with the id
            aw = Artwork.objects.get(pk=id)

        # if id can't be extracted, try to retrieve aw with diffusion title
        else :
            logger.warning(f"Can't extract id from {title}")

            # Try to get the artw by title
            aw = getArtworkByTitle(title_diff, sim_limit=.7)

            # If an aw match the title, use it
            if aw :
                logger.debug(f"The submitted title \"{title}\" matches the Kart artwork entitled \"{aw.title}\"")

            # If there is no match, abort the process for that row and continue
            else :
                logger.warning(f"The artwork \"{title}\" can not be found in Kart. Aborting.")

                with open("not_added.yaml", 'a') as stream:
                    try:
                        stream.write(f"ERROR_NOT_ADDED :\n  Diffusion title : {title_diff} \n  Reason : No id provided + Title not found in Kart \n  Original data : {title}\n\n")
                    except yaml.YAMLError as exc:
                        print(exc)
                # Stop the process for that artwork and continue with the next row
                continue

        # Get the diff gallery from Kart
        diff_gal = getDiffGallery(aw.id)



        # getDiffGallery() return None if the aw has no diff gallery
        if diff_gal is None :
            print(f"No Diff Gallery for {aw.title}")
            print(f"\tInstantiating a new gallery ...")

            # create a new gallery
            diff_gal = Gallery()
            diff_gal.label = "Diffusion"
            diff_gal.description = f"Galerie de diffusion de {aw.title} (id:{aw.id})"

            # save the created gallery
            diff_gal.save()

            # add the new gallery to artwrok
            aw.diff_galleries.add(diff_gal)

            # Save the gallery TODO : really useful after an "add()" ?
            aw.save()

        # getDiffGallery() return False if the aw does not exist (should not occur as the aw exists here)
        elif diff_gal == False :
            print("Artwork does not exist")
            continue

        # If the diff gallery already exists
        # harmonize the gal title and description
        print(f"{aw.title} has a diff gallery : {diff_gal}")
        diff_gal.description = f"Galerie de diffusion de {aw.title} (id:{aw.id})"
        diff_gal.save()

        # Check if the media does not already exists in the gallery
        # get the media associated with the gallery
        existing_media = Medium.objects.filter(gallery=diff_gal.id)

        # the list of media to create
        media_to_create = []

        # Check the existence of both FR and EN media and create them accodingly
        for lang in ['FR', 'EN'] :
            new_media_url = row[lang]

            # new_media_url is not well defined, raise a warning
            if new_media_url and not is_url(new_media_url) :
                logger.warning(f"{title} ({lang}) : url not well defined : \"{new_media_url}\"")

            # If a proper url is provided
            if new_media_url and is_url(new_media_url) :
                # Dict with new media properties
                new_media = {   'label' : 'Diffusion video',
                                'medium_url' : new_media_url,
                                'description': f"lang : {lang}",
                                'updated_on' : datetime.now(),
                                'gallery' : diff_gal
                                }
                media_to_create += [new_media]

                # if there are media related to the gallery
                for medium in existing_media :
                    # if the existing media has the same url than the new, remove it from list to create
                    # (check also the description in case of same url for EN and FR version)
                    if medium.medium_url == row[lang] and medium.description != new_media['description'] :
                        logger.warning(f"{title} : Same url for EN and FR version")
                    if medium.medium_url == row[lang] and medium.description == new_media['description'] :
                        # remove the media from the list to create if same url and same description
                        media_to_create.pop()


        for new_media in media_to_create :
            medium = Medium(**new_media)
            medium.save()



def csv2kart(field="", model="", csvkart_mapping=conf['csvkart_mapping']):
    """ Return the corresponding Kart field name from current csv field name"""
    if "" == model :
        for model in csvkart_mapping.keys() :
            for k, v in csvkart_mapping[model].items():
                if v == field : return k
    else :
        for k, v in csvkart_mapping[model].items():
            if v == field : return k
    return field


if __name__ == "__main__" :
    # id_prod = 416
    # gal = getDiffGallery(id_prod)
    # run_import(csv_path="./Kart-TEASER_VOD.csvSd")
    pass