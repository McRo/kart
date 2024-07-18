from people.models import User, Artist, Staff
from production.models import (Film, Installation, Performance, Event,
                               Organization, FilmGenre, InstallationGenre,
                               OrganizationTask, ProductionOrganizationTask, StaffTask, ProductionStaffTask,)
from slugify import slugify
import markdownify
import csv
import unidecode
import datetime
import pytz
from langdetect import detect

from .utils.artist_utils import getArtistByNames
from .utils.user_utils import getUserByNames
from utils.kart_tools import usernamize


DRY_RUN = False
stats = {}

"""
    USAGE : ./manage.py runscript scripts.catalogue.catalogue-to-kart
    OU
    ./manage.py runscript scripts.catalogue.catalogue-to-kart --script-args DRY_RUN 
    -> DRY_RUN NE FONCTIONNE PAS

"""

def populateAPI(data):

    global DRY_RUN
    
    # GET DB ARTIST
    # get name
    artist_name = data['artist_nickname'] if data['artist_nickname'] else data['user_first_name'] + " " + data['user_last_name']    
    # search
    artist_search = getArtistByNames(data['user_first_name'], data['user_last_name'], data['artist_nickname'])
    artist_search_list = getArtistByNames(data['user_first_name'], data['user_last_name'], data['artist_nickname'], True)
    # doute ?
    if artist_search["dist"] < .9:
        ask = input("Est-ce la même personne ? (db) {}  <-> {} (csv)".format(artist_search["artist"], artist_name))
        if "n" in ask:
            print("Artiste non trouvé")
            print("Et dans cette liste ? ")
            select_with_result_list = input_choices(artist_search_list)
            if select_with_result_list:
                artist_search = select_with_result_list["artist"]
                created = False
            else:
                print("ARTIST CREATOR ERROR !!! ")
                print("il n'existe pas alors que normalement il doit être dans la base")
                return

    artist = artist_search["artist"]

    print("START WITH ARTIST")
    print("  {} ".format(artist))
    print("*********")

    # BIO
    bio_fr = select_french_text(data["artist_biography"], data["artist_biography_translated"])
    bio_en = select_english_text(data["artist_biography"], data["artist_biography_translated"])

    artwork_type = data["artwork_type"]
    
    artwork_title =  data["artwork_title"]
    artwork_subtitle = data["artwork_subtitle"]
    artwork_text_fr = select_french_text(data["artwork_description"], data["artwork_description_translated"])
    artwork_text_en = select_english_text(data["artwork_description"], data["artwork_description_translated"])
    
    # film
    artwork_duration = data["artwork_duration"]
    artwork_shooting_format = data["artwork_shooting_format"]
    artwork_aspect_ratio = data["artwork_aspect_ratio"]
    artwork_process = data["artwork_process"]
    shooting_places = data["artwork_shooting_places"]
    # install
    artwork_technical_description = data["artwork_technical_description"]
    # thanks
    artwork_thanks = data["artwork_thanks"]
    # partners
    artwork_partners = data["artwork_partners"]
    partners_description = data["artwork_partners_description"]
    # credits
    artwork_credits = data["artwork_credits"]
    artwork_credits_description = data["artwork_credits_description"]
    if artwork_credits == "" and "\n" in artwork_credits_description and ':' in artwork_credits_description:
        artwork_credits = artwork_credits_description
    # keywords
    keywords = data["artwork_keywords"]
    genres = data["artwork_genres"]
    # images
    images = data["artwork_images_screen"] if data["artwork_images_screen"] != "" else data["artwork_images"]

    images = replaceUrlMedia(images)
    images = images.split("|")
    
    artwork_avatar = images.pop()
    artwork_medias = images
    artwork_partners_media = replaceUrlMedia(data["artwork_logos"]).split("|") if data["artwork_logos"] else []

    # artist
    artist_db = artist

    print("ARTWORK")
    print("  {} - {}".format(artwork_title, artwork_type))
    print("*********")

    artwork = None
    if(artist_db):
        artwork = getOrCreateProduction(
            artist_db, artwork_title, artwork_type)
        

    # subtitle
    artwork.subtitle = artwork_subtitle

    # artist bio
    artist_db = updateArtistBio(artist_db, bio_fr, bio_en)

    # nickname
    if(artist_name and 
        slugify(artist_name) != slugify(artist_db.user.first_name + " " + artist_db.user.last_name)):                
        artist_db.nickname = artist_name

    # ARTIST SAVE 
    if not DRY_RUN:
        artist_db.save()

    # duration
    if(artwork_duration):
        # 20:00
        duration = artwork_duration.split(":")
        artwork.duration = datetime.timedelta(
            # hours=int(duration[0]), minutes=int(duration[1]))
            minutes=int(duration[0]), seconds=int(duration[1]))
        
   
    

    # text
    # artwork.description_fr = markdownify.markdownify(artwork_text_fr)
    artwork.description_fr = artwork_text_fr
    # artwork.description_en = markdownify.markdownify(artwork_text_en)
    artwork.description_en = artwork_text_en

    # keywords
    keyword_list = keywords.replace(", ",",").split(',')
    if not DRY_RUN:
        artwork.keywords.set(keyword_list)

    # genres
    genres_list = genres.split(",")
    for genre in genres_list:
        set_genre(artwork, genre)
  
    # print(artwork)
    
    # shooting_places
    if(artwork_type.lower() == 'film' and shooting_places):
        places_list = shooting_places.split('\n')
        for str_place in places_list:
            place = getPlace(str_place)
            if(place):
                artwork.shooting_place.add(place)
    # shooting format ->  keep first()
    if(artwork_type.lower() == 'film' and artwork_shooting_format):
        artwork.shooting_format = artwork_shooting_format.split(',')[0]
    # aspect_ratio
    if(artwork_type.lower() == 'film' and artwork_shooting_format):
        artwork.aspect_ratio = artwork_aspect_ratio.split(',')[0]

     # process
    if(artwork_type.lower() == 'film' and artwork_process):
        artwork.process = artwork_process.split(',')[0]


    if artwork_type.lower() == 'installation':
        artwork.technical_description = artwork_technical_description

    # avatar
    if( artwork_avatar == "" and artwork_medias):
        artwork_avatar = artwork_medias.pop(0)

    if(artwork_avatar and not artwork.picture):
        avatar_name = artwork_avatar.split('/')[-1]
        avatar_file = createFileFromUrl(artwork_avatar)
        artwork.picture.save(avatar_name[-35:], avatar_file, save=True)
    # gallery
    gallery_visuels, gall_created = createGalleryFromArtwork(artwork, artist_db, "Images de l'oeuvre")
    artwork.in_situ_galleries.add(gallery_visuels.id)
    if gall_created:
        for url in artwork_medias:
            createMediaFromUrl(url, gallery_visuels.id)


    # partners
    # set base production
    orga_fresnoy = Organization.objects.get(
        name__icontains='le fresnoy')
    task_prod = OrganizationTask.objects.get(
        label__icontains='producteur')

    po, created = ProductionOrganizationTask.objects.get_or_create(
        task=task_prod, organization=orga_fresnoy, production=artwork)
    
    setStats(po, created)
    
    set_partners(artwork, artwork_partners, artwork_partners_media)
    
    # collaborators -> credits
    set_credits(artwork, artwork_credits)

    artwork.thanks_fr = markdownify.markdownify(artwork_thanks)
    artwork.credits_fr = markdownify.markdownify(artwork_credits_description)

    if(partners_description):
        artwork.credits_fr += "\n\nDescription du partenariat:\n"
        artwork.credits_fr += markdownify.markdownify(partners_description)




    # ARTWORK SAVE
    artwork.save()

    print("END ARTWORK")
    print("  {} - {}".format(artwork, artwork.id))
    print("*********")

    return artwork


