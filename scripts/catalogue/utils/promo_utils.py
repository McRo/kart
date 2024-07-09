from django.contrib.postgres.search import TrigramSimilarity
from school.models import Promotion

def getPromoByName(promo_name="") :
    """ Return a promotion object from a promo name"""
    # First filter by lastname similarity
    guessPromo = Promotion.objects.annotate(
                                        similarity=TrigramSimilarity('name', promo_name)
                                   ).filter(
                                        similarity__gt=0.8
                                    ).order_by('-similarity')
    if guessPromo :
        return guessPromo[0]
    print("Promo non trouvée", promo_name)
    return None
