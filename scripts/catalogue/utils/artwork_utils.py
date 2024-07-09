


def artworkCleaning():
    """Preparation and cleannig step of the awards csv file

    WARNING: this function requires a human validation and overrides `artworks_artists.csv` & `merge.csv`

    1) from the csv data, extract potential artworks already present in Kart
    2) when doubts about the name of the artwork, with close syntax, store the artwork kart_title in a csv for
    validation by head of diffusion.
    3) if no match at all, mark the artwork for creation
    """

    aws = pd.read_csv('./tmp/merge.csv')

    # Check if the id provided in the csv match with the artwork description
    # replace the nan with empty strings
    aws.fillna('', inplace=True)

    # List of object to create
    obj2create = []

    # For each award of the csv file
    for ind, aw in aws.iterrows():

        # Variables init
        no_artwork = no_artist = False

        # Parsing
        aw_id = int(aw.artwork_id) if aw.artwork_id else None
        aw_title = str(aw.artwork_title)
        lastname = str(aw.artist_lastname)
        firstname = str(aw.artist_firstname)
        _artist_l = getArtistByNames(firstname=firstname, lastname=lastname, listing=True)

        # If an id is declared, get the aw from kart and check its
        # similarity with the content of the row to validate
        if aw_id:
            # Artwork validation if the title from aw generated with id and title in csv
            aw_kart = Artwork.objects.prefetch_related('authors__user').get(pk=aw_id)
            if dist2(aw_kart.title, aw_title) < .8:
                logger.warning(f"""ARTWORK INTEGRITY PROBLEM:
                    Kart       :\"{aw_kart.title}\"
                    should match
                    Candidate  : \"{aw_title}\"""")
                aws.loc[ind, 'aw_art_valid'] = False

            # Artist/author validation
            # The closest artists in Kart from the data given in CSV (listing => all matches)
            _artist_l = getArtistByNames(firstname=firstname, lastname=lastname, listing=True)

            # If no match, should create artist ?
            if not _artist_l:
                # Add the object to the list of object to create
                o2c = {'type': 'Artist', 'data': {'firstname': firstname, 'lastname': lastname, }}
                if o2c not in obj2create:
                    logger.warning(
                        f"No artist can be found with {firstname} {lastname}: CREATE ARTIST ?\n\n")
                    obj2create.append(o2c)
                # Create the object in Kart # TODO
                # input(f'Should I create the an artist with these data: {o2c} ')
                continue

            # Compare the artists found in CSV to the authors of the artwork in Kart
            # List of the artist that are BOTH in the authots in Kart and in the CSV
            artist_in_authors = [x['artist']
                                 for x in _artist_l if x['artist'] in aw_kart.authors.all()]

            # If no match between potential artists and authors: integrity issue of the csv
            if not len(artist_in_authors):
                logger.warning(
                    f"""Artist and artwork do not match ---------- SKIPPING\nArtist: {_artist_l}\n
                    Artwork: {aw_kart}\n{aw_kart.authors.all()[0].id}\n\n""")
                aws.loc[ind, 'aw_art_valid'] = False
                continue
            else:
                # Otherwise, the authors are validated and their id are stored in csv
                aws.loc[ind, "artist_id"] = ",".join([str(x.id) for x in artist_in_authors])
                # logger.info(f"authors {aws.loc[ind, 'artist_id']}")
                # Continue to next row
                continue

        # If no id and no title provided, skip
        if not aw_id and aw_title == '':
            logger.info(
                "No data about artwork in the csv file, only artist will be specified in the award.")
            no_artwork = True

        # If partial to no artist data in the csv
        if not all([firstname, lastname]):
            if not any([firstname, lastname]):
                logger.info("No info about the artist")
                no_artist = True
            else:
                logger.info("Partial data about artist ...")

        if all([no_artwork, no_artist]):
            logger.warning(
                f"{aw_title} No info about the artwork nor the artists: SKIPPING\n{aw}\n\n")
            continue

        # IF NO ID ARTWORK
        # Retrieve artwork with title similarity
        getArtworkByTitle()

    aws.to_csv('./tmp/artworks_artists.csv', index=False)


def getArtworkByTitle(aw_title):
    guessAW = Artwork.objects.annotate(
        similarity=TrigramSimilarity('title', aw_title),
    ).filter(similarity__gt=0.7).order_by('-similarity')

    if guessAW:
        logger.warning(f"Potential artworks in Kart found for \"{aw_title}\"...")
        # Explore the potential artworks
        for gaw in guessAW:
            logger.warning(f"\t->Best guess: \"{gaw.title}\"")
            # If approaching results is exactly the same
            title_match_dist = dist2(aw_title.lower(), gaw.title.lower())
            logger.warning(f"title_match_dist {title_match_dist}")

            # if all([title_match_dist, author_match_dist, title_match_dist == 1, author_match_dist == 1]):
            #     logger.warning("Perfect match: artwork and related authors exist in Kart")
            # if all([title_match_dist, author_match_dist, title_match_dist == 1]):
            #     logger.warning(
            #         f"Sure about the artwork title, confidence in author: {author_match_dist}")
            # if all([title_match_dist, author_match_dist, author_match_dist == 1]):
            #     logger.warning(
            #         f"Sure about the authors, confidence in artwirk: {author_match_dist}")

            # TODO: include author_match_dist for higher specificity
            # if all([title_match_dist, author_match_dist, title_match_dist == 1, author_match_dist == 1]):
            #     logger.warning("Perfect match: artwork and related authors exist in Kart")
            # if all([title_match_dist, author_match_dist, title_match_dist == 1]):
            #     logger.warning(
            #         f"Sure about the artwork title, confidence in author: {author_match_dist}")
            # if all([title_match_dist, author_match_dist, author_match_dist == 1]):
            #     logger.warning(
            #         f"Sure about the authors, confidence in artwirk: {author_match_dist}")

    else:  # no artwork found in Kart
        logger.warning(f"No approaching artwork in KART for {aw_title}")
        # Retrieving data to create the artwork