def replaceUrlMedia(str):
    return str.replace("app/static/", "https://catalogue-panorama.lefresnoy.net/static/")


def setStats(value_from_model, created):
    class_name = value_from_model.__class__.__name__.lower()
    attibute = class_name + "_created" if created else class_name + "_reused"
    if not attibute in stats:
        stats[attibute] = []
    stats[attibute].append(value_from_model)



def get_or_create(model, attr):

    global DRY_RUN

    created = False
    try:
        instance = model.objects.get(**attr)
    except Exception as e:
        instance = model(**attr)
        created = True
        if not DRY_RUN:
            instance.save()
    return [instance, created]



def select_french_text(str1, str2):
    str1_language = detect(str1)
    if(str1_language == 'fr'):
        # print("LAngue FR : ", str1[:25])
        return str1
    # print("LAngue FR : ", str2[:25])
    return str2

def select_english_text(str1, str2):
    str1_language = detect(str1)
    if(str1_language == 'en'):
        # print("LAngue EN : ", str1[:25])
        return str1
    # print("LAngue EN : ", str2[:25])
    return str2


def input_choices(values):

    if not values:
        return False
    
    print("Plusieurs valeurs sont possibles, selectionnez-en une :")
    for id, value in enumerate(values):
        print("{} : {}" .format(id, value))
    print("n : pas dans la liste")
    select = input("Votre choix : ")
    
    # select = input("Plusieurs valeurs sont possibles, selectionnez-en une :" 
    #                + str([str(id) + " : " + str(s) for id, s in enumerate(values)]))
    try:
        select_int = int(select)
        selected = values[select_int]
        return selected
    except Exception as e:
        return False
    

