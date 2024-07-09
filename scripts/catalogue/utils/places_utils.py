import os
import sys
import pandas as pd
import logging
from difflib import SequenceMatcher
import re
import unidecode
import pathlib


import django
from django.conf import settings
sys.path.append(str(pathlib.Path(__file__).parent.parent.absolute()))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "kart.settings")
django.setup()


from diffusion.models import Place
from django.contrib.postgres.search import TrigramSimilarity
from django_countries import countries





# Logging
logger = logging.getLogger('create_places')

# Minimum level of message to trigger logging
logger.setLevel(logging.DEBUG)

# clear the logs
open('import_csv.log', 'w').close()

# create file handler which logs even debug messages
fh = logging.FileHandler('create_places.log')
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



DEFAULT_CSV = "/tmp/events.csv"

def createPlaces(csv_file=DEFAULT_CSV, dry_run = False, DEBUG = True):
    """Create the places listed in the awards csv files

    """

    global CREATED_CONTENT

    # Get the data from awards csv extended with title cleaning and events (merge.csv)
    merge = pd.read_csv('./tmp/events.csv')
    # Drop duplicates
    places = merge.drop_duplicates(['place_city', 'place_country'])
    # Remove rows with full empty location
    places = places.dropna(subset=['place_city', 'place_country'], how="all")
    # Replace NA/NaN (similarity fails otherwise)
    places.fillna('', inplace=True)

    for ind, place in places.iterrows():
        city = place.place_city
        country = place.place_country
        if city == country == '':
            continue
        logger.info(f"\n\nPLACE: {city} - {country}")

        # Processing CITY
        # Look for really approaching (simi=.9) name of city in Kart
        guessCity = Place.objects.annotate(
            similarity=TrigramSimilarity('name', city),
        ).filter(similarity__gt=0.9).order_by('-similarity')

        # If a city in Kart is close from the city in csv file
        if guessCity:
            logger.info(f"CITY FOUND IN KART: {guessCity[0].city}")
        else:
            logger.info("No close city name in Kart, the place should be created or is empty")

        # Processing COUNTRY
        # Look for ISO country code related to the country name in csv
        codeCountryCSV = getISOname(country)

        # If code is easly found, keep it
        if codeCountryCSV:
            logger.info(f"CODE FOUND: {country} -> {codeCountryCSV}")

        # If no code found, check if the country associated with the city found in Kart
        # is close from the country in csv file to use its code instead
        elif guessCity and guessCity[0].country:
            codeCountryKart = guessCity[0].country
            countryNameKart = dict(countries)[codeCountryKart]

            # Compute the distance between the 2 country names
            dist = round(SequenceMatcher(None, str(country).lower(),
                                         countryNameKart.lower()).ratio(), 2)

            # If really close, keep the Kart version
            if dist > .9:
                logger.info(f"Really close name, replacing {country} by {countryNameKart}")
                codeCountryCSV = codeCountryKart
            else:
                # Process the us case (happens often!)
                if re.search('[EeéÉ]tats[ ]?-?[ ]?[Uu]nis', country):
                    codeCountryCSV = "US"
                else:  # If not close to the Kart version, try with similarity with other countries
                    codeCountryCSV = getISOname(country, simili=True)

        else:  # No city found, so no clue to find the country => full search
            # parameter simili=True triggers a search by similarity btw `country` and django countries entries
            codeCountryCSV = getISOname(country, simili=True)
            if codeCountryCSV:
                logger.info(
                    f"Looked for the country code of {country} and obtained {codeCountryCSV}")
            else:
                # Check for Kosovo:
                # Although Kosovo has no ISO 3166-1 code either, it is generally accepted to be XK temporarily;
                # see http://ec.europa.eu/budget/contracts_grants/info_contracts/inforeuro/inforeuro_en.cfm or the CLDR
                if re.search("kosovo", country, re.IGNORECASE):
                    codeCountryCSV = "XK"
                logger.info("No city found, no country found:-(")

        # Check if place exists, if not, creates it
        place_obj = Place.objects.filter(
            name=city if city else country,
            city=city,
            country=codeCountryCSV if codeCountryCSV else ''
        )
        # If place already exist
        if len(place_obj):
            # Arbitrarily use the first place of the queryset (may contain more than 1)
            # TODO: what if more than one ?
            place_obj = place_obj[0]
            created = False
        else:
            # Create the Place
            place_obj = Place(
                name=city if city else country,
                city=city,
                country=codeCountryCSV if codeCountryCSV else ''
            )
            if not dry_run:
                place_obj.save()
            # TODO : modify model for dry_run mode (see event model)

            created = True
        if place.place_city == '':
            logger.info(f'Empty City ============== {place_obj}')

        if created:
            logger.info(f"Place {place_obj} was created")
        else:
            logger.info(f"Place {place_obj} was already in Kart")
        # Store the id of the place
        places.loc[ind, 'place_id'] = place_obj.id

    # Store the places
    places.to_csv('./tmp/places.csv', index=False)

    # test to deal with city only rows, use "NULL" to allow the merging with missing data
    places.loc[places['place_city'] == '', 'place_city'] = "**NULL**"
    merge.loc[merge['place_city'].isna(), 'place_city'] = "**NULL**"

    merge_df = pd.merge(
        merge,
        places[["place_city", "place_country", "place_id"]],
        how='left', on=["place_city", "place_country"]
    )
    # Restore the missing data after the merge
    merge_df.loc[merge_df['place_city'] == "**NULL**", 'place_city'] = ''
    merge_df.to_csv('./tmp/merge_events_places.csv', index=False)


def getISOname(countryName=None, simili=False, dry_run=False, DEBUG=True):
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


if __name__ == "__main__":
    
    createPlaces()



    