def set_partners(artwork, partners_str, partners_media):
    if partners_str.strip() == "":
        return
    # FORME - type : structure \n
    partners_arr = partners_str.split("\n")
    for partner in partners_arr:
        # la forme Coproduction : Julien Taïb, Crossed Lab
        partner = partner.strip()
        if partner == "":
            continue
        if not ":" in partner:
            # set default partenaire type
            partner = "Partenaire : " + partner
        
        # TYPE 
        partner_type_str = partner.split(":")[0].strip()
        partner_types = getOrCreateMultiInstancesByStr(OrganizationTask, 'label', partner_type_str)

        # ORGANIZATION
        organization_str = partner.split(":")[1].strip()
        organizations = getOrCreateMultiInstancesByStr(Organization, "name", organization_str)

        # ADD logo to ORGA
        for organization in organizations:
            name = organization.name
            if not organization.picture and partners_media:
                print("Organisation : " + name + " est sans logo, est-ce qu'il est dans ce choix ? ")
                media_choice = input_choices(partners_media)
                if media_choice:
                    name = media_choice.split('/')[-1]
                    file = createFileFromUrl(media_choice)
                    organization.picture.save(name[-35:], file, save=True)

        
        # HAVE TO 
        # ONE type ONE organization
        # One type Multi organizations
        # Multi types -> problems One task
        # Multi type multi organizations -> problem
        if (len(partner_types) == 0 or 
            len(organizations)==0 or
            (len(partner_types) > 1 and len(organizations) > 1) ):
            print("*****PROBLEME DE PARTNERS  ******")
            print(partner)
            continue
        # partner : organization
        elif len(partner_types) == 1 and len(organizations) == 1:
            partner_type = partner_types[0]
            organization = organizations[0]
            pot, created = ProductionOrganizationTask.objects.get_or_create(
                task=partner_type, organization=organization, production=artwork)
            setStats(pot, created)
            print(pot)
        # partner : organization 1, organization 2
        elif len(partner_types) == 1 and len(organizations) > 1:
            partner_type = partner_types[0]
            for organization in organizations:
                pot, created = ProductionOrganizationTask.objects.get_or_create(
                     task=partner_type, organization=organization, production=artwork)
                setStats(pot, created)
                print(pot)
        # partner, coproduction  : organization
        elif len(partner_types) > 1 and len(organizations) == 1:
            organization = organizations[0]
            for partner_type in partner_types:
                pot, created = ProductionOrganizationTask.objects.get_or_create(
                     task=partner_type, organization=organization, production=artwork)
                setStats(pot, created)
                print(pot)


def getOrCreateMultiInstancesByStr(model, attr, txt_str):
    instances = []

    if "," in txt_str or  " et " in txt_str:
        str_split = txt_str.split(",") if "," in txt_str else txt_str.split(" et ")
        for s in str_split:
            instance = getOrCreateModelInstanceByStr(model, attr, s)
            instances.append(instance)
    else:
        instance = getOrCreateModelInstanceByStr(model, attr, txt_str)
        instances.append(instance)

    return instances


def getOrCreateModelInstanceByStr(model, attr, txt_str):
    
    instance = False
    
    query = model.objects.filter(**{attr+"__iexact":txt_str})
    if query.count() == 0:
        query = model.objects.filter(**{attr+"__icontains":txt_str})
    
    if query.count() > 1:
        print(str(model) + " (csv) : "+ txt_str)
        instance = input_choices(query)
        
    elif query.count() == 1:
        instance = query.first()

    if not instance:
        instance, created = model.objects.get_or_create(**{attr:txt_str.title()})
        setStats(instance, created)
        print("Création d'une instance" + str(model) + " : " + str(instance))

    return instance



def set_genre(aw, genre_str):
    genre_str = genre_str.strip()

    if genre_str == "":
        return

    modelGenre = FilmGenre if aw.polymorphic_ctype.model == 'film' else InstallationGenre
    # query genre
    genre_query = modelGenre.objects.filter(label__iexact=genre_str)
    if genre_query.count() == 0:
        genre_query = modelGenre.objects.filter(label__icontains=genre_str)

    genre = False
    if genre_query and genre_query.count() == 1:
        genre = genre_query.first()
        
    elif genre_query and genre_query.count() > 1:
        print("Genre csv : "+ genre_str)
        genre = input_choices(genre_query)

    if not genre:
        print("********** GENRE PROBLEME *********** ")
        print(genre)
    else:
        aw.genres.add(genre)


def set_credits(aw, credits):
    
    # many ways detected in csv
    # staf : task \n
    # staf : name or fistname, lastname

    if not "\n" in credits:
        return False

    credits_arr = credits.split("\n")
    for credit in credits_arr:

        if not ":" in credit:
            print("/!\\ credit n'a pas de ':'" + credit)
            continue        
        
        # SEARCH FOR USER
        user_str = credit.split(":")[0]
        print("SEARCH FOR USER : " + user_str)
        users = []
        user = False
        # "," in name mean that this is an human in DB (comme with catalog plateform dev)
        # but mean sometimes two person for the same task Nina Guseva, Anna Collard : céramiste 
        # OR Nina Guseva et Anna Collard
        if "," in user_str or  " et " in user_str:
            str_split = user_str.split(",") if "," in user_str else user_str.split(" et ")
            first_user = str_split[0].strip()
            # is multi ? il y a un espace (nom prénom) et c'est assez long
            if(" " in first_user and len(first_user)>3):
                for u in str_split:
                    user, created = get_or_create_user(u)
                    users.append(user)
        # "," est gérée dans get_or_create_user
        if not user:
            user, created = get_or_create_user(user_str)
            users.append(user)
        
        # Is staff
        staffs=[]
        for user in users:
            if user.staff_set.count() > 0:
                staff = user.staff_set.first()
            else:
                staff, created = Staff.objects.get_or_create(user=user)
                setStats(staff, created)                    
            staffs.append(staff)

        # search for task
        task_str = credit.split(":")[1]
        # sometimes Benjamin Griere : Graphisme 3D, Développeur 3D
        tasks = getOrCreateMultiInstancesByStr(StaffTask, 'label', task_str)

        # HAVE TO 
        # ONE user ONE task
        # One user Multi tasks
        # Multi users One task
        # Multi user multi task -> problem
        if (len(staffs) == 0 or 
            len(tasks)==0 or
            (len(staffs) > 1 and len(tasks) > 1) ):
            print("*****PROBLEME DE CREDIT ******")
            print(credit)
            continue
        elif len(staffs) == 1 and len(tasks) == 1:
            staff = staffs[0]
            task = tasks[0]
            pst, created = ProductionStaffTask.objects.get_or_create(staff=staff, task=task, production=aw)
            setStats(pst, created)
            print(pst)

        elif len(staffs) > 1 and len(tasks)==1:
            task = tasks[0]
            for staff in staffs:
                pst, created = ProductionStaffTask.objects.get_or_create(staff=staff, task=task, production=aw)
                setStats(pst, created)
                print(pst)

        elif len(staffs) == 1 and len(tasks) > 1:
            staff = staffs[0]
            for task in tasks:
                pst, created = ProductionStaffTask.objects.get_or_create(staff=staff, task=task, production=aw)
                setStats(pst, created)
                print(pst)
            
    # END OF FOR CREDITS

        
def get_or_create_user(user_str):
    # search user from usersearchutils
    # return user
    
    first_name, last_name = get_first_last_name_from_str(user_str)
    print("firsname:"+first_name)
    print("lastname:"+last_name)

    user = False
    user_search = False
    created = False
    # are we lucky ?
    # , mean that this is an human in DB
    if "," in user_str:
        user_search = getUserByNames(user_str.split(",")[0], user_str.split(",")[1])
        search_list = getUserByNames(first_name, last_name, True)

    # search by artist : ça arrive (SMITH?!)
    if not user_search:
        user_search = getArtistByNames("", "", user_str)
        search_list_artist = getArtistByNames("", "", user_str, True)
        if user_search and user_search["dist"] >= .9:
            artist = user_search["artist"]
            user = artist.user
            created = False
        else:
            user_search = False
            user = False
    
    # try user_search if we are not in previous cases
    if not user and not user_search:
        user_search = getUserByNames(first_name, last_name)
        search_list = getUserByNames(first_name, last_name, True)

    # search in DB
    if not user and user_search:
        if user_search["dist"] <= 1:
            print("Recherche d'un User : " + user_str)
            # concat arrays if exist
            list = search_list + search_list_artist if search_list_artist else search_list
            select_with_result_list = input_choices(list)
            if select_with_result_list:
                if "user" in select_with_result_list:
                    user = select_with_result_list["user"]

                if "artist" in select_with_result_list:
                    artist = select_with_result_list['artist']
                    user = artist.user
                created = False
        else:
            user = user_search["user"]
            created = False
            print("KNOW User : " + str(user) + "(kart)  pour " + user_str + " (csv)")
            # print(user_search)
                        
    if not user:
        username = usernamize(first_name, last_name, False)
        try:
            user, created = User.objects.get_or_create(first_name=first_name.title(), last_name=last_name.title(), 
                                                       username=username)
        except Exception as e:
            username = usernamize(first_name, last_name, True)
            user, created = User.objects.get_or_create(first_name=first_name.title(), last_name=last_name.title(), 
                                                       username=username)
        setStats(user, created)
        print("CREATE User : " + str(user))

    return [user, created]

def get_or_create_stafftask(task_str):
    print("SEARCH FOR TASK : " + task_str)
    # delete spaces
    task_str = task_str.strip()
    # search by query exact and second time filter
    task_query = StaffTask.objects.filter(label__iexact=task_str)
    if task_query.count() == 0:
        task_query = StaffTask.objects.filter(label__icontains=task_str)
    # init task
    task = False
    # find more than one ? choose !
    if task_query.count() > 1:
        print("Plusieurs tâches ont été trouvées pour : " + task_str)
        task = input_choices(task_query)
        
    elif task_query.count() == 1:
        task = task_query.first()
    if not task:
        task, created = StaffTask.objects.get_or_create(label=task_str.title())
        setStats(task, created)   
        print("Création TASK : " + str(task))
    
    print(task)

    return task



# 
def get_first_last_name_from_str(str):
    str = str.strip()
    if " " in str:
        str_split = str.split(" ", 1)
        first_name = str_split[0]
        last_name = str_split[1]

        return [first_name, last_name]
    return ["", str]

#
def getPlace(str_place):
    from geopy.geocoders import Nominatim
    from geopy import distance
    
    from diffusion.models import Place

    # recharche dans les places existant
    print( "Place cherche : ", str_place,".")
    # clear str
    if(str_place.strip() == ""):
        return None
    # error
    if not "," in str_place:
        city = country = str(str_place)
    else:
        city, country = str_place.split(',',1)
    # search place in bdd
    place = Place.objects.filter(city=city)
    if(place):
        # print( "Trouve dans la base : ", place)
        return place.first()
    else:
    # recherche dans les internets
        geolocator = Nominatim(user_agent="panorama_creation_place")
        location = geolocator.geocode(str_place, language="fr", addressdetails=True)

        if(not location):
            # print( "!!!!!!!! Nouvel essaie : ", str_place)
            from functools import partial
            geo = partial(geolocator.geocode, language="fr", addressdetails=True)
            location = geo(str_place)

        if(not location):
            # print( "!!!!!_____ Nouvel essaie : ", str_place)
            from functools import partial
            geo = partial(geolocator.geocode, language="fr", addressdetails=True)
            location = geo(country)

        if(location):
            #print( "Trouve dans les internets : ", location)
            # -> si trouve, recherche si pas loin d'une place existante
            places = Place.objects.all()
            for p in places:
                point1 = (p.latitude, p.longitude)
                point2 = (location.latitude, location.longitude)
                if(distance.distance(point1, point2).km < 0.1 ):
                    print ("_______ UNE place dans la base a été trouvée : ", p)
                    return p
            print("Pas de place dans la base à proximité, création")
            
            country_code = location.raw['address']['country_code'] if location.raw else ""
            # city
            location_city = city
            for key in ["town","city", "village", "province"]:
                if(key in location.raw['address']):
                    location_city = location.raw['address'][key]
                    break

            place = Place(name=city,
                          description=city,
                          address=location.address[:255],
                          latitude=location.latitude,
                          longitude=location.longitude,
                          city=location_city[:50],
                          country=country_code,
                          )
            if not DRY_RUN:
                place.save()
            return place
    print("/!\/!\/!\/!\ Rien trouvé ! :", str_place, "\n")
    return None


def createFileFromUrl(url):
    from django.core.files import File
    from django.core.files.temp import NamedTemporaryFile
    import urllib

    if(url == ""):
        return None
    
    # url = url.replace("app/static/", "https://catalogue-panorama.lefresnoy.net/static/")

    print("téléchargement du media : (...)" + url[-35:])
    
    img_temp = NamedTemporaryFile(delete=True)
    img_temp.write( open( urllib.request.urlretrieve(url)[0], 'rb').read() )
    img_temp.flush()

    return File(img_temp)


def createMediaFromUrl(url, gallery_id):
    from assets.models import Medium

    if(url == ""):
        return None
    
    file = createFileFromUrl(url)
    name = url.split('/')[-1]

    medium = Medium()
    medium.gallery_id = gallery_id
    medium.picture.save(name[:35], file, save=True)

    medium.save()
    
    return medium

def createGalleryFromArtwork(artwork, authors, gallery_type):
    from assets.models import Gallery

    label = "{0} - {1}".format(gallery_type,  artwork.title)
    gallery, created = get_or_create(Gallery, {'label':label} )

    gallery.description = "{0} \n {1}".format(authors, artwork.title)
    gallery.description += "{0} {1}".format(artwork.polymorphic_ctype.name, artwork.production_date.year)
    gallery.description += "\nProduction Le Fresnoy – Studio national des arts contemporains"
    gallery.description += "\n© {}".format(authors)

    gallery.save()
    return [gallery, created]


def updateArtistBio(artist, bio_fr, bio_en):

    bio_fr = markdownify.markdownify(bio_fr)
    bio_en = markdownify.markdownify(bio_en)

    # print(bio_fr)
    # verify empty bio
    if(artist.bio_fr == ""):
        # print(artist.__str__() + " : update bio")
        artist.bio_fr = bio_fr
    else:
        # keep infos
        # print(artist.__str__() + " : has an old bio")
        if(not "<!--" in artist.bio_fr and 
           not bio_fr in artist.bio_fr
           ):
            # print(artist.__str__() + " : update his old bio")
            artist.bio_fr = "<!--"+artist.bio_fr+"-->\n"+bio_fr

    if(artist.bio_en == ""):
        artist.bio_en = bio_en
    else:
        if(not "<!--" in artist.bio_en and 
           not bio_fr in artist.bio_en
           ):
            artist.bio_en = "<!--"+artist.bio_en+"-->\n"+bio_en

    return artist


def getStudent(name, firstname, email):
    return getArtist(name, firstname, email, True)


def createArtist(name, firstname, email):
    username = unidecode.unidecode(firstname[0]+name)
    user, user_created = User.objects.get_or_create(
        username=username, email=email, first_name=firstname, last_name=name)
    artist, artist_created = Artist.objects.get_or_create(user=user)

    return artist


def getArtist(idartist):
    searchresult = None
    try:
        return Artist.objects.get(id=idartist)
    except(Artist.MultipleObjectsReturned, Artist.DoesNotExist):
        searchresult = None


def getOrCreateProduction(artist, title, type):

    production = None
    created = False
    production_year = datetime.datetime.now().year

    if(type.lower() == "film"):
        production, created = get_or_create(Film, 
                                            {'title':title, 'production_date':datetime.date(production_year, 1, 1)})

    if(type.lower() == "installation"):
        production, created = get_or_create(Installation, 
                                            {'title':title, 'production_date':datetime.date(production_year, 1, 1)})
    if(type.lower() == "performance"):
        production, created = get_or_create(Performance, 
                                            {'title':title, 'production_date':datetime.date(production_year, 1, 1)})
        
    if(created):
        production.authors.add(artist)
    
    setStats(production, created)

    return production


def makePressFolder(artist_name, firstname, lastname, artwork_title):

    name = artist_name if(artist_name) else firstname + " " + lastname.upper()
    path_artist = slugify(name)
    path_artwork = slugify(artwork_title)

    # MAKE FOLDER PRESS
    print('mkdir "{}" '.format(path_artist))
    print('echo "{0}" >  "{1}/artist.txt"'.format(name, path_artist))
    print('mkdir "{0}/{1}" '.format(path_artist, path_artwork))
    print('echo "{2}" >  "{0}/{1}/artwork.txt"'.format(path_artist,
          path_artwork, artwork_title))


def cleanHTML(text):
    markdownify.markdownify(text)


# Mapping entre les colonnes CSV et les champs du modèle
FIELD_MAPPING = {
    'email':'user_email',
    'first_name':'user_first_name',
    'last_name':'user_last_name',
    'artist_type':'artist_type',
    'artist_name':'artist_nickname',
    'biography':'artist_biography',
    'biography_translated':'artist_biography_translated',
    'type':'artwork_type',
    'title':'artwork_title',
    'subtitle':'artwork_subtitle',
    'description':'artwork_description',
    'description_translated':'artwork_description_translated',
    'duration':'artwork_duration',
    'shooting_format':'artwork_shooting_format',
    'aspect_ratio':'artwork_aspect_ratio',
    'process':'artwork_process',
    'genres':'artwork_genres',
    'languages_vo':'artwork_languages_vo',
    'languages_subtitles':'artwork_languages_subtitles',
    'technical_description':'artwork_technical_description',
    'thanks':'artwork_thanks',
    'partners':'artwork_partners',
    'partners_description':'artwork_partners_description',
    'credits':'artwork_credits',
    'credits_description':'artwork_credits_description',
    'keywords':'artwork_keywords',
    'shooting_places':'artwork_shooting_places',
    'images':'artwork_images',
    'images_screen':'artwork_images_screen',
    'logos':'artwork_logos',
}

def map_csv_to_model(row):
    """Map les données d'une ligne CSV aux champs du modèle."""
    
    mapped_data = {}
    for csv_column, model_field in FIELD_MAPPING.items():
        mapped_data[model_field] = row.get(csv_column).strip()
    return mapped_data

def run(*args):
    # settup args
    global DRY_RUN
    if 'DRY_RUN' in args:
        DRY_RUN = True
        print("DRY_RUN Script")
        c = input("LE DRYRUN NE FONCTIONNE PAS ! Voulez-vous continuer ? Y/n")
        if c == "n":
            return
    # get the file
    fichier_csv = 'scripts/catalogue/catalogue.csv'  # 

    input("Vérifiez que vous avez la dernière version du catalalogue à mettre dans : " + fichier_csv)

    # create Panorama event
    current_year = datetime.datetime.now().year
    event, created = Event.objects.get_or_create(title="Panorama " + str(current_year+2-2000), 
                                        starting_date=datetime.datetime(current_year, 1, 1, 
                                                                        tzinfo=pytz.timezone("Europe/Paris")),)
   
    
    with open(fichier_csv, 'r') as csvfile:
        lecteur_csv = csv.DictReader(csvfile, delimiter=',', quotechar='"' )
        # TEST : avance dans le tableau
        # for i in range(10):
        #     row = next(lecteur_csv)

        for row in lecteur_csv:
            data = map_csv_to_model(row)
            artwork = populateAPI(data)
            # set sevent to panorama
            event_artworks = event.films if artwork.polymorphic_ctype.model == 'film' else event.installations
            event_artworks.add(artwork)
    
    for elt in stats:
        print(elt + " : " + str(len(stats[elt])))


    event.save()
